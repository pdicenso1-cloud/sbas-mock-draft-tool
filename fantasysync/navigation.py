"""Top navigation for the sidebar-free FantasySync shell."""
import json
from collections.abc import Callable
from typing import Any

import streamlit as st

PAGE_OPTIONS = [
    "Home",
    "Draft Room",
    "Rankings",
]

PAGE_ROUTE_MAP = {
    "Home": "Home",
    "Draft Room": "Draft Room",
    "Rankings": "Rankings & ADP",
}


def go_to_page(page: str) -> None:
    """Programmatically switch the active tab from anywhere else on the
    page (e.g. a "Home" quick-link button), then call st.rerun().

    Can't just assign st.session_state.top_navigation directly for this -
    that key already belongs to the st.radio widget below, and Streamlit
    raises StreamlitAPIException the moment you write to a widget's own key
    after that widget has been instantiated in the current script run
    (confirmed live: this app's page-render order puts the nav radio
    before every page's own content, so by the time a page's button click
    runs, the radio already claimed the key for this run). Queuing the
    request here instead and applying it at the top of this function - the
    first thing that happens, on the next run, before the radio widget
    exists yet - sidesteps that restriction entirely.
    """
    st.session_state["_pending_nav"] = page
    st.rerun()


def render_top_navigation() -> str:
    """Render the global top navigation and return the legacy page route.

    Reset/download-state used to live here too, on every page - they now
    render only on the Draft Room itself (see render_draft_room_actions),
    the only page they're actually relevant to.
    """
    if "top_navigation" not in st.session_state:
        st.session_state.top_navigation = "Home"

    pending = st.session_state.pop("_pending_nav", None)
    if pending is not None:
        st.session_state.top_navigation = pending

    with st.container(key="v670_top_nav"):
        selected_nav = st.radio(
            "FantasySync Navigation",
            PAGE_OPTIONS,
            key="top_navigation",
            horizontal=True,
            label_visibility="collapsed",
        )

    return PAGE_ROUTE_MAP[selected_nav]


def render_draft_room_actions(
    *,
    rebuild_draft: Callable[[], None],
    serializable_state: Callable[[], dict[str, Any]],
) -> None:
    """Reset + download-state buttons, Draft Room only (see render_top_navigation).
    Wrapped in its own keyed container so hub_theme.css can size these two
    down to match the small round/format pill chips next to them - they
    lost their old compact sizing (previously scoped to .st-key-v670_top_nav
    button) when they moved out of that container onto this page."""
    with st.container(key="draft_room_actions"):
        reset_col, download_col = st.columns([1, 1], gap="small")

        with reset_col:
            if st.button(
                "↺ Reset",
                use_container_width=True,
                key="top_reset_draft",
                help="Reset the current mock draft",
            ):
                rebuild_draft()
                st.session_state.draft_active = False
                st.session_state.clock_running = False
                st.session_state.draft_message = (
                    "Draft reset. Select a team and press Start Draft."
                )
                st.rerun()

        with download_col:
            state_json = json.dumps(serializable_state(), indent=2)
            st.download_button(
                "⇩ State",
                data=state_json,
                file_name="sbas_mock_draft_state.json",
                mime="application/json",
                use_container_width=True,
                key="top_download_draft_state",
                help="Download the current draft state",
            )
