"""Top navigation for the sidebar-free FantasySync shell."""
import json
from collections.abc import Callable
from typing import Any

import streamlit as st

PAGE_OPTIONS = [
    "Draft Room",
    "Rankings",
    "Recommendations",
    "Draft Grades",
    "Data Status",
    "League History",
    "Settings",
    "Keepers",
    "Trades",
    "League Setup",
]

PAGE_ROUTE_MAP = {
    "Draft Room": "Draft Room",
    "Rankings": "Rankings & ADP",
    "Recommendations": "Recommendations",
    # Preserve the existing routes while page implementations are modularized.
    "Draft Grades": "League History",
    "Data Status": "Available Players",
    "League History": "League History",
    "Settings": "Settings",
    # This tab's label used to say "Import / Export" while already routing
    # to "Keepers & Picks" - relabeled to match what it actually is/will be.
    "Keepers": "Keepers & Picks",
    "Trades": "Trades",
    # This tab's label used to say "Help & Docs" while already routing to
    # "League Setup" - relabeled to match what it actually is/will be.
    "League Setup": "League Setup",
}


def render_top_navigation(
    *,
    rebuild_draft: Callable[[], None],
    serializable_state: Callable[[], dict[str, Any]],
) -> str:
    """Render the global top navigation and return the legacy page route."""
    if "top_navigation" not in st.session_state:
        st.session_state.top_navigation = "Draft Room"

    with st.container(key="v670_top_nav"):
        nav_col, reset_col, download_col = st.columns(
            [8.9, 0.72, 0.92],
            gap="small",
        )

        with nav_col:
            selected_nav = st.radio(
                "FantasySync Navigation",
                PAGE_OPTIONS,
                key="top_navigation",
                horizontal=True,
                label_visibility="collapsed",
            )

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

    return PAGE_ROUTE_MAP[selected_nav]
