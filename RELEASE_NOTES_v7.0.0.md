# FantasySync v7.0.0 — Modular Architecture

This is a structural release. The intended user experience is unchanged from v6.7.2.

## Major changes

- `app.py` is reduced from ~7,000 lines to a frozen 7-line entrypoint.
- The prior application code now runs from `fantasysync/runtime.py`.
- Global CSS is extracted from Python into `styles/legacy.css`.
- Top navigation is isolated in `fantasysync/navigation.py`.
- Paths and constants are isolated in `fantasysync/paths.py` and `fantasysync/config.py`.
- Existing Draft Room components remain independently editable under `components/`.

## Why this matters

Future tray, board, navigation, and CSS changes should no longer require replacing `app.py`. This reduces the chance that a CSS brace, JavaScript string, or UI adjustment prevents the entire application from starting.

## Compatibility

The legacy runtime was intentionally preserved rather than rewriting draft logic in the same release. Draft state, CPU behavior, board behavior, Queue/Roster logic, keepers, trades, and the v6.7.2 UI remain on the same implementation path.

## GitHub

For the v7 migration, upload the **entire package once** because new folders are required. After v7 is deployed, normal releases should replace only the specific module being changed.
