from __future__ import annotations

from html import escape
from typing import Callable

import streamlit as st


def render_draft_board(
    board_html: Callable[[], str],
) -> None:
    """
    Render all 16 rounds inside a board-owned scroll viewport.

    The scroll container is part of the generated HTML rather than a nested
    Streamlit bounded container, preventing Streamlit wrapper heights from
    clipping the final rounds.
    """
    html = board_html()

    with st.container(key="v63_board_region"):
        st.markdown(
            f"""
            <style>
            .v643-board-scroll {{
                width: 100%;
                /* This 238px is everything rendered above the board (top
                   nav, "Mock Draft" header, team selector) - measured
                   directly rather than the stale 104px this used to be,
                   which was already short of the real offset even before
                   accounting for the tray below.
                   --fs-live-sheet-height (set in components/bottom_sheet.py
                   alongside the tray's own height) is subtracted too, so
                   the board's scrollable area actually ends where the
                   fixed-position tray begins instead of continuing
                   underneath it. Without this, the board's own coordinate
                   system had "room" for all 16 rounds, but the tray - a
                   separate, later-painted, opaque, fixed-position element -
                   physically covered the last several rounds regardless of
                   how far you scrolled, since scrolling only moves content
                   within the board's box, it can't move content out from
                   behind something outside that box. */
                height: calc(100vh - 238px - var(--fs-live-sheet-height, 0px));
                min-height: 200px;
                overflow-y: auto;
                overflow-x: hidden;
                overscroll-behavior: contain;
                scrollbar-gutter: stable;
                -webkit-overflow-scrolling: touch;
                scrollbar-width: thin;
                scrollbar-color: #465671 #091321;
                padding: 0 3px 58px 0;
                box-sizing: border-box;
            }}

            .v643-board-scroll::-webkit-scrollbar {{
                width: 7px;
            }}

            .v643-board-scroll::-webkit-scrollbar-track {{
                background: #091321;
            }}

            .v643-board-scroll::-webkit-scrollbar-thumb {{
                background: #465671;
                border-radius: 999px;
            }}

            .v643-board-scroll::-webkit-scrollbar-thumb:hover {{
                background: #657995;
            }}

            .v643-board-content {{
                width: 100%;
                height: auto;
                min-height: max-content;
                overflow: visible;
            }}

            .v643-board-end {{
                width: 100%;
                height: 48px;
                flex: 0 0 48px;
            }}
            </style>

            <div
                class="v643-board-scroll"
                role="region"
                aria-label="Scrollable draft board, rounds 1 through 16"
            >
                <div class="v643-board-content">
                    {html}
                </div>
                <div class="v643-board-end" aria-hidden="true"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
