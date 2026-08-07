"""CSS loading helpers.

Global styles live outside Python so CSS changes cannot break a Python f-string.
"""
from pathlib import Path
import streamlit as st


def inject_css(path: Path) -> None:
    css = path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
