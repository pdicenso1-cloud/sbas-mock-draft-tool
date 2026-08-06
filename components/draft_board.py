from __future__ import annotations

from typing import Callable

import streamlit as st


def render_draft_board(
    board_html: Callable[[], str],
) -> None:
    """
    Render the board as an independent R1-R16 scroll viewport.

    The fixed bottom sheet overlays this viewport and never changes its height.
    """
    with st.container(key="v63_board_region"):
        with st.container(
            height=760,
            border=False,
            key="v63_board_scroll",
        ):
            st.markdown(
                board_html(),
                unsafe_allow_html=True,
            )
