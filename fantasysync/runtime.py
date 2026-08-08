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

# Safety cap so a data/logic bug can never hang the app in an infinite loop.
_MAX_CPU_PICKS_PER_RERUN = 500


def _advance_cpu_picks() -> None:
    """Resolve CPU-owned picks in order until it is the user's turn.

    A 10-team snake draft spends most picks on CPU teams; those must resolve
    automatically or the draft can never progress past the first user pick.
    """
    if not st.session_state.draft_active:
        return

    for _ in range(_MAX_CPU_PICKS_PER_RERUN):
        idx = current_open_index()
        if idx is None:
            st.session_state.draft_active = False
            return

        owner = clean(st.session_state.picks.loc[idx, "current_owner"])
        if owner == clean(st.session_state.user_team):
            start_pick_clock()
            return

        if not run_one_cpu_pick():
            return


def _render_draft_room_page() -> None:
    apply_team_query_selection()
    _advance_cpu_picks()

    idx = current_open_index()
    user_is_up = idx is not None and clean(
        st.session_state.picks.loc[idx, "current_owner"]
    ) == clean(st.session_state.user_team)

    if st.session_state.draft_active and user_is_up and st.session_state.clock_running:
        # Ticks the pick clock and re-checks for an expired timer even if the
        # user never interacts with a widget during their turn.
        st_autorefresh(interval=1000, limit=None, key="pick_clock_tick")
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
    else:
        _render_placeholder_page(route)


render_app()
