from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

import streamlit as st

from components.bottom_sheet import (
    BottomSheetDependencies,
    render_bottom_sheet,
)
from components.draft_board import render_draft_board
from components.draft_header import (
    DraftHeaderDependencies,
    render_compact_draft_header,
)


@dataclass(frozen=True)
class DraftRoomDependencies:
    """Functions supplied by the existing FantasySync draft engine."""

    current_open_index: Callable[[], Optional[int]]
    render_player_tray_css: Callable[[], None]
    render_header: Callable[[Optional[int]], None]
    clean: Callable[[Any], str]
    remaining_pick_time: Callable[[], int]
    pause_pick_clock: Callable[[], None]
    start_pick_clock: Callable[[], None]
    reset_pick_clock: Callable[[], None]
    current_user_roster: Callable[[], Any]
    player_tray_settings: Callable[[], dict]
    snake_board_html: Callable[[], str]
    move_player_tray: Callable[[int], None]
    render_player_toolbar: Callable[[], None]
    render_player_picker: Callable[..., None]
    render_queue: Callable[..., None]
    render_roster_header: Callable[[], None]
    render_roster_rows: Callable[[], None]


def _is_user_turn(
    deps: DraftRoomDependencies,
    current_index: Optional[int],
) -> bool:
    if current_index is None:
        return False

    current_owner = deps.clean(
        st.session_state.picks.loc[
            current_index,
            "current_owner",
        ]
    )
    return current_owner == deps.clean(st.session_state.user_team)


def _render_team_selector(deps: DraftRoomDependencies) -> None:
    """
    Render team selection as real Streamlit buttons.

    Team selection used to be implemented as raw HTML <a href="?team=..">
    links embedded in the draft board's HTML. Clicking a real <a href> link
    is a genuine browser page navigation, not a Streamlit rerun - it
    reloaded the entire page (every stylesheet and script from scratch) on
    every single click, which is what caused the "whole page refreshes"
    flash when selecting a team. Real st.button widgets trigger Streamlit's
    normal in-place rerun instead, with no page navigation at all.
    """
    teams = st.session_state.teams.sort_values("draft_slot")

    with st.container(key="v670_team_selector"):
        cols = st.columns(10, gap="small")

        for col, row in zip(cols, teams.itertuples()):
            slot = int(row.draft_slot)
            team_name = deps.clean(row.team_name)
            active = team_name == deps.clean(st.session_state.user_team)

            with col:
                if st.button(
                    f"{slot}. {team_name}",
                    key=f"v670_team_select_{slot}",
                    use_container_width=True,
                    type="primary" if active else "secondary",
                    disabled=active,
                ):
                    st.session_state.user_team = team_name
                    deps.reset_pick_clock()
                    st.rerun()


def render_draft_room(
    deps: DraftRoomDependencies,
) -> None:
    """
    Render Draft Room 2.0.

    Phase 2 separates the board and tray into independent layers:
    - board: fixed-height R1-R16 internal scroll viewport
    - tray: fixed Sleeper-style bottom sheet with three snap positions
    """

    current_index = deps.current_open_index()
    render_compact_draft_header(
        DraftHeaderDependencies(
            clean=deps.clean,
            remaining_pick_time=deps.remaining_pick_time,
            pause_pick_clock=deps.pause_pick_clock,
            start_pick_clock=deps.start_pick_clock,
        ),
        current_index,
    )

    if st.session_state.draft_message:
        with st.container(key="v63_draft_message"):
            st.caption(st.session_state.draft_message)

    user_turn = _is_user_turn(deps, current_index)

    _render_team_selector(deps)

    render_draft_board(deps.snake_board_html)

    render_bottom_sheet(
        BottomSheetDependencies(
            render_player_toolbar=deps.render_player_toolbar,
            render_player_picker=deps.render_player_picker,
            render_queue=deps.render_queue,
            render_roster_header=deps.render_roster_header,
            render_roster_rows=deps.render_roster_rows,
            current_user_roster=deps.current_user_roster,
            clean=deps.clean,
        ),
        current_index=current_index,
        user_turn=user_turn,
    )
