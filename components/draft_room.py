from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional

import streamlit as st


@dataclass(frozen=True)
class DraftRoomDependencies:
    """Functions supplied by the existing FantasySync draft engine."""

    current_open_index: Callable[[], Optional[int]]
    render_player_tray_css: Callable[[], None]
    render_header: Callable[[Optional[int]], None]
    clean: Callable[[Any], str]
    player_tray_settings: Callable[[], Mapping[str, Any]]
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
    user_team = deps.clean(st.session_state.user_team)
    return current_owner == user_team


def _render_board(
    deps: DraftRoomDependencies,
    tray_settings: Mapping[str, Any],
) -> None:
    """Render the full-width, internally scrollable board."""

    board_height = int(tray_settings["board_height"])

    with st.container(key="v53_top_workspace"):
        with st.container(
            height=board_height,
            border=False,
            key="v53_board_panel",
        ):
            st.markdown(
                deps.snake_board_html(),
                unsafe_allow_html=True,
            )


def _render_tray_controls(
    deps: DraftRoomDependencies,
) -> None:
    """Render Sleeper-style snap controls between board and tray."""

    with st.container(key="v62_tray_controls"):
        _, up_col, label_col, down_col, _ = st.columns(
            [5.0, 0.55, 1.55, 0.55, 5.0],
            gap="small",
        )

        with up_col:
            st.button(
                "▲",
                key="v62_raise_tray",
                help="Show more players",
                disabled=st.session_state.player_tray_level >= 2,
                on_click=deps.move_player_tray,
                args=(1,),
                use_container_width=True,
            )

        with label_col:
            st.markdown(
                '<div class="v62-tray-label">PLAYER TRAY</div>',
                unsafe_allow_html=True,
            )

        with down_col:
            st.button(
                "▼",
                key="v62_lower_tray",
                help="Show more draft board",
                disabled=st.session_state.player_tray_level <= 0,
                on_click=deps.move_player_tray,
                args=(-1,),
                use_container_width=True,
            )


def _render_player_browser(
    deps: DraftRoomDependencies,
    current_index: Optional[int],
    user_turn: bool,
    tray_settings: Mapping[str, Any],
) -> None:
    with st.container(key="v61_player_toolbar"):
        deps.render_player_toolbar()

    if current_index is None:
        st.success("Draft complete.")
        return

    deps.render_player_picker(
        current_index,
        allow_draft=user_turn,
        list_height_override=int(
            tray_settings["player_height"]
        ),
    )


def _render_utility_panel(
    deps: DraftRoomDependencies,
    current_index: Optional[int],
    user_turn: bool,
) -> None:
    """Render Queue and Roster as tabs inside one compact panel."""

    with st.container(key="v621_utility_panel"):
        queue_tab, roster_tab = st.tabs(
            [
                f"QUEUE ({len(st.session_state.player_queue)})",
                "ROSTER",
            ]
        )

        with queue_tab:
            if current_index is None:
                st.caption("Draft complete.")
            else:
                deps.render_queue(
                    current_index,
                    allow_draft=user_turn,
                )

        with roster_tab:
            deps.render_roster_header()
            deps.render_roster_rows()


def _render_player_tray(
    deps: DraftRoomDependencies,
    current_index: Optional[int],
    user_turn: bool,
    tray_settings: Mapping[str, Any],
) -> None:
    """Render the separated player tray below the board."""

    with st.container(key="v53_bottom_workspace"):
        player_col, utility_col = st.columns(
            [6.65, 2.35],
            gap="small",
        )

        with player_col:
            _render_player_browser(
                deps,
                current_index,
                user_turn,
                tray_settings,
            )

        with utility_col:
            _render_utility_panel(
                deps,
                current_index,
                user_turn,
            )


def render_draft_room(
    deps: DraftRoomDependencies,
) -> None:
    """
    Render the FantasySync Draft Room.

    Phase 1 intentionally extracts layout only. Draft state, CPU selection,
    autorefresh, pick logic, queue behavior, roster assignment, and styling
    remain owned by the existing application.
    """

    current_index = deps.current_open_index()
    deps.render_player_tray_css()
    deps.render_header(current_index)

    if st.session_state.draft_message:
        with st.container(key="v621_draft_message"):
            st.caption(st.session_state.draft_message)

    user_turn = _is_user_turn(deps, current_index)
    tray_settings = deps.player_tray_settings()

    _render_board(deps, tray_settings)
    _render_tray_controls(deps)
    _render_player_tray(
        deps,
        current_index,
        user_turn,
        tray_settings,
    )
