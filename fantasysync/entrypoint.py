"""Stable FantasySync entrypoint.

The Streamlit root app delegates here so app.py never needs feature edits.
"""
from importlib import import_module


def run() -> None:
    # Importing runtime executes the existing Streamlit application once.
    import_module("fantasysync.runtime")
