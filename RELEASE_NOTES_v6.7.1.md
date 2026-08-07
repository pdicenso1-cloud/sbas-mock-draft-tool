# FantasySync v6.7.1 — Full-Width Snake Picks

Built directly from v6.7.0.

## Draft board changes

- Removed the R1/R2/R3 side-label column.
- Team headers remain fixed in draft-slot order.
- Pick labels now use Sleeper-style round.pick notation:
  - Round 1: 1.1 → 1.10
  - Round 2: 2.10 → 2.1 across the fixed team columns
  - Round 3: 3.1 → 3.10
  - alternating through the full draft.
- Draft board now uses nearly the complete browser width (8 px outer board gutters).
- Top navigation and compact draft controls remain slightly inset for readability.

## Preserved

- v6.7 top navigation shell
- player tray implementation and drag behavior
- CPU cadence/autorefresh
- draft colors and position colors
- team selection
- keepers/trades/queue/roster logic
- R1–R16 internal board scrolling

## GitHub update

Replace `app.py`, or upload the complete package.
