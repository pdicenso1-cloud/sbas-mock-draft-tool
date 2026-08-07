# FantasySync v6.4.6 — Floating Sleeper-Style Tray Controls

## Updated

- Removed the full-width tray control row.
- Added two small translucent circular ▲ / ▼ buttons.
- Controls float over the tray edge near Queue/Roster.
- Buttons use blur, transparency, subtle borders, and soft shadows.
- Controls remain visible in Collapsed, Draft, and Expanded states.
- The floating dock reserves no vertical page space.
- Positioning avoids Streamlit's Manage app overlay.

## Preserved

- Open- and collapsed-sidebar board widths
- Three tray states
- Player list and Queue/Roster behavior
- R1–R16 board scrolling
- Visible position filters
- Roster component
- Hidden autorefresh
- 180 ms CPU cadence
- Existing draft, timer, keeper, and trade logic

## GitHub update

Replace:

```text
app.py
components/bottom_sheet.py
```
