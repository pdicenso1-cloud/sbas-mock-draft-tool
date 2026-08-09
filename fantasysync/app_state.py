"""Session-state defaults, CSV loading, and tray/dock sizing.

Split out of the former monolithic runtime.py so app initialization and
layout-size settings can be found and changed without wading through draft
logic or UI rendering code.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from fantasysync.paths import DATA_DIR
from fantasysync.rankings_sources import LIVE_DATA_TTL, enrich_players_with_live_data


def clean(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def numeric(value, fallback=None):
    try:
        if pd.isna(value) or clean(value) == "":
            return fallback
        return float(value)
    except (TypeError, ValueError):
        return fallback


@st.cache_data(ttl=LIVE_DATA_TTL)
def load_defaults():
    players = pd.read_csv(DATA_DIR / "players.csv")
    teams = pd.read_csv(DATA_DIR / "teams.csv")
    keepers = pd.read_csv(DATA_DIR / "keepers.csv")

    for col in ["rank", "custom_rank", "market_rank", "consensus_adp", "underdog_adp",
                "nfl_adp", "sleeper_adp", "yahoo_adp", "espn_adp",
                "fantasypros_adp", "walterpicks_adp", "peter_score"]:
        if col in players.columns:
            players[col] = pd.to_numeric(players[col], errors="coerce")

    players["rank"] = players["rank"].fillna(9999).astype(int)
    players["custom_rank"] = players["custom_rank"].fillna(players["rank"]).astype(int)
    teams["team_id"] = teams["team_id"].astype(int)
    teams["draft_slot"] = teams["draft_slot"].astype(int)

    if not keepers.empty:
        keepers["team_id"] = pd.to_numeric(keepers["team_id"], errors="coerce").fillna(0).astype(int)
        keepers["keeper_round"] = pd.to_numeric(keepers["keeper_round"], errors="coerce").fillna(0).astype(int)

    # Live-data enrichment (ADP, bye weeks, and - once a FantasyPros API key
    # is configured - projections) refreshes on its own cache TTL; a fetch
    # failure or missing key just leaves the static CSV values in place.
    players = enrich_players_with_live_data(players, num_teams=len(teams))

    return players, teams, keepers


def snake_order(teams_df: pd.DataFrame, rounds: int) -> pd.DataFrame:
    by_slot = {
        int(row.draft_slot): {"team_id": int(row.team_id), "team_name": clean(row.team_name)}
        for row in teams_df.itertuples()
    }
    rows = []
    overall = 1
    for rnd in range(1, rounds + 1):
        slots = list(range(1, len(teams_df) + 1))
        if rnd % 2 == 0:
            slots.reverse()
        for slot in slots:
            team = by_slot[slot]
            rows.append({
                "overall": overall,
                "round": rnd,
                "slot": slot,
                "original_team_id": team["team_id"],
                "original_owner": team["team_name"],
                "current_owner": team["team_name"],
                "keeper_player": "",
                "selected_player": "",
                "source": "",
            })
            overall += 1
    return pd.DataFrame(rows)


def assign_keepers(picks: pd.DataFrame, keepers_df: pd.DataFrame, teams_df: pd.DataFrame) -> pd.DataFrame:
    picks = picks.copy()
    team_name_by_id = dict(zip(teams_df["team_id"], teams_df["team_name"]))
    for row in keepers_df.itertuples():
        if not clean(row.player) or int(row.team_id) not in team_name_by_id:
            continue
        target_idx = None
        exact = getattr(row, "exact_pick_override", "")
        if clean(exact):
            matches = picks.index[picks["overall"] == int(float(exact))].tolist()
            target_idx = matches[0] if matches else None
        if target_idx is None:
            owner = team_name_by_id[int(row.team_id)]
            matches = picks.index[
                (picks["round"] == int(row.keeper_round))
                & (picks["current_owner"] == owner)
                & (picks["keeper_player"] == "")
            ].tolist()
            target_idx = matches[0] if matches else None
        if target_idx is not None:
            picks.at[target_idx, "keeper_player"] = clean(row.player)
            picks.at[target_idx, "selected_player"] = clean(row.player)
            picks.at[target_idx, "source"] = "Keeper"
    return picks


def init_state(force=False):
    players, teams, keepers = load_defaults()
    defaults = {
        "players": players.copy(),
        "teams": teams.copy(),
        "keepers": keepers.copy(),
        "rounds": 16,
        "user_team": clean(teams.iloc[0]["team_name"]),
        "picks": assign_keepers(snake_order(teams, 16), keepers, teams),
        "draft_message": "",
        "turn_started_at": None,
        "turn_pick_overall": None,
        "pick_clock_seconds": 60,
        "clock_running": False,
        "draft_active": False,
        "clock_paused_remaining": 60,
        "dock_level": 1,
        "cpu_variance_enabled": None,
        "cpu_variance_seed": None,
        "player_queue": [],
        "queue_auto_draft": False,
        "player_tray_level": 1,
    }
    for key, value in defaults.items():
        if force or key not in st.session_state:
            st.session_state[key] = value




PLAYER_TRAY_LEVELS = {
    0: {
        "name": "Lower",
        "board_height": 500,
        "player_height": 205,
    },
    1: {
        "name": "Standard",
        "board_height": 430,
        "player_height": 280,
    },
    2: {
        "name": "Raised",
        "board_height": 350,
        "player_height": 360,
    },
}


def player_tray_settings() -> dict:
    level = int(st.session_state.get("player_tray_level", 1))
    level = max(0, min(2, level))
    st.session_state.player_tray_level = level
    return PLAYER_TRAY_LEVELS[level]


def move_player_tray(direction: int):
    current = int(st.session_state.get("player_tray_level", 1))
    st.session_state.player_tray_level = max(
        0,
        min(2, current + direction),
    )


def render_player_tray_css():
    """Legacy no-op retained for compatibility with non-Draft Room pages."""
    return None



DOCK_LEVELS = {
    0: {"name": "Compact", "dock_vh": 24, "list_px": 178, "roster_vh": 20},
    1: {"name": "Standard", "dock_vh": 38, "list_px": 350, "roster_vh": 34},
    2: {"name": "Expanded", "dock_vh": 64, "list_px": 620, "roster_vh": 59},
}


def dock_settings() -> dict:
    level = int(st.session_state.get("dock_level", 1))
    level = max(0, min(2, level))
    st.session_state.dock_level = level
    return DOCK_LEVELS[level]



def render_dynamic_dock_css():
    settings = dock_settings()
    st.markdown(
        f"""
        <style>
        .st-key-draft_drawer {{
            height: {settings["dock_vh"]}vh !important;
            overflow: hidden !important;
            transition: height .22s ease-in-out !important;
        }}
        .st-key-draft_drawer {{
            position: fixed !important;
        }}
        .st-key-dock_controls {{
            position: absolute !important;
            top: 8px !important;
            right: 8px !important;
            z-index: 1005 !important;
            width: 40px !important;
            min-width: 40px !important;
            padding: 0 !important;
            margin: 0 !important;
            background: rgba(18, 27, 43, .96) !important;
            border: 1px solid rgba(150,170,210,.22) !important;
            border-radius: 9px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,.28) !important;
        }}
        .st-key-dock_controls [data-testid="stVerticalBlock"] {{
            gap: 4px !important;
            padding: 4px !important;
        }}
        .st-key-dock_controls button {{
            min-height: 32px !important;
            height: 32px !important;
            padding: 0 !important;
            font-size: .94rem !important;
            font-weight: 900 !important;
            border-radius: 7px !important;
        }}
        
/* ============================================================
   FantasySync v6.7.1 — Full-width snake board + round.pick labels
   ============================================================ */

/* Force the Streamlit page shell to use the browser width, regardless of
   older max-width rules retained from pre-v6.7 sidebar builds. */
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
[data-testid="stAppViewContainer"] .main,
.main,
.main .block-container {{
    width: 100vw !important;
    max-width: 100vw !important;
    min-width: 0 !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    box-sizing: border-box !important;
}}

/* Navigation/header stay comfortably inset while the board itself uses nearly
   the full viewport. */
.st-key-v670_top_nav,
.st-key-v640_header,
.st-key-v63_draft_message {{
    width: calc(100vw - 28px) !important;
    max-width: calc(100vw - 28px) !important;
    margin-left: 14px !important;
    margin-right: 14px !important;
    box-sizing: border-box !important;
}}

/* The draft grid is intentionally wider than the ordinary content column. */
.st-key-v63_board_region {{
    width: calc(100vw - 16px) !important;
    max-width: calc(100vw - 16px) !important;
    margin-left: 8px !important;
    margin-right: 8px !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    box-sizing: border-box !important;
}}

.st-key-v63_board_region .v643-board-scroll,
.st-key-v63_board_region .v643-board-content,
.st-key-v63_board_region .snake-board-wrap,
.st-key-v63_board_region .snake-board-shell,
.st-key-v63_board_region .snake-board-grid,
.st-key-v63_board_region .snake-draft-grid {{
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
    box-sizing: border-box !important;
}}

/* Round labels no longer exist; prevent stale CSS from reserving space if a
   browser keeps an old DOM fragment during a rerun. */
.st-key-v63_board_region .snake-round-label {{
    display: none !important;
    width: 0 !important;
    min-width: 0 !important;
    max-width: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    border: 0 !important;
}}

/* Pick notation is now the useful orientation cue, so make it a touch easier
   to read without competing with the player name. */
.st-key-v63_board_region .snake-pick {{
    font-size: .52rem !important;
    font-weight: 780 !important;
    letter-spacing: .01em !important;
    opacity: .78 !important;
}}

</style>
        """,
        unsafe_allow_html=True,
    )
