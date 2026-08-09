"""FantasySync Streamlit runtime: session init, navigation, and page dispatch.

Executed fresh on every Streamlit rerun by ``fantasysync.entrypoint``. This is
the module that actually draws the app; the individual page/component
modules (``fantasysync.draft_engine``, ``fantasysync.app_state``,
``fantasysync.player_pool``, ``components.*``) only expose functions and are
never invoked on their own.
"""
from __future__ import annotations

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from components import DraftRoomDependencies, render_draft_room
from components.draft_room_widgets import (
    current_user_roster,
    render_live_roster_header,
    render_live_roster_rows,
    render_player_picker_table,
    render_queue_panel,
    render_v53_header,
    render_v61_player_toolbar,
)
from fantasysync.app_state import (
    clean,
    init_state,
    move_player_tray,
    player_tray_settings,
    render_dynamic_dock_css,
    render_player_tray_css,
)
from fantasysync.draft_engine import (
    auto_pick_user_if_expired,
    current_open_index,
    pause_pick_clock,
    rebuild_draft,
    remaining_pick_time,
    reset_pick_clock,
    run_one_cpu_pick,
    serializable_state,
    snake_board_html,
    start_pick_clock,
)
from fantasysync.navigation import render_top_navigation
from fantasysync.player_pool import apply_team_query_selection
from fantasysync.rankings_sources import get_stats_season_label

# Milliseconds between each revealed CPU pick, for the ticker effect.
_CPU_TICKER_INTERVAL_MS = 900


def _tick_cpu_draft() -> None:
    """Reveal CPU-owned picks one at a time, ticker-style.

    A 10-team snake draft spends most picks on CPU teams. Resolving all of
    them in a single instant batch felt jarring, so this reveals exactly one
    CPU pick per rerun and, if more CPU picks remain before the user's next
    turn, schedules a quick autorefresh to reveal the next one. Once the open
    pick belongs to the user, it starts their pick clock and stops ticking.
    """
    if not st.session_state.draft_active:
        return

    idx = current_open_index()
    if idx is None:
        st.session_state.draft_active = False
        return

    owner = clean(st.session_state.picks.loc[idx, "current_owner"])
    if owner == clean(st.session_state.user_team):
        start_pick_clock()
        return

    run_one_cpu_pick()

    next_idx = current_open_index()
    if next_idx is None:
        st.session_state.draft_active = False
        return

    next_owner = clean(st.session_state.picks.loc[next_idx, "current_owner"])
    if next_owner == clean(st.session_state.user_team):
        start_pick_clock()
    else:
        with st.container(key="cpu_autorefresh_mount"):
            st_autorefresh(interval=_CPU_TICKER_INTERVAL_MS, limit=None, key="cpu_ticker")


def _render_draft_room_page() -> None:
    apply_team_query_selection()
    _tick_cpu_draft()

    idx = current_open_index()
    user_is_up = idx is not None and clean(
        st.session_state.picks.loc[idx, "current_owner"]
    ) == clean(st.session_state.user_team)

    if st.session_state.draft_active and user_is_up and st.session_state.clock_running:
        # Ticks the pick clock and re-checks for an expired timer even if the
        # user never interacts with a widget during their turn. This page is
        # widget-heavy (a ~100-row player table), so a full rerender is not
        # cheap - refresh every few seconds rather than every second to keep
        # the tab responsive.
        with st.container(key="cpu_autorefresh_mount"):
            st_autorefresh(interval=3000, limit=None, key="pick_clock_tick")
        if auto_pick_user_if_expired():
            st.rerun()

    render_draft_room(
        DraftRoomDependencies(
            current_open_index=current_open_index,
            render_player_tray_css=render_player_tray_css,
            render_header=render_v53_header,
            clean=clean,
            remaining_pick_time=remaining_pick_time,
            pause_pick_clock=pause_pick_clock,
            start_pick_clock=start_pick_clock,
            reset_pick_clock=reset_pick_clock,
            current_user_roster=current_user_roster,
            player_tray_settings=player_tray_settings,
            snake_board_html=snake_board_html,
            move_player_tray=move_player_tray,
            render_player_toolbar=render_v61_player_toolbar,
            render_player_picker=render_player_picker_table,
            render_queue=render_queue_panel,
            render_roster_header=render_live_roster_header,
            render_roster_rows=render_live_roster_rows,
        )
    )


def _render_rankings_page() -> None:
    """Full player list with live ADP/bye - the same st.session_state.players
    the Draft Room's player tray reads from, so the two pages can never show
    inconsistent data within a session."""
    st.header("Rankings & ADP")
    stats_season = get_stats_season_label()
    stats_note = (
        f" Rush/Rec/Pass Yds and Proj Pts are {stats_season} season stats via "
        "[nflverse](https://github.com/nflverse/nflverse-data) until a FantasyPros "
        "key is configured, then switch to forward projections automatically."
        if stats_season
        else ""
    )
    st.caption(
        "ADP and bye weeks refresh automatically every few hours. "
        "Live ADP via [Fantasy Football Calculator](https://fantasyfootballcalculator.com/adp)."
        + stats_note
    )

    players = st.session_state.players.copy()

    search_col, pos_col = st.columns([2, 3])
    with search_col:
        query = st.text_input(
            "Search players",
            key="rankings_search",
            placeholder="Search players...",
            label_visibility="collapsed",
        )
    with pos_col:
        selected_pos = st.radio(
            "Position",
            ["ALL", "QB", "RB", "WR", "TE"],
            key="rankings_position_filter",
            horizontal=True,
            label_visibility="collapsed",
        )

    if query:
        players = players[players["player"].str.contains(query, case=False, na=False)]
    if selected_pos != "ALL":
        players = players[players["position"] == selected_pos]

    players = players.sort_values(["custom_rank", "rank"])

    display = players[["custom_rank", "player", "position", "nfl_team", "tier", "consensus_adp"]].rename(
        columns={
            "custom_rank": "Rank",
            "player": "Player",
            "position": "Pos",
            "nfl_team": "Team",
            "tier": "Tier",
            "consensus_adp": "ADP",
        }
    )
    if "bye" in players.columns:
        display["Bye"] = players["bye"]
    for col, label in [
        ("proj_pts", "Proj Pts"),
        ("rush_yds", "Rush Yds"),
        ("rec_yds", "Rec Yds"),
        ("pass_yds", "Pass Yds"),
    ]:
        if col in players.columns and players[col].notna().any():
            display[label] = players[col]

    st.dataframe(display, width="stretch", hide_index=True, height=600)


def _render_placeholder_page(route: str) -> None:
    st.header(route)
    st.info(
        f"The “{route}” page has not been built yet. "
        "Only Draft Room is implemented today."
    )


def render_app() -> None:
    init_state()
    render_dynamic_dock_css()

    route = render_top_navigation(
        rebuild_draft=rebuild_draft,
        serializable_state=serializable_state,
    )

    if route == "Draft Room":
        _render_draft_room_page()
    elif route == "Rankings & ADP":
        _render_rankings_page()
    else:
        _render_placeholder_page(route)
