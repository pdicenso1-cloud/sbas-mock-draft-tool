# FantasySync v7.0.3 — Safe Startup Render

## Purpose
Fix the persistent black-screen startup problem without changing frozen app.py.

## Boot-order changes
- `st.set_page_config()` moved to `fantasysync/entrypoint.py`.
- Runtime renders before `styles/legacy.css` is injected.
- Legacy CSS is loaded only after successful runtime completion.
- `styles/safety.css` is injected last and only guarantees shell visibility.
- Startup exceptions now render with native Streamlit styling and an expanded traceback.

## Unchanged
- `app.py` is byte-for-byte unchanged.
- Draft board logic and styling are unchanged.
- Player tray logic is unchanged.
- CPU behavior is unchanged.
- Navigation behavior is unchanged.

## GitHub update
Replace:
- `fantasysync/entrypoint.py`
- `fantasysync/runtime.py`
- add `styles/safety.css`

You may upload the whole package for simplicity.
