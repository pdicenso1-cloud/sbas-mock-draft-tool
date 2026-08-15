"""Read-only ESPN league sync - settings, scoring rules, and roster config.

Needs three Streamlit secrets, all belonging to the account owner (this
mirrors the espn_s2/SWID scope decision already made for league sync -
see the [[espn-league-sync-goal]] memory): ESPN_LEAGUE_ID, ESPN_S2,
ESPN_SWID. Silently returns None if any are missing or the connection
fails, same "degrade to nothing rather than crash" pattern used throughout
fantasysync/rankings_sources.py.

Deliberately does NOT touch data/teams.csv or data/keepers.csv. Confirmed
live against the real league (2026-08-14): ESPN's API only exposes draft
order and keeper designations once the actual draft has happened, and the
site's manually-maintained draft order/keepers are already correct for the
upcoming draft - so this module is read-only status/comparison data for the
Data Status page, not a source the rest of the app draws from.
"""
from __future__ import annotations

from typing import Optional

import streamlit as st

try:
    from espn_api.football import League
except ImportError:
    League = None


@st.cache_data(ttl="1h", show_spinner=False)
def fetch_espn_league_summary(season: int = 2026) -> Optional[dict]:
    """Snapshot of the connected ESPN league's settings, teams, and scoring
    rules for display on the Data Status page. None if not configured, the
    espn_api package isn't installed, or the connection fails."""
    if League is None:
        return None

    try:
        league_id = int(st.secrets.get("ESPN_LEAGUE_ID", 0))
        espn_s2 = st.secrets.get("ESPN_S2", "")
        swid = st.secrets.get("ESPN_SWID", "")
    except Exception:
        # No secrets.toml configured anywhere (local or Cloud).
        return None

    if not league_id or not espn_s2 or not swid:
        return None

    try:
        league = League(league_id=league_id, year=season, espn_s2=espn_s2, swid=swid)
    except Exception:
        return None

    settings = league.settings

    reception_points = None
    scoring_rules = []
    for item in settings.scoring_format:
        label = item.get("label", "Unknown")
        points = item.get("points", 0)
        scoring_rules.append({"stat": label, "points": points})
        if item.get("abbr") == "REC":
            reception_points = points

    teams = []
    for team in league.teams:
        owner_name = ""
        if team.owners:
            owner = team.owners[0]
            owner_name = f"{owner.get('firstName', '')} {owner.get('lastName', '')}".strip()
        teams.append({
            "espn_team_id": team.team_id,
            "team_name": team.team_name,
            "owner": owner_name,
        })

    return {
        "league_name": settings.name,
        "team_count": settings.team_count,
        "keeper_count": settings.keeper_count,
        "scoring_type": settings.scoring_type,
        "reception_points": reception_points,
        "scoring_rules": scoring_rules,
        "position_slot_counts": {
            k: v for k, v in settings.position_slot_counts.items() if v
        },
        "teams": teams,
        "draft_completed": bool(league.draft),
    }
