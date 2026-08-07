from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any, Callable, Optional

import streamlit as st
import streamlit.components.v1 as components


TRAY_LEVELS = {
    # Nearly the entire board is visible. Queue, roster, and players are hidden.
    0: {
        "name": "Collapsed",
        "height": 46,
        "player_height": 0,
    },
    # Primary drafting state: roughly seven board rows remain visible.
    1: {
        "name": "Draft",
        "height": 258,
        "player_height": 138,
    },
    # Player-focused state: roughly five board rows remain visible.
    2: {
        "name": "Expanded",
        "height": 392,
        "player_height": 265,
    },
}


@dataclass(frozen=True)
class BottomSheetDependencies:
    render_player_toolbar: Callable[[], None]
    render_player_picker: Callable[..., None]
    render_queue: Callable[..., None]
    render_roster_header: Callable[[], None]
    render_roster_rows: Callable[[], None]
    current_user_roster: Callable[[], Any]
    clean: Callable[[Any], str]



def _roster_slot_group(slot: str) -> str:
    upper = str(slot).upper()
    if upper.startswith("QB"):
        return "QB"
    if upper.startswith("RB"):
        return "RB"
    if upper.startswith("WR"):
        return "WR"
    if upper.startswith("TE"):
        return "TE"
    return "BN"


def _render_isolated_roster(
    deps: BottomSheetDependencies,
    viewport_height: int,
) -> None:
    """
    Render all roster slots inside an isolated HTML document.

    Keeping this implementation inside bottom_sheet.py removes the obsolete
    v6.4.0 roster renderer from the active dependency path.
    """
    roster = deps.current_user_roster()
    filled = int((roster["Player"].astype(str) != "").sum())
    team = escape(deps.clean(st.session_state.user_team))

    rows: list[str] = []
    for row in roster.itertuples():
        player = deps.clean(row.Player)
        slot = deps.clean(row.Slot)
        pos = deps.clean(row.Pos)
        group = _roster_slot_group(slot)

        if player:
            content = (
                f'<span class="player">{escape(player)}</span>'
                f'<span class="pos">({escape(pos)})</span>'
            )
        else:
            content = '<span class="empty">Empty</span>'

        rows.append(
            f'<div class="row">'
            f'<span class="slot slot-{group}">{escape(slot)}</span>'
            f'<span class="content">{content}</span>'
            f'</div>'
        )

    html = f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        * {{ box-sizing: border-box; }}
        html, body {{
          width: 100%;
          height: 100%;
          margin: 0;
          padding: 0;
          overflow: hidden;
          background: #101D2E;
          color: #F8FAFC;
          font-family: Inter, ui-sans-serif, system-ui, -apple-system,
            BlinkMacSystemFont, "Segoe UI", sans-serif;
        }}
        .card {{
          width: 100%;
          height: {int(viewport_height)}px;
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }}
        .heading {{
          flex: 0 0 36px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 2px 5px 7px;
          border-bottom: 1px solid rgba(148,163,184,.18);
        }}
        .team {{
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          font-size: 13px;
          font-weight: 800;
        }}
        .count {{
          flex: 0 0 auto;
          margin-left: 8px;
          color: #B8C4D5;
          font-size: 10px;
          font-weight: 700;
        }}
        .scroll {{
          flex: 1 1 auto;
          min-height: 0;
          overflow-y: scroll;
          overflow-x: hidden;
          overscroll-behavior: contain;
          scrollbar-gutter: stable;
          scrollbar-width: thin;
          scrollbar-color: #60728F #101D2E;
          padding-right: 4px;
        }}
        .scroll::-webkit-scrollbar {{ width: 7px; }}
        .scroll::-webkit-scrollbar-track {{ background: #101D2E; }}
        .scroll::-webkit-scrollbar-thumb {{
          background: #60728F;
          border-radius: 999px;
        }}
        .row {{
          min-height: 32px;
          display: grid;
          grid-template-columns: 40px minmax(0, 1fr);
          align-items: center;
          gap: 8px;
          border-bottom: 1px solid rgba(148,163,184,.13);
        }}
        .slot {{
          width: 36px;
          height: 23px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          border-radius: 5px;
          color: #FFFFFF;
          font-size: 10px;
          font-weight: 800;
        }}
        .slot-QB {{ background: #7D55C7; }}
        .slot-RB {{ background: #47A368; }}
        .slot-WR {{ background: #3E7DE0; }}
        .slot-TE {{ background: #EA9848; }}
        .slot-BN {{ background: #69758A; }}
        .content {{
          min-width: 0;
          display: flex;
          align-items: baseline;
          gap: 5px;
          overflow: hidden;
          white-space: nowrap;
        }}
        .player {{
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          font-size: 12px;
          font-weight: 750;
        }}
        .pos {{
          flex: 0 0 auto;
          color: #9EABC0;
          font-size: 9px;
        }}
        .empty {{
          color: #8E9BB0;
          font-size: 11px;
        }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="heading">
          <span class="team">{team}</span>
          <span class="count">{filled} / 16 players</span>
        </div>
        <div class="scroll">{''.join(rows)}</div>
      </div>
    </body>
    </html>
    """

    components.html(
        html,
        height=int(viewport_height),
        scrolling=False,
    )



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


def _current_utility_view() -> str:
    """
    Return the persistent utility-panel view.

    Streamlit tabs reset during frequent CPU reruns. A session-state-backed
    view remains selected while CPU picks continue.
    """
    view = str(
        st.session_state.get(
            "v632_utility_view",
            "queue",
        )
    ).lower()

    if view not in {"queue", "roster"}:
        view = "queue"

    st.session_state.v632_utility_view = view
    return view


def set_utility_view(view: str) -> None:
    normalized = str(view).lower()
    if normalized in {"queue", "roster"}:
        st.session_state.v632_utility_view = normalized


def _render_sheet_css(level: int) -> None:
    settings = TRAY_LEVELS[level]
    sheet_height = int(settings["height"])
    player_height = int(settings["player_height"])
    sheet_visible = "block"
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

        /*
         * Persistent tray controls are rendered inside the fixed bottom sheet.
         * This avoids clipping by Streamlit's outer wrappers.
         */
        .st-key-v647_tray_controls {{
            position: absolute !important;
            top: 4px !important;
            right: 176px !important;
            z-index: 10080 !important;
            width: 86px !important;
            height: 38px !important;
            min-height: 38px !important;
            max-height: 38px !important;
            margin: 0 !important;
            padding: 0 !important;
            background: transparent !important;
            border: 0 !important;
            pointer-events: none !important;
        }}

        .st-key-v647_tray_controls
            [data-testid="stHorizontalBlock"] {{
            width: 86px !important;
            height: 38px !important;
            min-height: 38px !important;
            gap: 6px !important;
            align-items: center !important;
            justify-content: flex-end !important;
            margin: 0 !important;
            padding: 0 !important;
            pointer-events: none !important;
        }}

        .st-key-v647_tray_controls
            [data-testid="stColumn"] {{
            width: 38px !important;
            min-width: 38px !important;
            max-width: 38px !important;
            flex: 0 0 38px !important;
            pointer-events: auto !important;
        }}

        .st-key-v647_tray_controls button {{
            width: 38px !important;
            min-width: 38px !important;
            max-width: 38px !important;
            height: 38px !important;
            min-height: 38px !important;
            max-height: 38px !important;
            padding: 0 !important;
            border-radius: 999px !important;
            border: 1px solid rgba(151,166,190,.42) !important;
            background: rgba(84,99,126,.66) !important;
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
            backdrop-filter: blur(10px) !important;
            -webkit-backdrop-filter: blur(10px) !important;
            box-shadow:
                0 4px 14px rgba(0,0,0,.30),
                inset 0 1px 0 rgba(255,255,255,.10) !important;
            opacity: 1 !important;
            pointer-events: auto !important;
            z-index: 10081 !important;
        }}

        .st-key-v647_tray_controls button * {{
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
        }}

        .st-key-v647_tray_controls button:hover {{
            background: rgba(108,124,155,.84) !important;
            border-color: rgba(194,205,225,.62) !important;
        }}

        .st-key-v647_tray_controls button:disabled {{
            opacity: .28 !important;
        }}

        body:has(section[data-testid="stSidebar"][aria-expanded="true"])
            .st-key-v647_tray_controls {{
            right: 188px !important;
        }}

        body:has(section[data-testid="stSidebar"][aria-expanded="false"])
            .st-key-v647_tray_controls {{
            right: 176px !important;
        }}

        /*
         * True fixed bottom sheet. It overlays the board and never participates
         * in normal Streamlit page flow.
         */
        .st-key-v63_bottom_sheet {{
            display: {sheet_visible} !important;
            position: fixed !important;
            pointer-events: auto !important;
            left: var(--fs-sidebar-width) !important;
            right: 0 !important;
            bottom: 0 !important;
            z-index: 10010 !important;
            height: {sheet_height}px !important;
            transition:
                height 180ms ease,
                left 180ms ease !important;
            min-height: {sheet_height}px !important;
            max-height: {sheet_height}px !important;
            margin: 0 !important;
            padding: 10px 12px 12px !important;
            box-sizing: border-box !important;
            overflow: hidden !important;
            background: #0B1625 !important;
            isolation: isolate !important;
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
            min-height: 34px !important;
            height: 34px !important;
            padding: 0 !important;
            align-items: center !important;
        }}

        .st-key-v63_bottom_sheet
            .st-key-war_player_list
            [data-testid="stColumn"] {{
            min-height: 34px !important;
            height: 34px !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }}

        .st-key-v63_bottom_sheet .player-name2 {{
            font-size: .70rem !important;
            line-height: 1.08 !important;
            font-weight: 780 !important;
            color: #F8FAFC !important;
            -webkit-text-fill-color: #F8FAFC !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }}

        .st-key-v63_bottom_sheet .player-sub2 {{
            font-size: .50rem !important;
            line-height: 1.02 !important;
            margin-top: 2px !important;
            color: #91A2B9 !important;
            -webkit-text-fill-color: #91A2B9 !important;
        }}

        .st-key-v63_bottom_sheet .stat2,
        .st-key-v63_bottom_sheet .rank2 {{
            font-size: .57rem !important;
            line-height: 1 !important;
            color: #CFD8E6 !important;
            -webkit-text-fill-color: #CFD8E6 !important;
        }}

        .st-key-v63_bottom_sheet
            .st-key-war_player_list button {{
            width: 24px !important;
            min-width: 24px !important;
            height: 24px !important;
            min-height: 24px !important;
            padding: 0 !important;
            font-size: .69rem !important;
        }}

        .st-key-v63_bottom_sheet .value-badge {{
            height: 20px !important;
            min-width: 26px !important;
            font-size: .49rem !important;
        }}

        .st-key-v63_bottom_sheet .player-row-divider {{
            margin: 0 !important;
            background: rgba(148,163,184,.12) !important;
        }}

        .st-key-v63_bottom_sheet .player-table-header2 {{
            min-height: 23px !important;
            height: 23px !important;
            font-size: .49rem !important;
            line-height: 1 !important;
        }}

        .st-key-v63_utility_side {{
            overflow: hidden !important;
            pointer-events: auto !important;
        }}

        .st-key-v63_utility_side .roster-line {{
            min-height: 27px !important;
            padding: 0 !important;
        }}

        .st-key-v63_utility_side .roster-slot-pill {{
            height: 20px !important;
        }}

        .st-key-v63_utility_side button {{
            min-height: 26px !important;
            height: 26px !important;
            padding: 0 6px !important;
            font-size: .52rem !important;
        }}

        /*
         * Persistent Queue / Roster buttons remain clickable and selected
         * through rapid CPU reruns.
         */
        .st-key-v63_utility_side
            > div
            > div
            > [data-testid="stVerticalBlock"] {{
            gap: 5px !important;
        }}

        .st-key-v63_utility_side
            [data-testid="stHorizontalBlock"]:first-of-type {{
            min-height: 31px !important;
            height: 31px !important;
            gap: 5px !important;
            border-bottom: 1px solid rgba(148,163,184,.15) !important;
            padding-bottom: 4px !important;
        }}

        .st-key-v63_utility_side
            [data-testid="stHorizontalBlock"]:first-of-type button {{
            min-height: 27px !important;
            height: 27px !important;
            font-size: .55rem !important;
            font-weight: 850 !important;
            letter-spacing: .01em !important;
            border-radius: 6px !important;
            pointer-events: auto !important;
            position: relative !important;
            z-index: 10040 !important;
        }}

        /*
         * The utility content owns its own vertical scrollbar. This allows the
         * complete roster to be inspected without scrolling the page or board.
         */
        .st-key-v632_utility_content {{
            min-height: 0 !important;
            overflow: visible !important;
        }}

        .st-key-v632_utility_content
            [data-testid="stVerticalBlockBorderWrapper"] {{
            height: 100% !important;
            max-height: 100% !important;
            min-height: 0 !important;
            overflow-y: hidden !important;
            overflow-x: hidden !important;
            overscroll-behavior: contain !important;
            scrollbar-gutter: stable !important;
            -webkit-overflow-scrolling: touch !important;
            scrollbar-width: thin !important;
            scrollbar-color: #53647F #101D2E !important;
        }}

        .st-key-v632_utility_content
            [data-testid="stVerticalBlockBorderWrapper"]
            > div,
        .st-key-v632_utility_content
            [data-testid="stVerticalBlock"] {{
            height: auto !important;
            max-height: none !important;
            min-height: 0 !important;
            overflow: visible !important;
        }}

        .st-key-v632_utility_content
            [data-testid="stVerticalBlockBorderWrapper"]
            ::-webkit-scrollbar {{
            width: 7px !important;
        }}

        .st-key-v632_utility_content
            [data-testid="stVerticalBlockBorderWrapper"]
            ::-webkit-scrollbar-track {{
            background: #101D2E !important;
        }}

        .st-key-v632_utility_content
            [data-testid="stVerticalBlockBorderWrapper"]
            ::-webkit-scrollbar-thumb {{
            background: #53647F !important;
            border-radius: 999px !important;
        }}

        .st-key-v632_utility_content
            [data-testid="stVerticalBlockBorderWrapper"]
            ::-webkit-scrollbar-thumb:hover {{
            background: #7085A5 !important;
        }}

        .st-key-v633_roster_scroll {{
            min-height: 0 !important;
            overflow: visible !important;
        }}

        .st-key-v633_roster_scroll
            [data-testid="stVerticalBlockBorderWrapper"] {{
            height: 100% !important;
            max-height: 100% !important;
            min-height: 0 !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            overscroll-behavior: contain !important;
            scrollbar-gutter: stable !important;
            -webkit-overflow-scrolling: touch !important;
            scrollbar-width: thin !important;
            scrollbar-color: #60728F #101D2E !important;
        }}

        .st-key-v633_roster_scroll
            [data-testid="stVerticalBlockBorderWrapper"]
            > div,
        .st-key-v633_roster_scroll
            [data-testid="stVerticalBlock"] {{
            height: auto !important;
            max-height: none !important;
            min-height: max-content !important;
            overflow: visible !important;
        }}

        .st-key-v633_roster_scroll
            [data-testid="stVerticalBlockBorderWrapper"]
            ::-webkit-scrollbar {{
            width: 7px !important;
        }}

        .st-key-v633_roster_scroll
            [data-testid="stVerticalBlockBorderWrapper"]
            ::-webkit-scrollbar-track {{
            background: #101D2E !important;
        }}

        .st-key-v633_roster_scroll
            [data-testid="stVerticalBlockBorderWrapper"]
            ::-webkit-scrollbar-thumb {{
            background: #60728F !important;
            border-radius: 999px !important;
        }}

        .st-key-v633_roster_scroll
            [data-testid="stVerticalBlockBorderWrapper"]
            ::-webkit-scrollbar-thumb:hover {{
            background: #7B90B0 !important;
        }}

        .st-key-v633_roster_scroll .roster-header-row,
        .st-key-v633_roster_scroll .roster-line {{
            position: relative !important;
            top: auto !important;
            bottom: auto !important;
            transform: none !important;
            flex-shrink: 0 !important;
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
    """Render persistent tray arrows inside the fixed bottom sheet."""
    with st.container(key="v647_tray_controls"):
        up_col, down_col = st.columns([1, 1], gap="small")

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
        active_view = _current_utility_view()

        queue_col, roster_col = st.columns(
            [1, 1],
            gap="small",
        )

        with queue_col:
            st.button(
                f"QUEUE ({len(st.session_state.player_queue)})",
                key="v632_queue_view",
                type=(
                    "primary"
                    if active_view == "queue"
                    else "secondary"
                ),
                on_click=set_utility_view,
                args=("queue",),
                use_container_width=True,
            )

        with roster_col:
            st.button(
                "ROSTER",
                key="v632_roster_view",
                type=(
                    "primary"
                    if active_view == "roster"
                    else "secondary"
                ),
                on_click=set_utility_view,
                args=("roster",),
                use_container_width=True,
            )

        # Read state again because a button callback executes before rendering.
        active_view = _current_utility_view()

        with st.container(
            height=(
                210
                if _current_level() == 1
                else 340
            ),
            border=False,
            key="v632_utility_content",
        ):
            if active_view == "queue":
                if current_index is None:
                    st.caption("Draft complete.")
                else:
                    deps.render_queue(
                        current_index,
                        allow_draft=user_turn,
                    )
            else:
                _render_isolated_roster(
                    deps=deps,
                    viewport_height=(
                        164
                        if _current_level() == 1
                        else 292
                    ),
                )


def render_bottom_sheet(
    deps: BottomSheetDependencies,
    current_index: Optional[int],
    user_turn: bool,
) -> None:
    level = _current_level()
    settings = TRAY_LEVELS[level]
    _render_sheet_css(level)

    with st.container(key="v63_bottom_sheet"):
        _render_handle(level)

        # Collapsed state is a thin dock containing only the arrows.
        if level == 0:
            return

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
