# FantasySync v6.2.2 — Separated Player Tray

Visual-only patch based on v6.2.1.

## Changed

- Restored a clear border and solid background around the complete player tray.
- Added spacing between the draft board, tray controls, and player tray.
- Prevented player, queue, and roster content from overlapping the draft board.
- Kept Queue and Roster inside one clickable tabbed utility box.

## Preserved

- Hidden autorefresh component
- 180 ms CPU cadence
- Current board scrolling logic
- Full-width board
- Sleeper-style tray arrows
- Queue/Roster tabs
- Draft colors, picks, timer, and selection behavior

## GitHub update

Replace only the root-level `app.py`, commit it, wait for Streamlit to
redeploy, then hard-refresh the browser.
