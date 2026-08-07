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

    st.markdown(
        f"""
        <style>
        :root {{
            --fs-sidebar-width: 13.7rem;
            --fs-live-sheet-height: {sheet_height}px;
        }}

        /* The board remains completely independent from this refactor. */
        .st-key-v63_board_region {{
            position: relative !important;
            z-index: 1 !important;
            width: 100% !important;
            margin: 0 !important;
            padding: 0 0 20px !important;
        }}

        /* Fixed grip, driven by the same height as the tray. */
        .st-key-v648_drag_handle {{
            position: fixed !important;
            bottom: calc(var(--fs-live-sheet-height) - 9px) !important;
            left: 55% !important;
            transform: translateX(-50%) !important;
            z-index: 10100 !important;
            width: 76px !important;
            height: 22px !important;
            min-height: 22px !important;
            max-height: 22px !important;
            margin: 0 !important;
            padding: 0 !important;
            border: 0 !important;
            background: transparent !important;
            overflow: visible !important;
            pointer-events: auto !important;
        }}

        .st-key-v648_drag_handle iframe {{
            width: 76px !important;
            height: 22px !important;
            border: 0 !important;
            background: transparent !important;
            overflow: visible !important;
            pointer-events: auto !important;
        }}

        /*
         * v6.6 tray shell:
         * one fixed container, one content row, and two independently
         * scrollable panels. No absolute-positioned tray body.
         */
        .st-key-v660_tray {{
            display: block !important;
            position: fixed !important;
            left: var(--fs-sidebar-width) !important;
            right: 0 !important;
            bottom: 0 !important;
            z-index: 10010 !important;
            height: var(--fs-live-sheet-height) !important;
            min-height: 52px !important;
            max-height: min(560px, calc(100vh - 150px)) !important;
            margin: 0 !important;
            padding: 8px 12px 6px !important;
            box-sizing: border-box !important;
            overflow: hidden !important;
            background: #0B1625 !important;
            border-top: 1px solid rgba(124,92,224,.72) !important;
            border-bottom: 0 !important;
            box-shadow: 0 -5px 16px rgba(0,0,0,.22) !important;
            pointer-events: auto !important;
            isolation: isolate !important;
        }}

        body:has(
            section[data-testid="stSidebar"][aria-expanded="false"]
        ) .st-key-v660_tray {{
            left: 0 !important;
        }}

        /* Only the tray's root wrappers receive full height. */
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

        /* Left and right panels fill their column. */
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

        /* Toolbar and table header remain fixed at the top. */
        .st-key-v61_player_toolbar {{
            flex: 0 0 auto !important;
            min-height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: visible !important;
            pointer-events: auto !important;
        }}

        .st-key-v61_player_toolbar button,
        .st-key-v61_player_toolbar input {{
            pointer-events: auto !important;
        }}

        /*
         * The player-list shell is measured precisely by the drag component.
         * CSS provides safe fallback behavior before JavaScript attaches.
         */
        .st-key-v660_tray .st-key-war_player_list {{
            flex: 1 1 auto !important;
            height: auto !important;
            max-height: none !important;
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
            [data-testid="stVerticalBlockBorderWrapper"]
            ::-webkit-scrollbar {{
            width: 7px !important;
        }}

        .st-key-v660_tray
            .st-key-war_player_list
            [data-testid="stVerticalBlockBorderWrapper"]
            ::-webkit-scrollbar-track {{
            background: #0B1625 !important;
        }}

        .st-key-v660_tray
            .st-key-war_player_list
            [data-testid="stVerticalBlockBorderWrapper"]
            ::-webkit-scrollbar-thumb {{
            background: #53647F !important;
            border-radius: 999px !important;
        }}

        /* Compact, readable rows. */
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

        .st-key-v660_tray
            .st-key-war_player_list button {{
            width: 24px !important;
            min-width: 24px !important;
            height: 24px !important;
            min-height: 24px !important;
            padding: 0 !important;
            font-size: .69rem !important;
        }}

        .st-key-v660_tray .value-badge {{
            height: 20px !important;
            min-width: 26px !important;
            font-size: .49rem !important;
        }}

        .st-key-v660_tray .player-table-header2 {{
            min-height: 23px !important;
            height: 23px !important;
            font-size: .49rem !important;
            line-height: 1 !important;
        }}

        /* Remove all divider artifacts crossing player names. */
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

        /* Utility tabs remain fixed; content gets the remaining height. */
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
            height: auto !important;
            max-height: none !important;
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

        /* True compact state only. */
        .st-key-v660_tray.fs-tray-compact
            > div
            > div
            > [data-testid="stVerticalBlock"]
            > [data-testid="stHorizontalBlock"] {{
            opacity: 0 !important;
            visibility: hidden !important;
            pointer-events: none !important;
        }}

        /* Retire all previous tray implementations. */
        .st-key-v650_tray_content,
        .st-key-v649_tray_content,
        .st-key-v63_bottom_sheet,
        .st-key-v53_bottom_workspace,
        .st-key-v62_tray_controls {{
            display: none !important;
        }}

        /* Hidden CPU refresh remains unchanged. */
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

def _render_drag_handle(initial_height: int) -> None:
    """
    Resize the tray and then measure the actual remaining space for each inner
    scroll viewport. This avoids hard-coded toolbar offsets and remains stable
    when the sidebar opens or closes.
    """
    drag_html = f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        * {{ box-sizing: border-box; }}
        html, body {{
          width: 100%; height: 100%; margin: 0; padding: 0;
          overflow: visible; background: transparent;
          user-select: none; -webkit-user-select: none;
        }}
        #grip {{
          width: 66px; height: 14px; margin: 3px auto 0;
          display: flex; align-items: center; justify-content: center;
          cursor: ns-resize;
          border: 1px solid rgba(143,158,184,.48);
          border-radius: 999px;
          background: rgba(39,52,73,.90);
          box-shadow: 0 3px 12px rgba(0,0,0,.30),
                      inset 0 1px 0 rgba(255,255,255,.08);
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
          touch-action: none;
        }}
        #grip::before {{
          content: '';
          width: 26px; height: 3px;
          border-radius: 999px;
          background: rgba(204,215,232,.78);
          box-shadow: 0 -4px 0 rgba(204,215,232,.24),
                      0 4px 0 rgba(204,215,232,.24);
        }}
        #grip:hover, #grip.dragging {{
          background: rgba(67,86,116,.98);
          border-color: rgba(205,216,235,.82);
        }}
      </style>
    </head>
    <body>
      <div id="grip" title="Drag up or down to resize player tray"></div>
      <script>
      (() => {{
        const grip = document.getElementById('grip');
        const STORAGE_KEY = 'fantasysync_tray_height_v660';
        let parentDoc;
        let parentWin;

        try {{
          parentDoc = window.parent.document;
          parentWin = window.parent;
        }} catch (err) {{
          return;
        }}

        const q = (selector) => parentDoc.querySelector(selector);
        const getTray = () => q('.st-key-v660_tray');

        const clamp = (value) => {{
          const maxHeight = Math.min(560, parentWin.innerHeight - 150);
          return Math.max(52, Math.min(maxHeight, value));
        }};

        const setImportant = (node, property, value) => {{
          if (node) node.style.setProperty(property, value, 'important');
        }};

        const bindScrollIsolation = (node) => {{
          if (!node || node.dataset.fsScrollBound === '1') return;
          node.dataset.fsScrollBound = '1';

          node.addEventListener(
            'wheel',
            (event) => {{
              event.stopPropagation();
            }},
            {{ passive: true }}
          );

          node.addEventListener(
            'touchmove',
            (event) => {{
              event.stopPropagation();
            }},
            {{ passive: true }}
          );
        }};

        const syncInnerLayout = () => {{
          const tray = getTray();
          if (!tray) return;

          const safeHeight = tray.getBoundingClientRect().height;
          const compact = safeHeight <= 64;
          tray.classList.toggle('fs-tray-compact', compact);

          const playerSide = q(
            '.st-key-v660_tray .st-key-v63_player_side'
          );
          const playerList = q(
            '.st-key-v660_tray .st-key-war_player_list'
          );
          const playerScroll = playerList?.querySelector(
            '[data-testid="stVerticalBlockBorderWrapper"]'
          );

          if (playerSide && playerList) {{
            const sideRect = playerSide.getBoundingClientRect();
            const listRect = playerList.getBoundingClientRect();
            const available = Math.max(
              compact ? 0 : 72,
              Math.floor(sideRect.bottom - listRect.top)
            );

            setImportant(playerList, 'height', `${{available}}px`);
            setImportant(playerList, 'max-height', `${{available}}px`);
            setImportant(playerList, 'min-height', compact ? '0px' : '72px');
            setImportant(playerList, 'display', compact ? 'none' : 'block');
            setImportant(playerList, 'visibility', compact ? 'hidden' : 'visible');
            setImportant(playerList, 'opacity', compact ? '0' : '1');

            setImportant(playerScroll, 'height', '100%');
            setImportant(playerScroll, 'max-height', '100%');
            setImportant(playerScroll, 'min-height', '0px');
            setImportant(playerScroll, 'overflow-y', 'auto');
            setImportant(playerScroll, 'overflow-x', 'hidden');
            setImportant(playerScroll, 'pointer-events', 'auto');
            bindScrollIsolation(playerScroll);
          }}

          const utilitySide = q(
            '.st-key-v660_tray .st-key-v63_utility_side'
          );
          const utilityContent = q(
            '.st-key-v660_tray .st-key-v632_utility_content'
          );
          const utilityScroll = utilityContent?.querySelector(
            '[data-testid="stVerticalBlockBorderWrapper"]'
          );

          if (utilitySide && utilityContent) {{
            const sideRect = utilitySide.getBoundingClientRect();
            const contentRect = utilityContent.getBoundingClientRect();
            const available = Math.max(
              compact ? 0 : 72,
              Math.floor(sideRect.bottom - contentRect.top)
            );

            setImportant(utilityContent, 'height', `${{available}}px`);
            setImportant(utilityContent, 'max-height', `${{available}}px`);
            setImportant(utilityContent, 'min-height', compact ? '0px' : '72px');
            setImportant(utilityContent, 'display', compact ? 'none' : 'block');
            setImportant(utilityContent, 'visibility', compact ? 'hidden' : 'visible');
            setImportant(utilityContent, 'opacity', compact ? '0' : '1');

            setImportant(utilityScroll, 'height', '100%');
            setImportant(utilityScroll, 'max-height', '100%');
            setImportant(utilityScroll, 'min-height', '0px');
            setImportant(utilityScroll, 'overflow-y', 'auto');
            setImportant(utilityScroll, 'overflow-x', 'hidden');
            setImportant(utilityScroll, 'pointer-events', 'auto');
            bindScrollIsolation(utilityScroll);

            const iframe = utilityContent.querySelector('iframe');
            if (iframe) {{
              setImportant(iframe, 'height', `${{available}}px`);
              setImportant(iframe, 'max-height', `${{available}}px`);
              setImportant(iframe, 'min-height', '0px');
            }}
          }}
        }};

        const scheduleSync = () => {{
          parentWin.requestAnimationFrame(() => {{
            parentWin.requestAnimationFrame(syncInnerLayout);
          }});
        }};

        const applyHeight = (height, persist = true) => {{
          const safe = clamp(Math.round(height));
          parentDoc.documentElement.style.setProperty(
            '--fs-live-sheet-height',
            `${{safe}}px`
          );

          const tray = getTray();
          if (tray) {{
            setImportant(tray, 'height', `${{safe}}px`);
            setImportant(tray, 'min-height', '52px');
            setImportant(
              tray,
              'max-height',
              `${{Math.min(560, parentWin.innerHeight - 150)}}px`
            );
          }}

          const handle = q('.st-key-v648_drag_handle');
          if (handle) {{
            setImportant(
              handle,
              'bottom',
              `${{Math.max(43, safe - 9)}}px`
            );
          }}

          scheduleSync();

          if (persist) {{
            try {{
              parentWin.localStorage.setItem(STORAGE_KEY, String(safe));
            }} catch (err) {{}}
          }}
        }};

        let saved = null;
        try {{
          saved = Number(parentWin.localStorage.getItem(STORAGE_KEY));
        }} catch (err) {{}}

        applyHeight(
          Number.isFinite(saved) && saved > 0
            ? saved
            : {int(initial_height)},
          false
        );

        let dragging = false;
        let startY = 0;
        let startHeight = 0;

        const move = (event) => {{
          if (!dragging) return;
          event.preventDefault();
          applyHeight(startHeight + (startY - event.clientY), false);
        }};

        const stop = () => {{
          if (!dragging) return;
          dragging = false;
          grip.classList.remove('dragging');

          const tray = getTray();
          if (tray) {{
            applyHeight(
              Math.round(tray.getBoundingClientRect().height),
              true
            );
          }}

          parentWin.removeEventListener('pointermove', move, true);
          parentWin.removeEventListener('pointerup', stop, true);
          parentWin.removeEventListener('pointercancel', stop, true);
        }};

        grip.addEventListener('pointerdown', (event) => {{
          event.preventDefault();
          const tray = getTray();
          if (!tray) return;

          dragging = true;
          grip.classList.add('dragging');
          startY =
            event.clientY +
            window.frameElement.getBoundingClientRect().top;
          startHeight = tray.getBoundingClientRect().height;

          parentWin.addEventListener('pointermove', move, true);
          parentWin.addEventListener('pointerup', stop, true);
          parentWin.addEventListener('pointercancel', stop, true);
        }});

        parentWin.addEventListener('resize', () => {{
          const tray = getTray();
          if (tray) {{
            applyHeight(tray.getBoundingClientRect().height, false);
          }}
        }});

        /*
         * Sidebar collapse/expand and Streamlit CPU reruns replace DOM nodes.
         * Re-measure after each mutation without changing the saved height.
         */
        let mutationTimer = null;
        const observer = new MutationObserver(() => {{
          parentWin.clearTimeout(mutationTimer);
          mutationTimer = parentWin.setTimeout(() => {{
            const tray = getTray();
            if (!tray) return;

            let current = null;
            try {{
              current = Number(
                parentWin.localStorage.getItem(STORAGE_KEY)
              );
            }} catch (err) {{}}

            applyHeight(
              Number.isFinite(current) && current > 0
                ? current
                : tray.getBoundingClientRect().height,
              false
            );
          }}, 40);
        }});

        observer.observe(parentDoc.body, {{
          childList: true,
          subtree: true,
          attributes: true,
          attributeFilter: ['aria-expanded', 'data-state', 'class']
        }});

        parentWin.setTimeout(scheduleSync, 100);
        parentWin.setTimeout(scheduleSync, 350);
      }})();
      </script>
    </body>
    </html>
    """

    with st.container(key="v648_drag_handle"):
        components.html(
            drag_html,
            height=22,
            scrolling=False,
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
            height=120,
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
                    viewport_height=420,
                )


def render_bottom_sheet(
    deps: BottomSheetDependencies,
    current_index: Optional[int],
    user_turn: bool,
) -> None:
    level = _current_level()
    effective_level = 1 if level == 0 else level
    settings = TRAY_LEVELS[effective_level]
    _render_sheet_css(effective_level)

    # The grip and content are sibling fixed elements driven by the same
    # --fs-live-sheet-height value. Nothing can separate them vertically.
    _render_drag_handle(int(settings["height"]))

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
            )
