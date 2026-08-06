# FantasySync v6.4.4 — Collapsed Sidebar Full Width

## Updated

When the left sidebar is completely collapsed:

- The main Draft Room uses `calc(100vw - 32px)`.
- The app keeps only 16 px gutters on the left and right.
- Compact header, team headers, draft cells, and board scroll viewport expand
  together.
- Legacy centered/max-width board constraints are removed.
- The fixed bottom tray and arrow controls align to the same gutters.

The expanded-sidebar layout remains unchanged.

## Preserved

- Position-filter visibility fix
- R1–R16 board scrolling
- Roster component and Queue/Roster controls
- Three tray states
- Hidden autorefresh
- 180 ms CPU cadence
- Current draft logic, timer, colors, keepers, and trades

## GitHub update

Replace `app.py`, or upload the complete package.
