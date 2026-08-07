"""CSS loading helpers.

Global styles live outside Python so CSS changes cannot break a Python
f-string. Missing styles raise a clear startup error.
"""
from pathlib import Path
import streamlit as st


def inject_css(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"FantasySync stylesheet not found: {path}")
    css = path.read_text(encoding="utf-8")
    st.markdown("<style>" + css + "</style>", unsafe_allow_html=True)
