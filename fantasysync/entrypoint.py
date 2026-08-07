"""Stable FantasySync entrypoint.

v7.1.2 fixes Streamlit reruns while keeping app.py frozen.

Why this is required:
Streamlit reruns app.py after widget interaction and state changes. A normal
Python import executes fantasysync.runtime only once per process because Python
caches imported modules. On later Streamlit reruns, import_module() returned the
cached runtime without executing its UI code again, leaving the page empty.

This entrypoint explicitly reloads the runtime on every subsequent Streamlit
rerun so the full interface renders every time.
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
    if RUNTIME_MODULE in sys.modules:
        importlib.reload(sys.modules[RUNTIME_MODULE])
    else:
        importlib.import_module(RUNTIME_MODULE)


def run() -> None:
    st.set_page_config(
        page_title="Susan Boyles Ass Sweat — Mock Draft Tool",
        page_icon="🏈",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    project_root = Path(__file__).resolve().parents[1]

    try:
        # Important: this MUST execute on every Streamlit rerun.
        _render_runtime()

        # Load design CSS only after the application UI has rendered.
        inject_css(project_root / "styles" / "legacy.css")
        inject_css(project_root / "styles" / "safety.css")

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
