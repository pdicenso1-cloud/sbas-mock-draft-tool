# FantasySync v6.4.9 — Linked Draggable Tray

## Fixed

The v6.4.8 grip resized the outer sheet, but Streamlit's inner player and
utility content remained anchored independently near the bottom of the page.

v6.4.9 adds one linked workspace:

```text
Bottom Sheet
├── Drag Grip
└── v649_tray_content
    ├── Available Players
    └── Queue / Roster
```

`v649_tray_content` is absolutely pinned directly beneath the grip and fills
the remainder of the live sheet height. Players, Queue, and Roster therefore
move up and down with the grip as one unit.

## Dynamic resizing

- Player-list height recalculates from the dragged tray height.
- Queue/Roster content height recalculates from the same live height.
- No blank expanding region remains between the grip and tray content.
- Saved tray height continues to persist through CPU reruns.

## Preserved

- Draft-board width, colors, and styling
- R1–R16 board scrolling
- Sidebar-open and sidebar-closed widths
- Player filters
- Roster and Queue behavior
- Hidden autorefresh
- 180 ms CPU cadence
- Timer, keepers, trades, and draft logic

## GitHub update

Replace:

```text
app.py
components/bottom_sheet.py
```
