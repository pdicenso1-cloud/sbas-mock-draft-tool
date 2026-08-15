"""Live ADP/stats/projections enrichment from public fantasy-data APIs.

Three sources today:
- Fantasy Football Calculator: free, no API key, real ADP + bye weeks.
- nflverse: free, no API key, real final stats from the most recently
  completed season (rush/rec/pass yards, receptions, fantasy points).
  Populates rush_yds/rec_yds/pass_yds as a baseline.
- FantasyPros: consensus rankings + full-stat *projections*, needs an API
  key (st.secrets["FANTASYPROS_API_KEY"]). Silently skipped if no key is
  configured. When a key is present, its forward-looking projections
  overwrite the nflverse historical baseline in rush_yds/rec_yds/pass_yds -
  last season's real stats today, this season's projections automatically
  once a key is added, rather than two parallel sets of similar columns.

Every fetch function returns None on any failure (network error, bad
response, timeout) instead of raising - a live-data outage should degrade
to "keep showing the last known values," never crash the app.
"""
from __future__ import annotations

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

    # These two sources are independent network calls - fetching them
    # concurrently instead of one after the other roughly halves the wait
    # on a cache miss (the slower of the two, not the sum of both).
    with ThreadPoolExecutor(max_workers=2) as pool:
        adp_future = pool.submit(fetch_ffcalculator_adp, teams=num_teams)
        history_future = pool.submit(fetch_nflverse_season_stats)
        adp_source = adp_future.result()
        history = history_future.result()

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

    return players.drop(columns=["_match_key"])
