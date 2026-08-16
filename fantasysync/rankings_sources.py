"""Live ADP/stats/projections/headshots enrichment from public fantasy-data
APIs.

Five sources today:
- Sleeper: free, no API key, player headshot photo URLs for the draft
  board's drafted-cell photo (fantasysync/draft_engine.py's
  snake_board_html). Not used for any ranking/ADP data.
- Fantasy Football Calculator: free, no API key, real ADP + bye weeks.
- ESPN: free, no API key or private-league credentials needed - a public
  "league defaults" endpoint gives platform-wide ADP across all ESPN
  leagues, separate from this app's connected private league
  (fantasysync/espn_sync.py). Confirmed no half-PPR-specific breakout
  exists here (checked ~10 endpoint variants and every scoring-type
  option) - it's one blended ADP number per player regardless of format.
- nflverse: free, no API key, real final stats from the most recently
  completed season (rush/rec/pass yards, receptions, fantasy points).
  Populates rush_yds/rec_yds/pass_yds as a baseline.
- FantasyPros: consensus rankings + full-stat *projections*, needs an API
  key (st.secrets["FANTASYPROS_API_KEY"]). Silently skipped if no key is
  configured. When a key is present, its forward-looking projections
  overwrite the nflverse historical baseline in rush_yds/rec_yds/pass_yds -
  last season's real stats today, this season's projections automatically
  once a key is added, rather than two parallel sets of similar columns.

Every available ADP source (FFCalculator, ESPN, and FantasyPros once
configured) is blended into consensus_adp itself - a row-wise average
across whichever sources have a value for a given player - rather than
kept as separate unused columns, so every consumer of consensus_adp (the
Draft Room's ADP sort/VAL badge, the Rankings tab) gets the blend for
free. FantasyPros' free API tier caps results at ~10 players per position,
so most players' blend is just FFCalculator + ESPN.

Every fetch function returns None on any failure (network error, bad
response, timeout) instead of raising - a live-data outage should degrade
to "keep showing the last known values," never crash the app.
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import pandas as pd
import requests
import streamlit as st

from fantasysync.config import (
    PPR_RECEPTION_VALUE,
    SCORING_FORMAT_FANTASYPROS,
    SCORING_FORMAT_FFCALCULATOR,
)

FANTASYPROS_BASE = "https://api.fantasypros.com/public/v2/json"
# FantasyPros' consensus-rankings/projections endpoints require one call
# per position - there is no "all positions" option (confirmed against a
# live response: requesting without `position` returns a 400 listing the
# valid values). Limited to the four positions this app actually ranks.
FANTASYPROS_POSITIONS = ["QB", "RB", "WR", "TE"]
FFCALCULATOR_BASE = "https://fantasyfootballcalculator.com/api/v1/adp"
# ESPN's public "league defaults" player-info endpoint - platform-wide
# average draft position across all ESPN leagues, not tied to any specific
# private league (confirmed live 2026-08-14: no espn_s2/SWID needed at
# all). Tried ~10 different `leaguedefaults/{id}` values and every scoring
# type in `sortDraftRanks` looking for a half-PPR-specific number - none
# exist, this view returns one blended ADP per player regardless of
# scoring format (draftRanksByRankType only has STANDARD/PPR/ELIMINATION/
# SUPERFLEX, no half-PPR option either). Still real, large-sample,
# platform-wide data worth blending in, just not format-precise the way
# FFCalculator's and FantasyPros' numbers are.
ESPN_LEAGUEDEFAULTS_BASE = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons"
ESPN_POSITION_SLOT_IDS = {"QB": 0, "RB": 2, "WR": 4, "TE": 6}
# Sleeper's full player list (free, no key) doubles as a public headshot
# CDN: https://sleepercdn.com/content/nfl/players/{sleeper_id}.jpg -
# confirmed live 2026-08-15, no smaller/thumbnail variant exists at this
# URL (a /thumb/ and /60x60/ path were both tried - same full-size image
# or a 403). One-time ~4MB fetch of Sleeper's full player list, cached
# 6h same as everything else here; only a compact id/name/position slice
# of it is kept afterward, not the raw payload.
SLEEPER_PLAYERS_URL = "https://api.sleeper.app/players/nfl"
SLEEPER_HEADSHOT_BASE = "https://sleepercdn.com/content/nfl/players"
NFLVERSE_SEASON_STATS_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "player_stats/player_stats_season.csv"
)
REQUEST_TIMEOUT = 10
LIVE_DATA_TTL = "6h"

_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def normalize_name(name: str) -> str:
    """Reduce a player name to a form comparable across data sources."""
    text = str(name or "").lower().strip()
    text = text.replace(".", "").replace("'", "")
    words = [w for w in re.split(r"[\s-]+", text) if w and w not in _SUFFIXES]
    return " ".join(words)


@st.cache_data(ttl=LIVE_DATA_TTL, show_spinner=False)
def fetch_ffcalculator_adp(
    teams: int = 10,
    scoring: str = SCORING_FORMAT_FFCALCULATOR,
) -> Optional[pd.DataFrame]:
    """Live ADP + bye weeks + real draft-community ADP variance ("stdev" -
    how much actual drafters disagree on when to take this player). Free,
    no API key. Returns None on any failure."""
    try:
        resp = requests.get(
            f"{FFCALCULATOR_BASE}/{scoring}",
            params={"teams": teams},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        players = payload.get("players", [])
        if not players:
            return None

        df = pd.DataFrame(players)
        if "stdev" not in df.columns:
            # Defensive: don't let the whole ADP feed fail if the API ever
            # omits this field, since it's used for a secondary feature
            # (CPU pick variance) - just proceed without it.
            df["stdev"] = pd.NA
        df = df[["name", "position", "team", "adp", "bye", "stdev"]]
        df["_match_key"] = (df["name"].map(normalize_name) + "|" + df["position"])
        # set_index() below requires a unique index; two players sharing a
        # normalized name+position (rare, but not impossible) would raise.
        df = df.drop_duplicates(subset="_match_key", keep="first")
        return df
    except (requests.RequestException, ValueError, KeyError):
        return None


@st.cache_data(ttl=LIVE_DATA_TTL, show_spinner=False)
def fetch_espn_platform_adp(season: int = 2026, per_position_limit: int = 60) -> Optional[pd.DataFrame]:
    """Platform-wide ADP across all ESPN leagues. Free, no API key or
    espn_s2/SWID needed - this is separate from this app's connected
    private league (fantasysync/espn_sync.py), which wouldn't be a useful
    ADP source even once it drafts (one 10-team draft is one data point
    per player, not an average). Returns None on any failure."""
    try:
        rows = []
        for position, slot_id in ESPN_POSITION_SLOT_IDS.items():
            resp = requests.get(
                f"{ESPN_LEAGUEDEFAULTS_BASE}/{season}/segments/0/leaguedefaults/3",
                params={"view": "kona_player_info"},
                headers={
                    "x-fantasy-filter": json.dumps({
                        "players": {
                            "filterSlotIds": {"value": [slot_id]},
                            "limit": per_position_limit,
                            "sortDraftRanks": {
                                "sortPriority": 1,
                                "sortAsc": True,
                                "value": "STANDARD",
                            },
                        }
                    })
                },
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            for entry in resp.json().get("players", []):
                player = entry.get("player", {})
                adp = player.get("ownership", {}).get("averageDraftPosition")
                name = player.get("fullName")
                if adp is None or not name:
                    continue
                rows.append({"name": name, "position": position, "espn_adp": adp})

        if not rows:
            return None

        df = pd.DataFrame(rows)
        df["_match_key"] = df["name"].map(normalize_name) + "|" + df["position"]
        df = df.drop_duplicates(subset="_match_key", keep="first")
        return df
    except (requests.RequestException, ValueError, KeyError):
        return None


@st.cache_data(ttl=LIVE_DATA_TTL, show_spinner=False)
def fetch_sleeper_headshots() -> Optional[pd.DataFrame]:
    """Player headshot URLs, for the draft board's drafted-cell photo. Free,
    no API key. The raw payload is every player Sleeper has ever tracked
    (~12k, most inactive/practice-squad/irrelevant) - trimmed down to just
    the four fantasy positions this app ranks before returning, so what
    actually gets cached is small even though the fetch itself isn't."""
    try:
        resp = requests.get(SLEEPER_PLAYERS_URL, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, dict) or not payload:
            return None

        rows = []
        for sleeper_id, player in payload.items():
            position = player.get("position")
            if position not in {"QB", "RB", "WR", "TE"}:
                continue
            first = str(player.get("first_name") or "").strip()
            last = str(player.get("last_name") or "").strip()
            full_name = f"{first} {last}".strip()
            if not full_name:
                continue
            rows.append({
                "name": full_name,
                "position": position,
                "headshot_url": f"{SLEEPER_HEADSHOT_BASE}/{sleeper_id}.jpg",
            })

        if not rows:
            return None

        df = pd.DataFrame(rows)
        df["_match_key"] = df["name"].map(normalize_name) + "|" + df["position"]
        df = df.drop_duplicates(subset="_match_key", keep="first")
        return df
    except (requests.RequestException, ValueError, KeyError):
        return None


@st.cache_data(ttl=LIVE_DATA_TTL, show_spinner=False)
def fetch_nflverse_season_stats() -> Optional[pd.DataFrame]:
    """Real final stats from the most recently completed NFL season.

    Free, no API key - a community-maintained CSV of season-total stats
    published by the nflverse project. Automatically finds the latest
    season present in the file rather than a hardcoded year, so it keeps
    working once next season's stats are published without a code change.
    """
    try:
        resp = requests.get(NFLVERSE_SEASON_STATS_URL, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        from io import StringIO

        df = pd.read_csv(StringIO(resp.text), low_memory=False)
        df = df[df["season_type"] == "REG"]
        if df.empty:
            return None

        latest_season = int(df["season"].max())
        df = df[df["season"] == latest_season]

        rename_map = {
            "player_display_name": "name",
            "recent_team": "team",
            "rushing_yards": "rush_yds",
            "receiving_yards": "rec_yds",
            "passing_yards": "pass_yds",
        }
        df = df.rename(columns=rename_map)

        # nflverse only publishes standard and full-PPR point totals, not
        # this league's half-PPR - computed here from the standard total
        # plus half a point per reception rather than using the full-PPR
        # column directly, since the two diverge meaningfully for
        # pass-catching backs/WRs.
        if "fantasy_points" in df.columns and "receptions" in df.columns:
            df["fantasy_pts"] = df["fantasy_points"] + PPR_RECEPTION_VALUE * df["receptions"].fillna(0)

        keep = [c for c in ["name", "position", "team", "rush_yds", "rec_yds", "pass_yds", "receptions", "fantasy_pts"] if c in df.columns]
        df = df[keep]
        df["_match_key"] = (df["name"].map(normalize_name) + "|" + df["position"])
        df = df.drop_duplicates(subset="_match_key", keep="first")
        df.attrs["season"] = latest_season
        return df
    except (requests.RequestException, ValueError, KeyError):
        return None


@st.cache_data(ttl=LIVE_DATA_TTL, show_spinner=False)
def fetch_fantasypros_consensus(
    api_key: str,
    season: int,
    scoring: str = SCORING_FORMAT_FANTASYPROS,
) -> Optional[pd.DataFrame]:
    """Consensus expert rankings/ADP/tier from FantasyPros. Needs an API key.

    Verified against a live response (2026-08-14): the endpoint requires one
    call per position - there is no "all positions" option, requesting
    without `position` returns a 400 error. `rank_ave` (used here as ADP)
    comes back as a string, not a number. The free/base API tier also caps
    each position at ~10 players regardless of how many actually exist
    (`public_api_limited: true` in the response) - this only enriches the
    top of each position, everything past that keeps whatever ADP/rank it
    already had from the other sources.
    """
    if not api_key:
        return None
    try:
        frames = []
        for position in FANTASYPROS_POSITIONS:
            resp = requests.get(
                f"{FANTASYPROS_BASE}/nfl/{season}/consensus-rankings",
                params={"scoring": scoring, "position": position},
                headers={"x-api-key": api_key},
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            players = resp.json().get("players", [])
            if players:
                frames.append(pd.DataFrame(players))

        if not frames:
            return None

        df = pd.concat(frames, ignore_index=True)
        rename_map = {
            "player_name": "name",
            "player_position_id": "position",
            "player_team_id": "team",
            "rank_ecr": "fantasypros_rank",
            "tier": "fantasypros_tier",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        if "rank_ave" in df.columns:
            df["fantasypros_adp"] = pd.to_numeric(df["rank_ave"], errors="coerce")
        keep = [c for c in ["name", "position", "team", "fantasypros_rank", "fantasypros_adp", "fantasypros_tier"] if c in df.columns]
        if "name" not in keep or "position" not in keep:
            return None
        df = df[keep]
        df["_match_key"] = (df["name"].map(normalize_name) + "|" + df["position"])
        df = df.drop_duplicates(subset="_match_key", keep="first")
        return df
    except (requests.RequestException, ValueError, KeyError):
        return None


@st.cache_data(ttl=LIVE_DATA_TTL, show_spinner=False)
def fetch_fantasypros_projections(
    api_key: str,
    season: int,
    scoring: str = SCORING_FORMAT_FANTASYPROS,
) -> Optional[pd.DataFrame]:
    """Full-season stat projections from FantasyPros. Needs an API key.

    Verified against a live response (2026-08-14): same one-call-per-position
    requirement and ~10-player-per-position free-tier cap as the consensus
    endpoint above. Per-player fields are flat (`name`, `position_id`,
    `team_id`) but every stat lives nested under a `stats` object, and the
    scoring-format-aware point total is `stats.points_half` (not a top-level
    `fpts` field, and not `points_ppr` - the previous version of this
    function assumed a flat, unverified shape from FantasyPros' docs alone
    that didn't match what the API actually returns).
    """
    if not api_key:
        return None
    try:
        rows = []
        for position in FANTASYPROS_POSITIONS:
            resp = requests.get(
                f"{FANTASYPROS_BASE}/nfl/{season}/projections",
                params={"scoring": scoring, "position": position},
                headers={"x-api-key": api_key},
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            for player in resp.json().get("players", []):
                stats = player.get("stats", {})
                rows.append({
                    "name": player.get("name"),
                    "position": player.get("position_id"),
                    "team": player.get("team_id"),
                    "proj_pts": stats.get("points_half"),
                    "rush_yds": stats.get("rush_yds"),
                    "rec_yds": stats.get("rec_yds"),
                    "receptions": stats.get("rec_rec"),
                    "pass_yds": stats.get("pass_yds"),
                })

        if not rows:
            return None

        df = pd.DataFrame(rows)
        if "name" not in df.columns or "position" not in df.columns:
            return None
        df["_match_key"] = (df["name"].map(normalize_name) + "|" + df["position"])
        df = df.drop_duplicates(subset="_match_key", keep="first")
        return df
    except (requests.RequestException, ValueError, KeyError):
        return None


def enrich_players_with_live_data(
    players: pd.DataFrame,
    num_teams: int = 10,
    season: int = 2026,
) -> pd.DataFrame:
    """Overlay live ADP/bye/projections onto the static player roster.

    The individual fetch functions already swallow their own network
    errors, but the merge/matching logic itself can still fail in ways
    those try/excepts don't cover (unexpected data shapes, missing
    columns). This wrapper guarantees the promise made throughout this
    module - a live-data problem degrades to "keep the static CSV as-is,"
    never crashes the app - by catching anything unexpected here too.
    """
    try:
        return _merge_live_data(players, num_teams=num_teams, season=season)
    except Exception:
        return players


def get_stats_season_label() -> Optional[int]:
    """Which season the nflverse historical stats baseline is from, for
    display purposes (e.g. "2024 season stats"). None if unavailable."""
    try:
        history = fetch_nflverse_season_stats()
        return None if history is None else history.attrs.get("season")
    except Exception:
        return None


def _merge_live_data(
    players: pd.DataFrame,
    num_teams: int,
    season: int,
) -> pd.DataFrame:
    """Matches by normalized-name + position. Any player not found in a live
    source, or any source that's unavailable (no key, network failure),
    just keeps whatever was already in the static CSV - this never removes
    or blanks out existing data, only fills in/updates when a live match
    is found.
    """
    players = players.copy()
    players["_match_key"] = players["player"].map(normalize_name) + "|" + players["position"]

    # These four sources are independent network calls - fetching them
    # concurrently instead of one after the other keeps the wait to
    # whichever one is slowest on a cache miss, not the sum of all four.
    with ThreadPoolExecutor(max_workers=4) as pool:
        adp_future = pool.submit(fetch_ffcalculator_adp, teams=num_teams)
        history_future = pool.submit(fetch_nflverse_season_stats)
        espn_adp_future = pool.submit(fetch_espn_platform_adp, season=season)
        headshots_future = pool.submit(fetch_sleeper_headshots)
        adp_source = adp_future.result()
        history = history_future.result()
        espn_adp_source = espn_adp_future.result()
        headshots = headshots_future.result()

    if espn_adp_source is not None:
        lookup = espn_adp_source.set_index("_match_key")
        matched = players["_match_key"].map(lookup["espn_adp"])
        players["espn_adp"] = matched.combine_first(players.get("espn_adp", pd.Series(dtype=float)))

    if headshots is not None:
        lookup = headshots.set_index("_match_key")
        matched = players["_match_key"].map(lookup["headshot_url"])
        players["headshot_url"] = matched.combine_first(players.get("headshot_url", pd.Series(dtype=object)))

    if adp_source is not None:
        lookup = adp_source.set_index("_match_key")
        matched = players["_match_key"].map(lookup["adp"])
        players["consensus_adp"] = matched.combine_first(players.get("consensus_adp", pd.Series(dtype=float)))
        if "bye" not in players.columns:
            players["bye"] = pd.NA
        matched_bye = players["_match_key"].map(lookup["bye"])
        players["bye"] = matched_bye.combine_first(players["bye"])

        # Real draft-community disagreement per player, used by the CPU
        # draft logic (fantasysync/draft_engine.py) to make picks
        # unpredictable in proportion to how much real drafters actually
        # disagree on that player, rather than an app-wide flat setting.
        if "consensus_adp_stdev" not in players.columns:
            players["consensus_adp_stdev"] = pd.NA
        matched_stdev = players["_match_key"].map(lookup["stdev"])
        players["consensus_adp_stdev"] = matched_stdev.combine_first(players["consensus_adp_stdev"])

    # Last-completed-season real stats as a baseline for rush/rec/pass yards
    # and points - the FantasyPros block below overwrites these with
    # forward-looking projections once an API key is configured, since
    # projections are more useful for drafting than last year's stats once
    # available. Until then, real history beats an empty column.
    if history is not None:
        lookup = history.set_index("_match_key")
        for source_col, target_col in [
            ("rush_yds", "rush_yds"),
            ("rec_yds", "rec_yds"),
            ("pass_yds", "pass_yds"),
            ("fantasy_pts", "proj_pts"),
        ]:
            if source_col not in lookup.columns:
                continue
            if target_col not in players.columns:
                players[target_col] = pd.NA
            matched = players["_match_key"].map(lookup[source_col])
            players[target_col] = matched.combine_first(players[target_col])

    try:
        api_key = st.secrets.get("FANTASYPROS_API_KEY", "")
    except Exception:
        # No secrets.toml configured anywhere (local or Cloud) - proceed
        # without FantasyPros data rather than crashing the app.
        api_key = ""
    if api_key:
        consensus = fetch_fantasypros_consensus(api_key, season)
        if consensus is not None:
            lookup = consensus.set_index("_match_key")
            if "fantasypros_adp" in lookup.columns:
                matched = players["_match_key"].map(lookup["fantasypros_adp"])
                players["fantasypros_adp"] = matched.combine_first(players.get("fantasypros_adp", pd.Series(dtype=float)))

        projections = fetch_fantasypros_projections(api_key, season)
        if projections is not None:
            lookup = projections.set_index("_match_key")
            for col in ["proj_pts", "rush_yds", "rec_yds", "pass_yds"]:
                if col not in lookup.columns:
                    continue
                if col not in players.columns:
                    players[col] = pd.NA
                matched = players["_match_key"].map(lookup[col])
                players[col] = matched.combine_first(players[col])

    # Blend every available ADP source into consensus_adp itself, rather
    # than leaving fantasypros_adp/espn_adp as separate unused columns -
    # every consumer (Draft Room sort/VAL badge, Rankings tab) already
    # reads consensus_adp, so blending in place means the "average ADP
    # across sites" the site is going for reaches everywhere at once.
    # Row-wise mean skipping NaNs: a true average across whichever sources
    # have a value for a given player, down to just FFCalculator's number
    # alone for players outside FantasyPros' free-tier top-10-per-position
    # cap. Runs unconditionally - FFCalculator and ESPN are both always
    # fetched above with no key needed, FantasyPros only adds a third
    # column when configured.
    adp_sources = [pd.to_numeric(players.get("consensus_adp"), errors="coerce")]
    if "fantasypros_adp" in players.columns:
        adp_sources.append(pd.to_numeric(players["fantasypros_adp"], errors="coerce"))
    if "espn_adp" in players.columns:
        adp_sources.append(pd.to_numeric(players["espn_adp"], errors="coerce"))
    if len(adp_sources) > 1:
        players["consensus_adp"] = pd.concat(adp_sources, axis=1).mean(axis=1, skipna=True)

    return players.drop(columns=["_match_key"])
