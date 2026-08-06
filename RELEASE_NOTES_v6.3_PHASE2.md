# FantasySync v6.3 — Phase 2 Sleeper Bottom Sheet

## New components

```text
components/
├── __init__.py
├── draft_board.py
├── bottom_sheet.py
└── draft_room.py
```

## Draft board

- Independent fixed-height viewport
- Internal scrolling from Round 1 through Round 16
- Mouse wheel, trackpad, and subtle scrollbar support
- Board height never changes when the tray opens or closes

## Sleeper-style bottom sheet

Three arrow-controlled snap states:

1. **Collapsed**
   - Only the PLAYER TRAY handle is visible
   - Nearly the entire screen is available for the board

2. **Draft**
   - Search, position filters, player list
   - Queue and Roster tabs
   - Several selectable players visible

3. **Expanded**
   - Large player browser
   - Queue and Roster remain available
   - More player rows visible

The sheet is `position: fixed` and overlays the board. It does not push,
resize, or reflow the board.

## Preserved

- Hidden `streamlit-autorefresh` mount
- 180 ms CPU cadence
- Existing pick colors and draft-card styling
- CPU draft logic and timer
- Queue logic
- Roster assignment
- Keepers and traded picks
- Sidebar behavior

## GitHub update

Upload the complete package because Phase 2 adds:

```text
components/draft_board.py
components/bottom_sheet.py
```
