# FantasySync v6.5.0 — Restore and Link Complete Player Tray

This build starts from v6.4.8, the last version where Players, Queue, and
Roster were still rendered.

## Structural fix

The tray now consists of two sibling fixed elements:

```text
v648_drag_handle
v650_tray_content
    ├── Available Players
    └── Queue / Roster
```

Both use the same `--fs-live-sheet-height` value.

- Dragging the grip changes the complete tray height.
- Players, Queue, and Roster remain immediately below the grip.
- No blank middle region is created.
- Content is kept in normal top-down flow.
- The broken absolute nested-content approach from v6.4.9 is removed.

## Preserved

- Draft-board colors, width, and card layout
- Sidebar-open and sidebar-closed widths
- R1–R16 scrolling
- Player filters
- Roster and Queue behavior
- Hidden autorefresh
- 180 ms CPU selections
- Timer, keepers, trades, and draft logic

## GitHub update

Replace:

```text
app.py
components/bottom_sheet.py
```
