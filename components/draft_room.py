from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

import streamlit as st

from components.bottom_sheet import (
    BottomSheetDependencies,
    render_bottom_sheet,
)
from components.draft_board import render_draft_board


@dataclass(frozen=True)
class DraftRoomDependencies:
    """Functions supplied by the existing FantasySync draft engine."""

    current_open_index: Callable[[], Optional[int]]
    render_player_tray_css: Callable[[], None]
    render_header: Callable[[Optional[int]], None]
    clean: Callable[[Any], str]
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
    deps.render_header(current_index)

    if st.session_state.draft_message:
        with st.container(key="v63_draft_message"):
            st.caption(st.session_state.draft_message)

    user_turn = _is_user_turn(deps, current_index)

    render_draft_board(deps.snake_board_html)

    render_bottom_sheet(
        BottomSheetDependencies(
            render_player_toolbar=deps.render_player_toolbar,
            render_player_picker=deps.render_player_picker,
            render_queue=deps.render_queue,
            render_roster_header=deps.render_roster_header,
            render_roster_rows=deps.render_roster_rows,
        ),
        current_index=current_index,
        user_turn=user_turn,
    )
