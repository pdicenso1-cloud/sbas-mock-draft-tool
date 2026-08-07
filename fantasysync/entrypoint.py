"""Stable FantasySync entrypoint.

app.py delegates here permanently. Startup errors are intentionally rendered
before global CSS so a broken module/data dependency cannot become a blank
Streamlit page.
"""
from __future__ import annotations

from importlib import import_module
import traceback

import streamlit as st


def run() -> None:
    try:
        # Importing runtime executes the Streamlit application once.
        import_module("fantasysync.runtime")
    except Exception as exc:
        # Do not inject application CSS here. Keep Streamlit's native error
        # surface visible so deployment failures are diagnosable.
        st.error("FantasySync could not finish starting.")
        st.write(f"**{type(exc).__name__}:** {exc}")
        with st.expander("Startup traceback", expanded=False):
            st.code(traceback.format_exc(), language="text")
        st.info(
            "Check that the full v7 package was uploaded, including the "
            "data/, fantasysync/, components/, and styles/ folders."
        )
