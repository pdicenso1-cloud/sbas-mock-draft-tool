"""Stable FantasySync entrypoint.

v7.0.3 boot order:
1. Configure Streamlit before any other UI command.
2. Import/render the runtime without global application CSS.
3. Inject legacy CSS only after a successful render.
4. Apply a tiny visibility safeguard last.
5. If startup fails, show the native Streamlit error surface.
"""
from __future__ import annotations

from importlib import import_module
import traceback
from pathlib import Path

import streamlit as st

from styles.loader import inject_css


def run() -> None:
    st.set_page_config(
        page_title="Susan Boyles Ass Sweat — Mock Draft Tool",
        page_icon="🏈",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    project_root = Path(__file__).resolve().parents[1]

    try:
        # Runtime renders the entire application. CSS is intentionally delayed
        # until this import has completed successfully.
        import_module("fantasysync.runtime")

        inject_css(project_root / "styles" / "legacy.css")
        inject_css(project_root / "styles" / "safety.css")

    except Exception as exc:
        # Ensure no application CSS can hide the failure surface.
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
        st.info(
            "The app.py entrypoint is still frozen. This error is coming from "
            "a modular runtime/component and can now be diagnosed directly."
        )
