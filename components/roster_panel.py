from __future__ import annotations

from html import escape
from typing import Any, Callable

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


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
                f'<span class="roster-player">{escape(player)}</span>'
                f'<span class="roster-pos">({escape(pos)})</span>'
            )
        else:
            content = '<span class="roster-empty">Empty</span>'

        rows.append(
            f"""
            <div class="roster-row">
                <span class="roster-slot slot-{group}">
                    {escape(slot)}
                </span>
                <span class="roster-content">{content}</span>
            </div>
            """
        )

    html = f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        * {{ box-sizing: border-box; }}
        html, body {{
          width: 100%; height: 100%; margin: 0; padding: 0;
          overflow: hidden; background: #101D2E; color: #F8FAFC;
          font-family: Inter, ui-sans-serif, system-ui, -apple-system,
            BlinkMacSystemFont, "Segoe UI", sans-serif;
        }}
        .roster-card {{
          width: 100%; height: {int(viewport_height)}px;
          display: flex; flex-direction: column; overflow: hidden;
        }}
        .roster-heading {{
          flex: 0 0 36px; display: flex; align-items: center;
          justify-content: space-between; padding: 2px 4px 7px;
          border-bottom: 1px solid rgba(148,163,184,.18);
        }}
        .roster-team {{
          overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
          font-size: 13px; font-weight: 850;
        }}
        .roster-count {{
          flex: 0 0 auto; margin-left: 8px; color: #B8C4D5;
          font-size: 10px; font-weight: 700;
        }}
        .roster-scroll {{
          flex: 1 1 auto; min-height: 0; overflow-y: auto;
          overflow-x: hidden; overscroll-behavior: contain;
          scrollbar-gutter: stable; scrollbar-width: thin;
          scrollbar-color: #60728F #101D2E; padding-right: 4px;
        }}
        .roster-scroll::-webkit-scrollbar {{ width: 7px; }}
        .roster-scroll::-webkit-scrollbar-track {{ background: #101D2E; }}
        .roster-scroll::-webkit-scrollbar-thumb {{
          background: #60728F; border-radius: 999px;
        }}
        .roster-row {{
          min-height: 32px; display: grid;
          grid-template-columns: 40px minmax(0,1fr);
          align-items: center; gap: 8px;
          border-bottom: 1px solid rgba(148,163,184,.13);
        }}
        .roster-slot {{
          width: 36px; height: 23px; display: inline-flex;
          align-items: center; justify-content: center; border-radius: 5px;
          color: #fff; font-size: 10px; font-weight: 850;
        }}
        .slot-QB {{ background:#7D55C7; }}
        .slot-RB {{ background:#47A368; }}
        .slot-WR {{ background:#3E7DE0; }}
        .slot-TE {{ background:#EA9848; }}
        .slot-BN {{ background:#69758A; }}
        .roster-content {{
          min-width: 0; display: flex; align-items: baseline;
          gap: 5px; overflow: hidden; white-space: nowrap;
        }}
        .roster-player {{
          min-width: 0; overflow: hidden; text-overflow: ellipsis;
          font-size: 12px; font-weight: 760;
        }}
        .roster-pos {{ flex: 0 0 auto; color:#9EABC0; font-size:9px; }}
        .roster-empty {{ color:#8E9BB0; font-size:11px; }}
      </style>
    </head>
    <body>
      <div class="roster-card">
        <div class="roster-heading">
          <span class="roster-team">{team}</span>
          <span class="roster-count">{filled} / 16 players</span>
        </div>
        <div class="roster-scroll">{''.join(rows)}</div>
      </div>
    </body>
    </html>
    """
    components.html(html, height=int(viewport_height), scrolling=False)
