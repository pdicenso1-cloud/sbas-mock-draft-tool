"""Live ADP/projections enrichment from public fantasy-data APIs.

Two sources today:
- Fantasy Football Calculator: free, no API key, real ADP + bye weeks.
- FantasyPros: consensus rankings + full-stat projections, needs an API key
  (st.secrets["FANTASYPROS_API_KEY"]). Silently skipped if no key is
  configured, so the app works fine without one and picks it up
  automatically the moment a key is added.

Every fetch function returns None on any failure (network error, bad
response, timeout) instead of raising - a live-data outage should degrade
to "keep showing the last known values," never crash the app.
"""
from __future__ import annotations

import re
from typing import Optional

import pandas as pd
import requests
import streamlit as st

FANTASYPROS_BASE = "https://api.fantasypros.com/public/v2/json"
FFCALCULATOR_BASE = "https://fantasyfootballcalculator.com/api/v1/adp"
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
def fetch_ffcalculator_adp(teams: int = 10, scoring: str = "ppr") -> Optional[pd.DataFrame]:
    """Live ADP + bye weeks. Free, no API key. Returns None on any failure."""
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

        df = pd.DataFrame(players)[["name", "position", "team", "adp", "bye"]]
        df["_match_key"] = (df["name"].map(normalize_name) + "|" + df["position"])
        return df
    except (requests.RequestException, ValueError, KeyError):
        return None


@st.cache_data(ttl=LIVE_DATA_TTL, show_spinner=False)
def fetch_fantasypros_consensus(
    api_key: str,
    season: int,
    scoring: str = "PPR",
) -> Optional[pd.DataFrame]:
    """Consensus expert rankings/ADP/tier from FantasyPros. Needs an API key."""
    if not api_key:
        return None
    try:
        resp = requests.get(
            f"{FANTASYPROS_BASE}/nfl/{season}/consensus-rankings",
            params={"scoring": scoring},
            headers={"x-api-key": api_key},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        players = payload.get("players", payload if isinstance(payload, list) else [])
        if not players:
            return None

        df = pd.DataFrame(players)
        rename_map = {
            "player_name": "name",
            "player_position_id": "position",
            "player_team_id": "team",
            "rank_ecr": "fantasypros_rank",
            "rank_ave": "fantasypros_adp",
            "tier": "fantasypros_tier",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        keep = [c for c in ["name", "position", "team", "fantasypros_rank", "fantasypros_adp", "fantasypros_tier"] if c in df.columns]
        if "name" not in keep or "position" not in keep:
            return None
        df = df[keep]
        df["_match_key"] = (df["name"].map(normalize_name) + "|" + df["position"])
        return df
    except (requests.RequestException, ValueError, KeyError):
        return None


@st.cache_data(ttl=LIVE_DATA_TTL, show_spinner=False)
def fetch_fantasypros_projections(
    api_key: str,
    season: int,
    scoring: str = "PPR",
) -> Optional[pd.DataFrame]:
    """Full-season stat projections from FantasyPros. Needs an API key.

    NOTE: built from FantasyPros' published field-naming conventions, not
    yet verified against a live response (no API key was available while
    writing this). The rename map below may need adjusting once real
    response data is seen - if projections don't populate after adding a
    key, log the raw payload's column names and fix rename_map to match.
    """
    if not api_key:
        return None
    try:
        resp = requests.get(
            f"{FANTASYPROS_BASE}/nfl/{season}/projections",
            params={"scoring": scoring},
            headers={"x-api-key": api_key},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        players = payload.get("players", payload if isinstance(payload, list) else [])
        if not players:
            return None

        df = pd.DataFrame(players)
        rename_map = {
            "player_name": "name",
            "player_position_id": "position",
            "fpts": "proj_pts",
            "rush_yds": "rush_yds",
            "rec_yds": "rec_yds",
            "rec_receptions": "receptions",
            "pass_yds": "pass_yds",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        keep = [c for c in ["name", "position", "proj_pts", "rush_yds", "rec_yds", "receptions", "pass_yds"] if c in df.columns]
        if "name" not in keep or "position" not in keep:
            return None
        df = df[keep]
        df["_match_key"] = (df["name"].map(normalize_name) + "|" + df["position"])
        return df
    except (requests.RequestException, ValueError, KeyError):
        return None


def enrich_players_with_live_data(
    players: pd.DataFrame,
    num_teams: int = 10,
    season: int = 2026,
) -> pd.DataFrame:
    """Overlay live ADP/bye/projections onto the static player roster.

    Matches by normalized-name + position. Any player not found in a live
    source, or any source that's unavailable (no key, network failure),
    just keeps whatever was already in the static CSV - this never removes
    or blanks out existing data, only fills in/updates when a live match
    is found.
    """
    players = players.copy()
    players["_match_key"] = players["player"].map(normalize_name) + "|" + players["position"]

    adp_source = fetch_ffcalculator_adp(teams=num_teams)
    if adp_source is not None:
        lookup = adp_source.set_index("_match_key")
        matched = players["_match_key"].map(lookup["adp"])
        players["consensus_adp"] = matched.combine_first(players.get("consensus_adp", pd.Series(dtype=float)))
        if "bye" not in players.columns:
            players["bye"] = pd.NA
        matched_bye = players["_match_key"].map(lookup["bye"])
        players["bye"] = matched_bye.combine_first(players["bye"])

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
