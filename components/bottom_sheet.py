from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import streamlit as st


TRAY_LEVELS = {
    0: {
        "name": "Collapsed",
        "height": 0,
        "player_height": 0,
    },
    1: {
        "name": "Draft",
        "height": 342,
        "player_height": 218,
    },
    2: {
        "name": "Expanded",
        "height": 610,
        "player_height": 475,
    },
}


@dataclass(frozen=True)
class BottomSheetDependencies:
    render_player_toolbar: Callable[[], None]
    render_player_picker: Callable[..., None]
    render_queue: Callable[..., None]
    render_roster_header: Callable[[], None]
    render_roster_rows: Callable[[], None]


def _current_level() -> int:
    level = int(st.session_state.get("player_tray_level", 1))
    level = max(0, min(2, level))
    st.session_state.player_tray_level = level
    return level


def change_tray_level(direction: int) -> None:
    current = _current_level()
    st.session_state.player_tray_level = max(
        0,
        min(2, current + direction),
    )


def _render_sheet_css(level: int) -> None:
    settings = TRAY_LEVELS[level]
    sheet_height = int(settings["height"])
    player_height = int(settings["player_height"])
    sheet_visible = "none" if level == 0 else "block"
    handle_bottom = sheet_height

    st.markdown(
        f"""
        <style>
        :root {{
            --fs-sidebar-width: 13.7rem;
            --fs-sheet-height: {sheet_height}px;
        }}

        /*
         * Board remains independent. The bottom sheet overlays it instead of
         * pushing or resizing it.
         */
        .st-key-v63_board_region {{
            position: relative !important;
            z-index: 1 !important;
            width: 100% !important;
            margin: 0 !important;
            padding: 0 0 20px !important;
        }}

        .st-key-v63_board_scroll {{
            height: calc(100vh - 145px) !important;
            max-height: calc(100vh - 145px) !important;
            min-height: 430px !important;
            overflow: visible !important;
        }}

        .st-key-v63_board_scroll
            [data-testid="stVerticalBlockBorderWrapper"] {{
            height: calc(100vh - 145px) !important;
            max-height: calc(100vh - 145px) !important;
            min-height: 430px !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            overscroll-behavior: contain !important;
            scrollbar-gutter: stable !important;
            -webkit-overflow-scrolling: touch !important;
            scrollbar-width: thin !important;
            scrollbar-color: #465671 #091321 !important;
        }}

        .st-key-v63_board_scroll
            [data-testid="stVerticalBlockBorderWrapper"] > div,
        .st-key-v63_board_scroll
            [data-testid="stVerticalBlock"],
        .st-key-v63_board_scroll
            [data-testid="stMarkdownContainer"],
        .st-key-v63_board_scroll
            [data-testid="stMarkdownContainer"] > div {{
            height: auto !important;
            max-height: none !important;
            min-height: 0 !important;
            overflow: visible !important;
        }}

        .st-key-v63_board_scroll
            [data-testid="stVerticalBlockBorderWrapper"]
            ::-webkit-scrollbar {{
            width: 7px !important;
        }}

        .st-key-v63_board_scroll
            [data-testid="stVerticalBlockBorderWrapper"]
            ::-webkit-scrollbar-track {{
            background: #091321 !important;
        }}

        .st-key-v63_board_scroll
            [data-testid="stVerticalBlockBorderWrapper"]
            ::-webkit-scrollbar-thumb {{
            background: #465671 !important;
            border-radius: 999px !important;
        }}

        /*
         * Fixed tray handle. It sits directly above the sheet and remains
         * visible when the sheet is collapsed.
         */
        .st-key-v63_sheet_handle {{
            position: fixed !important;
            left: var(--fs-sidebar-width) !important;
            right: 0 !important;
            bottom: {handle_bottom}px !important;
            z-index: 10020 !important;
            height: 38px !important;
            min-height: 38px !important;
            max-height: 38px !important;
            margin: 0 !important;
            padding: 0 !important;
            background: #081321 !important;
            border-top: 2px solid #7C5CE0 !important;
            border-bottom: 1px solid rgba(148,163,184,.20) !important;
            box-shadow: none !important;
        }}

        body:has(
            section[data-testid="stSidebar"][aria-expanded="false"]
        ) .st-key-v63_sheet_handle {{
            left: 0 !important;
        }}

        .st-key-v63_sheet_handle
            [data-testid="stHorizontalBlock"] {{
            height: 36px !important;
            min-height: 36px !important;
            align-items: center !important;
            justify-content: flex-end !important;
            gap: .22rem !important;
            padding-right: 8px !important;
        }}

        .st-key-v63_sheet_handle button {{
            min-height: 28px !important;
            height: 28px !important;
            padding: 0 !important;
            border-radius: 8px !important;
            background: #1C2739 !important;
            border: 1px solid #4B5B74 !important;
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
            box-shadow: none !important;
        }}

        .st-key-v63_sheet_handle button:hover {{
            background: #27354A !important;
            border-color: #846CE0 !important;
        }}

        .st-key-v63_sheet_handle button:disabled {{
            opacity: .34 !important;
        }}

        /*
         * True fixed bottom sheet. It overlays the board and never participates
         * in normal Streamlit page flow.
         */
        .st-key-v63_bottom_sheet {{
            display: {sheet_visible} !important;
            position: fixed !important;
            left: var(--fs-sidebar-width) !important;
            right: 0 !important;
            bottom: 0 !important;
            z-index: 10010 !important;
            height: {sheet_height}px !important;
            min-height: {sheet_height}px !important;
            max-height: {sheet_height}px !important;
            margin: 0 !important;
            padding: 10px 12px 12px !important;
            box-sizing: border-box !important;
            overflow: hidden !important;
            background: #0B1625 !important;
            border-top: 1px solid rgba(148,163,184,.25) !important;
            box-shadow: 0 -8px 24px rgba(0,0,0,.28) !important;
        }}

        body:has(
            section[data-testid="stSidebar"][aria-expanded="false"]
        ) .st-key-v63_bottom_sheet {{
            left: 0 !important;
        }}

        .st-key-v63_bottom_sheet > div,
        .st-key-v63_bottom_sheet > div > div,
        .st-key-v63_bottom_sheet
            [data-testid="stHorizontalBlock"] {{
            height: 100% !important;
            max-height: 100% !important;
            min-height: 0 !important;
        }}

        .st-key-v63_bottom_sheet
            [data-testid="stHorizontalBlock"] {{
            align-items: stretch !important;
            gap: .65rem !important;
        }}

        .st-key-v63_bottom_sheet
            [data-testid="stColumn"] {{
            height: 100% !important;
            max-height: 100% !important;
            min-height: 0 !important;
            overflow: hidden !important;
        }}

        .st-key-v63_player_side,
        .st-key-v63_utility_side {{
            height: 100% !important;
            max-height: 100% !important;
            min-height: 0 !important;
            overflow: hidden !important;
        }}

        .st-key-v63_player_side {{
            padding-right: 3px !important;
        }}

        .st-key-v63_utility_side {{
            padding: 7px 9px !important;
            border: 1px solid rgba(148,163,184,.22) !important;
            border-radius: 8px !important;
            background: #101D2E !important;
        }}

        .st-key-v63_bottom_sheet .st-key-war_player_list {{
            height: {player_height}px !important;
            max-height: {player_height}px !important;
            min-height: 0 !important;
            overflow-y: auto !important;
        }}

        /*
         * Bottom-sheet-specific typography overrides the older global compact
         * table rules. Player names remain readable in Draft and Expanded
         * states without changing draft-board card typography.
         */
        .st-key-v63_bottom_sheet
            .st-key-war_player_list
            [data-testid="stVerticalBlock"] {{
            gap: 0 !important;
        }}

        .st-key-v63_bottom_sheet
            .st-key-war_player_list
            [data-testid="stHorizontalBlock"] {{
            min-height: 38px !important;
            height: 38px !important;
            padding: 0 !important;
            align-items: center !important;
        }}

        .st-key-v63_bottom_sheet
            .st-key-war_player_list
            [data-testid="stColumn"] {{
            min-height: 38px !important;
            height: 38px !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }}

        .st-key-v63_bottom_sheet .player-name2 {{
            font-size: .76rem !important;
            line-height: 1.08 !important;
            font-weight: 780 !important;
            color: #F8FAFC !important;
            -webkit-text-fill-color: #F8FAFC !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }}

        .st-key-v63_bottom_sheet .player-sub2 {{
            font-size: .54rem !important;
            line-height: 1.05 !important;
            margin-top: 2px !important;
            color: #91A2B9 !important;
            -webkit-text-fill-color: #91A2B9 !important;
        }}

        .st-key-v63_bottom_sheet .stat2,
        .st-key-v63_bottom_sheet .rank2 {{
            font-size: .62rem !important;
            line-height: 1 !important;
            color: #CFD8E6 !important;
            -webkit-text-fill-color: #CFD8E6 !important;
        }}

        .st-key-v63_bottom_sheet
            .st-key-war_player_list button {{
            width: 27px !important;
            min-width: 27px !important;
            height: 27px !important;
            min-height: 27px !important;
            padding: 0 !important;
            font-size: .69rem !important;
        }}

        .st-key-v63_bottom_sheet .value-badge {{
            height: 22px !important;
            min-width: 28px !important;
            font-size: .53rem !important;
        }}

        .st-key-v63_bottom_sheet .player-row-divider {{
            margin: 0 !important;
            background: rgba(148,163,184,.12) !important;
        }}

        .st-key-v63_bottom_sheet .player-table-header2 {{
            min-height: 25px !important;
            height: 25px !important;
            font-size: .53rem !important;
            line-height: 1 !important;
        }}

        .st-key-v63_utility_side
            [data-testid="stTabs"] {{
            height: 100% !important;
            max-height: 100% !important;
        }}

        .st-key-v63_utility_side
            [data-testid="stTabs"] [role="tablist"] {{
            gap: 4px !important;
            margin-bottom: 5px !important;
            border-bottom: 1px solid rgba(148,163,184,.15) !important;
        }}

        .st-key-v63_utility_side
            [data-testid="stTabs"] button[role="tab"] {{
            min-height: 29px !important;
            height: 29px !important;
            padding: 0 9px !important;
            font-size: .55rem !important;
            font-weight: 800 !important;
        }}

        /* Old in-flow tray containers are no longer used. */
        .st-key-v53_bottom_workspace,
        .st-key-v62_tray_controls {{
            display: none !important;
        }}

        /* Keep the working hidden autorefresh behavior untouched. */
        .st-key-cpu_autorefresh_mount,
        .st-key-cpu_autorefresh_mount > div,
        .st-key-cpu_autorefresh_mount
            [data-testid="stVerticalBlock"],
        .st-key-cpu_autorefresh_mount
            [data-testid="stElementContainer"],
        .st-key-cpu_autorefresh_mount
            [data-testid="stCustomComponentV1"],
        .st-key-cpu_autorefresh_mount iframe {{
            display: none !important;
            visibility: hidden !important;
            position: absolute !important;
            width: 0 !important;
            height: 0 !important;
            min-width: 0 !important;
            min-height: 0 !important;
            max-width: 0 !important;
            max-height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            border: 0 !important;
            overflow: hidden !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_handle(level: int) -> None:
    """
    Render compact Sleeper-style tray arrows over the utility-panel side.

    The centered PLAYER TRAY label is intentionally removed so the divider is
    visually quieter and the controls sit above Queue / Roster.
    """
    with st.container(key="v63_sheet_handle"):
        _, up_col, down_col, trailing_space = st.columns(
            [8.55, 0.58, 0.58, 0.18],
            gap="small",
        )

        with up_col:
            st.button(
                "▲",
                key="v63_sheet_up",
                help="Show more of the player tray",
                disabled=level >= 2,
                on_click=change_tray_level,
                args=(1,),
                use_container_width=True,
            )

        with down_col:
            st.button(
                "▼",
                key="v63_sheet_down",
                help="Show more of the draft board",
                disabled=level <= 0,
                on_click=change_tray_level,
                args=(-1,),
                use_container_width=True,
            )


def _render_player_side(
    deps: BottomSheetDependencies,
    current_index: Optional[int],
    user_turn: bool,
    player_height: int,
) -> None:
    with st.container(key="v63_player_side"):
        deps.render_player_toolbar()

        if current_index is None:
            st.success("Draft complete.")
        else:
            deps.render_player_picker(
                current_index,
                allow_draft=user_turn,
                list_height_override=player_height,
            )


def _render_utility_side(
    deps: BottomSheetDependencies,
    current_index: Optional[int],
    user_turn: bool,
) -> None:
    with st.container(key="v63_utility_side"):
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


def render_bottom_sheet(
    deps: BottomSheetDependencies,
    current_index: Optional[int],
    user_turn: bool,
) -> None:
    level = _current_level()
    settings = TRAY_LEVELS[level]
    _render_sheet_css(level)
    _render_handle(level)

    # Collapsed state intentionally renders no player widgets.
    if level == 0:
        return

    with st.container(key="v63_bottom_sheet"):
        player_col, utility_col = st.columns(
            [6.65, 2.35],
            gap="small",
        )

        with player_col:
            _render_player_side(
                deps,
                current_index,
                user_turn,
                int(settings["player_height"]),
            )

        with utility_col:
            _render_utility_side(
                deps,
                current_index,
                user_turn,
            )
