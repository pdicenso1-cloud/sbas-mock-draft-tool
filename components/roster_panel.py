from __future__ import annotations

from html import escape
from typing import Any, Callable

import pandas as pd
import streamlit as st


def _slot_group(slot: str) -> str:
    upper = slot.upper()
    if upper.startswith("RB"):
        return "RB"
    if upper.startswith("WR"):
        return "WR"
    if upper.startswith("QB"):
        return "QB"
    if upper.startswith("TE"):
        return "TE"
    return "BN"


def render_scrollable_roster(
    get_roster: Callable[[], pd.DataFrame],
    clean: Callable[[Any], str],
    viewport_height: int,
) -> None:
    """
    Render the complete roster in one HTML element with its own scrollbar.

    This avoids nested Streamlit bounded containers, which previously clipped
    the roster after roughly five visible rows.
    """
    roster = get_roster()
    filled = int((roster["Player"].astype(str) != "").sum())
    team = escape(clean(st.session_state.user_team))

    rows: list[str] = []
    for row in roster.itertuples():
        player = clean(row.Player)
        slot = clean(row.Slot)
        pos = clean(row.Pos)
        group = _slot_group(slot)

        if player:
            content = (
                f'<span class="v640-roster-player">{escape(player)}</span>'
                f'<span class="v640-roster-pos">({escape(pos)})</span>'
            )
        else:
            content = '<span class="v640-roster-empty">Empty</span>'

        rows.append(
            f"""
            <div class="v640-roster-row">
                <span class="v640-roster-slot v640-slot-{group}">
                    {escape(slot)}
                </span>
                <span class="v640-roster-content">{content}</span>
            </div>
            """
        )

    st.markdown(
        f"""
        <div class="v640-roster-card">
            <div class="v640-roster-heading">
                <span class="v640-roster-team">{team}</span>
                <span class="v640-roster-count">{filled} / 16 players</span>
            </div>
            <div
                class="v640-roster-scroll"
                style="height:{int(viewport_height)}px"
            >
                {''.join(rows)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
