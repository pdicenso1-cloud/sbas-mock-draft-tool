# FantasySync v7 Architecture

`app.py` is now a frozen Streamlit entrypoint. Feature updates should not modify it.

## Ownership

| Area | File |
|---|---|
| Streamlit entrypoint | `app.py` |
| Runtime/session/draft compatibility layer | `fantasysync/runtime.py` |
| Top navigation | `fantasysync/navigation.py` |
| Stable constants | `fantasysync/config.py` |
| Project/data paths | `fantasysync/paths.py` |
| Global CSS | `styles/legacy.css` |
| CSS loader | `styles/loader.py` |
| Draft board viewport | `components/draft_board.py` |
| Draft-room composition | `components/draft_room.py` |
| Draft header | `components/draft_header.py` |
| Player tray / Queue / Roster | `components/bottom_sheet.py` |

## Update rule

Do not replace `app.py` for normal releases. Change only the owning module.

Examples:

- Board display change → `components/draft_board.py` or board renderer in `fantasysync/runtime.py`
- Tray change → `components/bottom_sheet.py`
- Top tabs → `fantasysync/navigation.py`
- Global color/spacing → `styles/legacy.css`
- Constants → `fantasysync/config.py`

## Compatibility runtime

The historical draft/session functions remain in `fantasysync/runtime.py` in v7.0.0 to minimize behavior risk. They can be migrated incrementally into dedicated `logic/` modules in later releases without ever touching `app.py`.
