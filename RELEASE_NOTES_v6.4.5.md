# FantasySync v6.4.5 — Open Sidebar Width and Tray Controls

## Open-sidebar width

When the left navigation is open:

- Draft Room uses nearly all space between the sidebar and browser edge.
- Main workspace has only 20 px left/right gutters.
- Header, team labels, draft cells, and board viewport expand together.
- Legacy centered max-width constraints are removed.
- The player tray aligns with the wider workspace.

## Tray arrows

- ▲ and ▼ are shifted left of Streamlit's Manage app overlay.
- A protected right-side region prevents the overlay from covering them.
- Buttons remain visible and clickable in collapsed, Draft, and Expanded tray
  states.
- Button z-index and pointer interaction are reinforced.

## Preserved

- Collapsed-sidebar full-width layout
- Position-filter visibility
- R1–R16 board scrolling
- Roster component and Queue/Roster behavior
- Three tray states
- Hidden autorefresh
- 180 ms CPU cadence
- Existing draft, timer, keeper, and trade logic

## GitHub update

Replace:

```text
app.py
components/bottom_sheet.py
```
