# FantasySync v6.7.0 — Top Navigation Shell

Built from v6.6.0.

## Sidebar removed

- The Streamlit left sidebar is no longer rendered.
- The sidebar collapse control is hidden.
- Draft Room is the default page every new session.
- The application now has one stable full-width viewport.

## Top navigation

Former sidebar destinations now appear as compact tabs across the top:

- Draft Room
- Rankings
- Recommendations
- Draft Grades
- Data Status
- League History
- Settings
- Import / Export
- Help & Docs

Existing underlying page routes are preserved for this shell migration.

## Draft utilities

Reset Draft and Download State have moved to the right side of the top navigation strip.

## Layout

- Main application uses `100vw` consistently.
- Draft board and top header inherit one stable width.
- Player tray left edge is permanently `0`; it no longer depends on sidebar state.
- Drag grip is centered against the browser viewport.

## Preserved

- Draft-board component and board logic
- v6.6.0 tray behavior
- R1–R16 board scrolling
- Hidden autorefresh
- 180 ms CPU cadence
- Player filters, queue, roster, keepers, trades, and timer logic

## GitHub update

Replace:

```text
app.py
components/bottom_sheet.py
```
