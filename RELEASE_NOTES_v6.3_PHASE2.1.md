# FantasySync v6.3 — Phase 2.1 Readability and Tray Controls

Built directly from Phase 2.

## Player-list readability

- Player names increased to a readable bottom-sheet-specific size.
- Team/position subtext, ranks, and statistics are also larger.
- Row height increased moderately to preserve readability.
- These rules are scoped to the bottom sheet and do not alter draft-board
  player cards.

## Tray controls

- Removed the centered `PLAYER TRAY` header.
- Moved the ▲ and ▼ buttons to the far-right edge.
- Controls now sit visually above the Queue / Roster utility panel.
- The full-width purple divider remains, preserving the Sleeper-style boundary.

## Preserved

- Fixed three-state bottom sheet
- Collapsed, Draft, and Expanded tray states
- Independent Round 1–16 board scrolling
- Hidden autorefresh mount
- 180 ms CPU cadence
- Queue and Roster tabs
- Draft logic, colors, keepers, trades, and roster assignment

## GitHub update

Upload the complete package, or replace:

```text
app.py
components/bottom_sheet.py
```
