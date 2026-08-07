# FantasySync v6.5.1 — Tray Fill and Player Scroll

## Fixed

- Removed the empty bottom region beneath the player list.
- Removed the visual bottom bar/footer from the tray.
- Reduced the drag grip from 84×20 px to 62×14 px.
- Player list now grows with the live dragged tray height.
- The native player-list wrapper scrolls through all available players.
- More player rows appear as the tray is expanded.
- Player content is hidden only at the true compact minimum.
- Removed player row and header dividers that appeared as white lines through
  player names.
- Queue/Roster height grows with the same live tray height.

## Preserved

- Working drag behavior and persisted height
- Draft-board width, colors, and styling
- R1–R16 board scrolling
- Open/closed sidebar widths
- Queue and roster behavior
- Hidden autorefresh
- 180 ms CPU cadence
- Timer, keepers, trades, and draft logic

## GitHub update

Replace:

```text
app.py
components/bottom_sheet.py
```
