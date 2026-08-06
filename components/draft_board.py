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
                height: calc(100vh - 104px);
                min-height: 520px;
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
