# FantasySync v7.2.0 — Tray Arrow States

Tray-only release built from the working v7.1.2 base.

## Changed
- Removed manual drag resizing.
- Removed browser/localStorage tray height persistence.
- Added centered ▲ / ▼ controls at the tray's top edge.
- Added three deterministic tray states:
  - Compact: 146 px — tuned for about 5 board rows visible.
  - Draft: 236 px — balanced working state.
  - Expanded: 332 px — tuned for about 2.5 board rows visible.
- Player-list height and Queue/Roster content height change with tray state.
- Player list retains internal scrolling.
- Queue/Roster retain internal scrolling.

## Explicitly untouched
- Draft board Python
- Draft board styling
- Board R1-R16 scrolling behavior
- Draft header
- CPU/autorefresh logic
- Top folder navigation
- app.py

## GitHub
Replace only:
`components/bottom_sheet.py`
