"""Player-pool search, position filtering, and column sorting for the
Draft Room's player table.

Split out of the former monolithic runtime.py.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from fantasysync.app_state import clean
from fantasysync.draft_engine import available_players, reset_pick_clock


def ensure_draft_filters():

    if "draft_position_filter" not in st.session_state:
        st.session_state.draft_position_filter = "ALL"
    if "draft_search" not in st.session_state:
        st.session_state.draft_search = ""

    # v7.3 player-table sorting persists through Streamlit/CPU reruns.
    if "player_sort_column" not in st.session_state:
        st.session_state.player_sort_column = "RK"
    if "player_sort_ascending" not in st.session_state:
        st.session_state.player_sort_ascending = True


PLAYER_SORT_CONFIG = {
    "RK": ("custom_rank", True),
    "PLAYER": ("player", True),
    "ADP": ("consensus_adp", True),
    "TIER": ("tier", True),
    "SCORE": ("peter_score", False),
    "PROJ": ("proj_pts", False),
    "AVG": ("proj_avg", False),
    "RUSH": ("rush_yds", False),
    "REC": ("rec_yds", False),
    "PASS": ("pass_yds", False),
    "BYE": ("bye", True),
    "VAL": ("_fs_value_sort", False),
}


def set_player_sort(column: str) -> None:
    """Toggle active player-table sorting without resetting the tray."""
    ensure_draft_filters()
    column = str(column).upper()
    if column not in PLAYER_SORT_CONFIG:
        return

    current = str(st.session_state.player_sort_column).upper()
    if current == column:
        st.session_state.player_sort_ascending = not bool(
            st.session_state.player_sort_ascending
        )
    else:
        st.session_state.player_sort_column = column
        st.session_state.player_sort_ascending = PLAYER_SORT_CONFIG[column][1]


def sort_player_pool(pool: pd.DataFrame, current_idx: int) -> pd.DataFrame:
    """Sort the filtered draft pool by the active user-selected column."""
    ensure_draft_filters()
    result = pool.copy()

    # VAL is live value vs the current overall pick.
    adp_numeric = pd.to_numeric(
        result.get("consensus_adp"),
        errors="coerce",
    )
    current_pick = int(st.session_state.picks.loc[current_idx, "overall"])
    result["_fs_value_sort"] = current_pick - adp_numeric

    column = str(st.session_state.player_sort_column).upper()
    field, default_ascending = PLAYER_SORT_CONFIG.get(
        column,
        ("custom_rank", True),
    )
    ascending = bool(
        st.session_state.get(
            "player_sort_ascending",
            default_ascending,
        )
    )

    if field not in result.columns:
        field = "custom_rank"
        ascending = True

    numeric_fields = {
        "custom_rank",
        "consensus_adp",
        "peter_score",
        "proj_pts",
        "proj_avg",
        "rush_yds",
        "rec_yds",
        "pass_yds",
        "bye",
        "_fs_value_sort",
    }

    if field in numeric_fields:
        result["_fs_active_sort"] = pd.to_numeric(
            result[field],
            errors="coerce",
        )
        result = result.sort_values(
            ["_fs_active_sort", "custom_rank"],
            ascending=[ascending, True],
            na_position="last",
            kind="stable",
        )
    else:
        result["_fs_active_sort"] = (
            result[field].fillna("").astype(str).str.casefold()
        )
        result = result.sort_values(
            ["_fs_active_sort", "custom_rank"],
            ascending=[ascending, True],
            na_position="last",
            kind="stable",
        )

    return result.drop(
        columns=["_fs_active_sort", "_fs_value_sort"],
        errors="ignore",
    )


FLEX_POSITIONS = {"RB", "WR", "TE"}


def render_position_filter():
    positions = ["ALL", "QB", "RB", "WR", "TE", "FLEX"]
    with st.container(key="v612_position_filter_bar"):
        cols = st.columns(len(positions))
        for i, pos in enumerate(positions):
            active = st.session_state.draft_position_filter == pos
            button_type = "primary" if active else "secondary"
            if cols[i].button(
                pos,
                key=f"draft_pos_{pos}",
                use_container_width=True,
                type=button_type,
            ):
                st.session_state.draft_position_filter = pos
                st.rerun()




def filtered_draft_pool() -> pd.DataFrame:
    pool = available_players().copy()
    selected_pos = st.session_state.draft_position_filter
    if selected_pos == "FLEX":
        pool = pool[pool["position"].isin(FLEX_POSITIONS)]
    elif selected_pos != "ALL":
        pool = pool[pool["position"] == selected_pos]
    query = clean(st.session_state.draft_search)
    if query:
        pool = pool[pool["player"].str.contains(query, case=False, na=False)]
    return pool.sort_values(["custom_rank", "rank"])




def apply_team_query_selection():
    team_id_param = st.query_params.get("team")
    if not team_id_param:
        return

    try:
        team_id = int(team_id_param)
    except (TypeError, ValueError):
        return

    match = st.session_state.teams[
        st.session_state.teams["team_id"] == team_id
    ]

    if match.empty:
        return

    team_name = clean(match.iloc[0]["team_name"])

    if team_name != clean(st.session_state.user_team):
        st.session_state.user_team = team_name
        reset_pick_clock()

    st.query_params.clear()
