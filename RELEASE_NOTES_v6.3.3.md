# FantasySync v6.3.3 — Compact Header and Roster Scroll

## Compact header
- Reduced top padding and header height.
- Smaller title, metadata chips, CPU status, clock, and Start/Pause button.
- Draft-status text sits closer to the board.
- Team headers begin higher on the screen.

## Roster scrolling
- Roster now uses its own bounded internal viewport.
- Draft state: 188 px.
- Expanded state: 318 px.
- Mouse wheel, trackpad, and subtle scrollbar reach all roster and bench slots.

## Preserved
- Three tray states
- R1–R16 board scrolling
- Persistent Queue/Roster buttons
- Hidden autorefresh
- 180 ms CPU cadence
- Existing draft, queue, roster, keeper, trade, and timer logic

## GitHub update
Replace:
- `app.py`
- `components/bottom_sheet.py`
