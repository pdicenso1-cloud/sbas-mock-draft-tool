# FantasySync v7.1.2 — Streamlit Rerun Fix

## Fixed
The modular v7 entrypoint used `import_module("fantasysync.runtime")`.

Python caches imported modules. Streamlit reruns `app.py` after widget changes,
but the cached runtime module did not execute again. The result was an empty /
black page after a rerun.

v7.1.2 now:
- imports the runtime on the first script run
- uses `importlib.reload()` on every subsequent Streamlit rerun
- renders the full FantasySync UI every time

## Preserved
- frozen 7-line `app.py`
- v7.1.1 folder-tab design
- draft board
- player tray
- Queue / Roster
- CPU/autorefresh behavior
- all draft logic

## GitHub update
Replace only:

`fantasysync/entrypoint.py`
