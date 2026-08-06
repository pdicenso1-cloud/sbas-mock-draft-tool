# FantasySync v6.3 — Phase 1 Component Refactor

## Completed

The Draft Room layout has been removed from the main `app.py` execution
branch and moved into:

```text
components/
├── __init__.py
└── draft_room.py
```

`app.py` now creates a `DraftRoomDependencies` object and calls:

```python
render_draft_room(...)
```

## Preserved

This phase intentionally does not rewrite the draft engine. The following
remain intact:

- hidden autorefresh component
- 180 ms CPU cadence
- CPU selection logic
- draft timer and Start/Pause controls
- draft-board HTML and colors
- current scrolling CSS and containers
- player queue behavior
- roster assignment
- keepers and traded picks
- Sleeper-style tray arrows and three tray levels
- Queue/Roster tabs
- all data files and deployment configuration

## Why this helps

Future layout work can now be made in `components/draft_room.py` without
editing the draft engine and unrelated pages inside `app.py`.

## GitHub update

Upload the complete extracted folder, not only `app.py`, because the app now
requires the new `components` directory:

```text
app.py
components/
    __init__.py
    draft_room.py
```
