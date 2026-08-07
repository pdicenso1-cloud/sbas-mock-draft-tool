FantasySync v7.3.3 — Restore Styled UI

Replace only:
components/bottom_sheet.py

This hotfix is rebuilt directly from the last known-good v7.3.0 tray file.
It does NOT use the broken v7.3.1/v7.3.2 CSS override.

Safe changes reapplied:
- sort headers remain clickable but visually render as small text
- hover is text underline/highlight, not a box
- default player viewport = 154px
- player rows = ~24px, targeting 6+ visible players
- total tray heights remain 58 / 236 / 332

Untouched:
- app.py
- runtime.py
- top folder navigation
- global legacy.css
- draft board
- ALL/QB/RB/WR/TE and search functionality
- Queue/Roster logic
- CPU/autorefresh

Validation:
- Python compile passed
- _render_sheet_css(0), (1), and (2) each executed successfully
