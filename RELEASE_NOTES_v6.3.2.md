# FantasySync v6.3.2 — Queue/Roster Interaction Fix

Built directly from v6.3.1.

## Queue and Roster controls

Streamlit tabs were replaced with persistent Queue and Roster buttons.

Why:

- Streamlit tabs reset to the first tab during rapid CPU autorefresh reruns.
- A session-state-backed selection persists through every CPU pick.
- The buttons remain clickable while CPU drafting is active.

## Roster scrolling

Queue/Roster content now renders inside its own bounded utility viewport.

- Draft tray: 210 px utility viewport
- Expanded tray: 340 px utility viewport
- Mouse wheel and trackpad scrolling
- Visible, subtle internal scrollbar
- Complete bench and roster slots remain accessible

## Preserved

- Three tray snap states and current dimensions
- Independent R1–R16 board scrolling
- Hidden autorefresh mount
- 180 ms CPU cadence
- Player row sizes and typography
- Right-aligned tray arrows
- Queue behavior, roster assignment, keepers, trades, and draft logic

## GitHub update

Upload the complete package, or replace:

```text
app.py
components/bottom_sheet.py
```
