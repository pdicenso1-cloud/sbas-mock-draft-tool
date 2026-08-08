"""Stable FantasySync entrypoint.

Streamlit re-executes this file's `run()` on every rerun (widget interaction,
autorefresh tick, etc.), so calling `fantasysync.runtime.render_app()`
explicitly here draws the full interface every time. `fantasysync.runtime` is
imported once and cached like any normal module; only `render_app()` itself
needs to run on each rerun, so there is no need to force-reload the module.
"""
from __future__ import annotations

import importlib
from pathlib import Path
import sys
import traceback

import streamlit as st

from styles.loader import inject_css


RUNTIME_MODULE = "fantasysync.runtime"


def _render_runtime() -> None:
    """Execute the FantasySync runtime on every Streamlit script run."""
    module = sys.modules.get(RUNTIME_MODULE)
    if module is None:
        module = importlib.import_module(RUNTIME_MODULE)
    module.render_app()


def run() -> None:
    st.set_page_config(
        page_title="Susan Boyles Ass Sweat — Mock Draft Tool",
        page_icon="🏈",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    project_root = Path(__file__).resolve().parents[1]

    try:
        # Load design CSS before rendering so the page never flashes
        # Streamlit's unstyled default look on a rerun. If rendering throws,
        # the except block below forces its own visibility styles regardless
        # of what legacy.css did, so error visibility does not depend on this
        # ordering.
        inject_css(project_root / "styles" / "legacy.css")
        inject_css(project_root / "styles" / "safety.css")

        # Important: this MUST execute on every Streamlit rerun.
        _render_runtime()

    except Exception as exc:
        # Native visible failure surface; do not allow application CSS to hide it.
        st.markdown(
            """
            <style>
            html, body,
            [data-testid="stAppViewContainer"],
            [data-testid="stMain"],
            .main,
            .main .block-container {
                display: block !important;
                visibility: visible !important;
                opacity: 1 !important;
                background: #ffffff !important;
                color: #111827 !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.error("FantasySync could not finish starting.")
        st.write(f"**{type(exc).__name__}:** {exc}")
        with st.expander("Startup traceback", expanded=True):
            st.code(traceback.format_exc(), language="text")
