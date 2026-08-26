"""Shared draft board persistence via Supabase.

The draft board is one shared state across every visitor now, not private
per browser session - picks, keeper assignments, and trades should look the
same to everyone who opens the site, and survive a Streamlit Cloud reboot
or redeploy (which wipes anything kept only on local disk or in memory).

Only `picks` (draft results plus trade ownership changes - trades are just
a `current_owner` change on this same table) is shared this way. Team/
keeper *configuration* stays exactly as before, in data/teams.csv and
data/keepers.csv via GitHub - this module never touches those. Per-visitor
things also stay session-local and are never written here: which team a
given visitor is viewing the board as (`user_team`), their personal player
queue, and pick-clock timing - two people watching at once shouldn't fight
over whose queue or clock is "real."

Saves happen at natural checkpoints (a real pick made, a trade saved, the
draft reset, the draft finishing) rather than on every CPU-ticker frame.
Checkpointing every tick would mean every one of those (currently ~250-
400ms apart) waits on a network round trip to Supabase, which would slow
the ticker back down after the work that specifically sped it up. See the
call sites in fantasysync/draft_engine.py and fantasysync/runtime.py.

Needs two Streamlit secrets: SUPABASE_URL and SUPABASE_KEY (the project's
anon/public API key - safe here since it only ever runs server-side in this
app, never reaches a visitor's browser, unlike a typical client-side
Supabase setup). Both fetch and save silently no-op if those aren't
configured, or if a request fails for any reason - a persistence outage
should degrade to "this visitor's session just won't see saved history,"
same as before this module existed, never crash the app.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
import requests
import streamlit as st

REQUEST_TIMEOUT = 10
_TABLE = "draft_state"
_ROW_ID = 1

# Every column snake_order()/assign_keepers() (fantasysync/app_state.py)
# put on a real picks DataFrame. A loaded row missing any of these isn't
# usable - it would parse into a DataFrame "successfully" here but blow up
# much later, deep in unrelated code (current_open_index(), the board
# HTML), the first time something reaches for a column that isn't there -
# far from this function's own error handling, so failures like that are
# hard to trace back to a bad row in the database. Checked explicitly
# instead so a malformed row degrades exactly like "nothing saved yet."
_REQUIRED_PICKS_COLUMNS = {
    "overall", "round", "slot", "original_team_id",
    "original_owner", "current_owner", "keeper_player",
    "selected_player", "source",
}


def _config() -> Optional[tuple[str, str]]:
    try:
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "")
    except Exception:
        # No secrets.toml configured anywhere (local or Cloud).
        return None
    if not url or not key:
        return None
    return url.rstrip("/"), key


def load_shared_picks() -> Optional[pd.DataFrame]:
    """The league's current shared draft board, if persistence is
    configured and a saved board exists. None if unconfigured, nothing has
    ever been saved yet, or the request fails - callers should fall back
    to building a fresh board from data/teams.csv + data/keepers.csv."""
    config = _config()
    if config is None:
        return None
    url, key = config
    try:
        resp = requests.get(
            f"{url}/rest/v1/{_TABLE}",
            params={"id": f"eq.{_ROW_ID}", "select": "picks_json"},
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        rows = resp.json()
        if not rows or not rows[0].get("picks_json"):
            return None
        picks = pd.DataFrame(rows[0]["picks_json"])
        if not _REQUIRED_PICKS_COLUMNS.issubset(picks.columns):
            return None
        return picks
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return None


def save_shared_picks(picks: pd.DataFrame) -> None:
    """Checkpoint the shared draft board so every visitor (and a rebooted
    app) sees it. Call at natural pause points only - see module
    docstring - never inside the CPU ticker's own per-tick path."""
    config = _config()
    if config is None:
        return
    url, key = config
    try:
        requests.post(
            f"{url}/rest/v1/{_TABLE}",
            params={"on_conflict": "id"},
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates",
            },
            json={"id": _ROW_ID, "picks_json": picks.fillna("").to_dict(orient="records")},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        pass
