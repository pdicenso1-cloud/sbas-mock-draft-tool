from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any, Callable, Optional

import streamlit as st
import streamlit.components.v1 as components


TRAY_LEVELS = {
    # Compact draft-board-first state.
    # Tuned to leave roughly five board rows visible on a typical laptop.
    0: {
        "name": "Compact",
        "height": 146,
        "player_height": 62,
        "utility_height": 78,
    },
    # Balanced drafting state.
    1: {
        "name": "Draft",
        "height": 236,
        "player_height": 146,
        "utility_height": 168,
    },
    # Player-focused state.
    # Tuned to leave roughly 2.5 draft-board rows visible.
    2: {
        "name": "Expanded",
        "height": 332,
        "player_height": 238,
        "utility_height": 264,
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

    st.markdown(
        f"""
        <style>
        :root {{
            --fs-live-sheet-height: {sheet_height}px;
        }}

        /*
         * v7.2.0 tray-only state system.
         * The draft board is intentionally not styled here.
         */
        .st-key-v660_tray {{
            display: block !important;
            position: fixed !important;
            left: 0 !important;
            right: 0 !important;
            bottom: 0 !important;
            z-index: 10010 !important;
            width: 100vw !important;
            max-width: 100vw !important;
            height: {sheet_height}px !important;
            min-height: {sheet_height}px !important;
            max-height: {sheet_height}px !important;
            margin: 0 !important;
            padding: 8px 12px 6px !important;
            box-sizing: border-box !important;
            overflow: hidden !important;
            background: #0B1625 !important;
            border-top: 1px solid rgba(124,92,224,.78) !important;
            border-bottom: 0 !important;
            box-shadow: 0 -5px 16px rgba(0,0,0,.22) !important;
            pointer-events: auto !important;
            isolation: isolate !important;
        }}

        /*
         * Floating ▲ / ▼ controls. They occupy no layout row and remain
         * centered on the tray's upper edge.
         */
        .st-key-v720_tray_controls {{
            position: fixed !important;
            left: 50% !important;
            bottom: {max(0, sheet_height - 17)}px !important;
            transform: translateX(-50%) !important;
            z-index: 10120 !important;
            width: 92px !important;
            height: 32px !important;
            min-height: 32px !important;
            max-height: 32px !important;
            margin: 0 !important;
            padding: 0 !important;
            background: transparent !important;
            border: 0 !important;
            pointer-events: none !important;
        }}

        .st-key-v720_tray_controls
            [data-testid="stHorizontalBlock"] {{
            width: 92px !important;
            height: 32px !important;
            min-height: 32px !important;
            gap: 6px !important;
            margin: 0 !important;
            padding: 0 !important;
            align-items: center !important;
            justify-content: center !important;
            pointer-events: none !important;
        }}

        .st-key-v720_tray_controls
            [data-testid="stColumn"] {{
            flex: 0 0 42px !important;
            width: 42px !important;
            min-width: 42px !important;
            max-width: 42px !important;
            height: 30px !important;
            min-height: 30px !important;
            pointer-events: auto !important;
        }}

        .st-key-v720_tray_controls button {{
            width: 42px !important;
            min-width: 42px !important;
            max-width: 42px !important;
            height: 30px !important;
            min-height: 30px !important;
            max-height: 30px !important;
            padding: 0 !important;
            border-radius: 999px !important;
            border: 1px solid rgba(151,166,190,.48) !important;
            background: rgba(45,59,81,.94) !important;
            color: #F8FAFC !important;
            -webkit-text-fill-color: #F8FAFC !important;
            font-size: .78rem !important;
            font-weight: 900 !important;
            line-height: 1 !important;
            box-shadow:
                0 3px 12px rgba(0,0,0,.30),
                inset 0 1px 0 rgba(255,255,255,.09) !important;
            pointer-events: auto !important;
        }}

        .st-key-v720_tray_controls button:hover {{
            background: rgba(72,91,121,.98) !important;
            border-color: rgba(196,210,233,.72) !important;
        }}

        .st-key-v720_tray_controls button:disabled {{
            opacity: .28 !important;
            cursor: default !important;
        }}

        /* Tray root fills its exact fixed state height. */
        .st-key-v660_tray > div,
        .st-key-v660_tray > div > div,
        .st-key-v660_tray
            > div
            > div
            > [data-testid="stVerticalBlock"] {{
            height: 100% !important;
            max-height: 100% !important;
            min-height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
        }}

        .st-key-v660_tray
            > div
            > div
            > [data-testid="stVerticalBlock"] {{
            display: flex !important;
            flex-direction: column !important;
            align-items: stretch !important;
            justify-content: flex-start !important;
            gap: 0 !important;
        }}

        .st-key-v660_tray
            > div
            > div
            > [data-testid="stVerticalBlock"]
            > [data-testid="stHorizontalBlock"] {{
            flex: 1 1 auto !important;
            width: 100% !important;
            height: 100% !important;
            max-height: 100% !important;
            min-height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            gap: .65rem !important;
            align-items: stretch !important;
            overflow: hidden !important;
        }}

        .st-key-v660_tray [data-testid="stColumn"] {{
            height: 100% !important;
            max-height: 100% !important;
            min-height: 0 !important;
            overflow: hidden !important;
        }}

        .st-key-v63_player_side,
        .st-key-v63_utility_side {{
            display: flex !important;
            flex-direction: column !important;
            height: 100% !important;
            max-height: 100% !important;
            min-height: 0 !important;
            margin: 0 !important;
            overflow: hidden !important;
            pointer-events: auto !important;
        }}

        .st-key-v63_player_side {{
            padding-right: 3px !important;
        }}

        .st-key-v63_utility_side {{
            padding: 7px 9px 4px !important;
            border: 1px solid rgba(148,163,184,.22) !important;
            border-radius: 8px !important;
            background: #101D2E !important;
        }}

        .st-key-v63_player_side > div,
        .st-key-v63_player_side > div > div,
        .st-key-v63_utility_side > div,
        .st-key-v63_utility_side > div > div {{
            height: 100% !important;
            max-height: 100% !important;
            min-height: 0 !important;
            overflow: hidden !important;
        }}

        .st-key-v63_player_side
            > div
            > div
            > [data-testid="stVerticalBlock"],
        .st-key-v63_utility_side
            > div
            > div
            > [data-testid="stVerticalBlock"] {{
            display: flex !important;
            flex-direction: column !important;
            height: 100% !important;
            max-height: 100% !important;
            min-height: 0 !important;
            gap: 0 !important;
            overflow: hidden !important;
        }}

        /* Search and position sorting controls always remain visible. */
        .st-key-v61_player_toolbar {{
            flex: 0 0 auto !important;
            min-height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: visible !important;
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
            z-index: 10030 !important;
        }}

        .st-key-v61_player_toolbar button,
        .st-key-v61_player_toolbar input {{
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
        }}

        /* Player list owns its own scroll viewport. */
        .st-key-v660_tray .st-key-war_player_list {{
            flex: 1 1 auto !important;
            min-height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
        }}

        .st-key-v660_tray
            .st-key-war_player_list
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
            scrollbar-color: #53647F #0B1625 !important;
            pointer-events: auto !important;
        }}

        .st-key-v660_tray
            .st-key-war_player_list
            [data-testid="stVerticalBlockBorderWrapper"]
            > div,
        .st-key-v660_tray
            .st-key-war_player_list
            [data-testid="stVerticalBlock"] {{
            height: auto !important;
            max-height: none !important;
            min-height: max-content !important;
            overflow: visible !important;
        }}

        .st-key-v660_tray
            .st-key-war_player_list
            [data-testid="stVerticalBlock"] {{
            gap: 0 !important;
        }}

        .st-key-v660_tray
            .st-key-war_player_list
            [data-testid="stHorizontalBlock"] {{
            min-height: 34px !important;
            height: 34px !important;
            padding: 0 !important;
            align-items: center !important;
            border: 0 !important;
            box-shadow: none !important;
        }}

        .st-key-v660_tray
            .st-key-war_player_list
            [data-testid="stColumn"] {{
            min-height: 34px !important;
            height: 34px !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }}

        .st-key-v660_tray .player-name2 {{
            font-size: .70rem !important;
            line-height: 1.08 !important;
            font-weight: 780 !important;
            color: #F8FAFC !important;
            -webkit-text-fill-color: #F8FAFC !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }}

        .st-key-v660_tray .player-sub2 {{
            font-size: .50rem !important;
            line-height: 1.02 !important;
            margin-top: 2px !important;
            color: #91A2B9 !important;
            -webkit-text-fill-color: #91A2B9 !important;
        }}

        .st-key-v660_tray .stat2,
        .st-key-v660_tray .rank2 {{
            font-size: .57rem !important;
            line-height: 1 !important;
            color: #CFD8E6 !important;
            -webkit-text-fill-color: #CFD8E6 !important;
        }}

        .st-key-v660_tray .player-row-divider,
        .st-key-v660_tray .player-header-divider,
        .st-key-v660_tray hr {{
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            min-height: 0 !important;
            max-height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            border: 0 !important;
            background: transparent !important;
        }}

        /* Queue / roster tabs remain fixed; their content scrolls below. */
        .st-key-v63_utility_side
            [data-testid="stHorizontalBlock"]:first-of-type {{
            flex: 0 0 31px !important;
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
            border-radius: 6px !important;
            pointer-events: auto !important;
            z-index: 10040 !important;
        }}

        .st-key-v632_utility_content {{
            flex: 1 1 auto !important;
            min-height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
        }}

        .st-key-v632_utility_content
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
            pointer-events: auto !important;
        }}

        .st-key-v632_utility_content
            [data-testid="stVerticalBlockBorderWrapper"]
            > div,
        .st-key-v632_utility_content
            [data-testid="stVerticalBlock"] {{
            height: auto !important;
            max-height: none !important;
            min-height: max-content !important;
            overflow: visible !important;
        }}

        /* Ensure every obsolete drag/control implementation stays retired. */
        .st-key-v648_drag_handle,
        .st-key-v647_tray_controls,
        .st-key-v646_floating_tray_controls,
        .st-key-v63_sheet_handle,
        .st-key-v62_tray_controls {{
            display: none !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_tray_controls(level: int) -> None:
    """Render centered fixed-state tray controls without affecting layout."""
    with st.container(key="v720_tray_controls"):
        up_col, down_col = st.columns([1, 1], gap="small")

        with up_col:
            st.button(
                "▲",
                key="v720_tray_up",
                help="Expand player tray",
                disabled=level >= max(TRAY_LEVELS),
                on_click=change_tray_level,
                args=(1,),
                use_container_width=True,
            )

        with down_col:
            st.button(
                "▼",
                key="v720_tray_down",
                help="Compact player tray",
                disabled=level <= min(TRAY_LEVELS),
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
    utility_height: int,
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
            height=int(utility_height),
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
                    viewport_height=max(72, int(utility_height) - 4),
                )


def render_bottom_sheet(
    deps: BottomSheetDependencies,
    current_index: Optional[int],
    user_turn: bool,
) -> None:
    level = _current_level()
    settings = TRAY_LEVELS[level]
    _render_sheet_css(level)
    _render_tray_controls(level)

    with st.container(key="v660_tray"):
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
                int(settings["utility_height"]),
            )
