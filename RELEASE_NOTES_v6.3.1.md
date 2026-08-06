# FantasySync v6.3.1 — Tray Snap Polish

Built from v6.3 Phase 2.1.

## Three tray states

### Collapsed

- Player widgets and Queue/Roster are hidden.
- Only the right-aligned ▲ / ▼ controls remain.
- The board viewport uses nearly the full browser height.
- Target: approximately 8–10 draft rows visible, depending on screen size.

### Draft

- Sheet height: 258 px.
- Search, position filters, selectable players, Queue and Roster are visible.
- Target: approximately seven draft rows remain visible.

### Expanded

- Sheet height: 392 px.
- Larger player-browser workspace with Queue and Roster available.
- Target: approximately five draft rows remain visible.

## Player list

- Rows reduced from 38 px to 34 px.
- Player names remain readable at 0.70 rem.
- Controls, stats, and badges are slightly tighter.
- More players fit in both Draft and Expanded states.

## Interaction

- 180 ms snap transition between tray heights.
- Board remains independently scrollable from R1 through R16.
- Tray overlays the board and never pushes it through document flow.

## Preserved

- Hidden autorefresh component
- 180 ms CPU cadence
- Draft colors and card styling
- CPU logic and clock
- Queue and roster logic
- Keepers, traded picks, and roster assignment
- Right-aligned tray arrows

## GitHub update

Upload the complete package, or replace:

```text
app.py
components/bottom_sheet.py
```
