# FantasySync v7.3.0 — Tray UX

Built from the working v7.2.1 tray and v7.1.2 runtime.

## Tray functionality
- Search and ALL / QB / RB / WR / TE are permanently visible while the tray is open.
- Removed the redundant PLAYERS / QUEUE / WATCHLIST toolbar labels from the player side.
- RK, PLAYER, POS, ADP, TIER, SCORE, PROJ, AVG, RUSH, REC, PASS, BYE and VAL are clickable sort controls.
- Click the active header again to toggle ascending / descending.
- Active sort displays ▲ or ▼.
- Sort state persists through Streamlit and CPU reruns.
- Player list now exposes up to 100 filtered players instead of only 60.
- Player list remains independently scrollable.

## Density
- Player rows reduced to ~31 px.
- Expanded 238 px list viewport targets 6–7 visible players.
- Draft and Expanded tray heights remain unchanged.
- Compact tray remains 58 px.

## Queue / Roster
- Queue and Roster selectors use the same matte file-folder style as the main top navigation.
- Queue and Roster selection remains session-state-backed through CPU reruns.
- Utility content keeps independent scrolling.

## Locked / unchanged
- app.py
- draft_board.py
- draft header
- draft room composition
- top navigation
- global folder-tab CSS
- board R1–R16 scrolling
- CPU/autorefresh implementation

## GitHub update
Replace:
- components/bottom_sheet.py
- fantasysync/runtime.py
