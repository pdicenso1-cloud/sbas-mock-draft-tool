# FantasySync v7.0.1 — Startup Reliability Hotfix

## Root cause fixed

The v7.0.0 modular package did not contain the required `data/` directory,
while `fantasysync/runtime.py` still loads:

- `data/players.csv`
- `data/teams.csv`
- `data/keepers.csv`

A fresh deployment could therefore fail before the Draft Room rendered.

## Changes

- Restores all three CSVs inside `data/`.
- Includes `requirements.txt` in the package.
- Adds a startup preflight before global CSS is injected.
- Adds an entrypoint exception surface so future startup failures show a
  readable error and traceback instead of a blank/black application.
- Keeps `app.py` frozen and unchanged at 7 lines.

## GitHub

Upload the complete v7.0.1 package for this migration repair. Future normal
feature work should continue to avoid `app.py`.
