# FantasySync v6.4.2 — Remove Obsolete Roster Path

The exact `v640-roster-*` markup shown in the deployed app came from the old
v6.4.0 roster renderer.

v6.4.2 removes that renderer from the component architecture:

- `components/roster_panel.py` is no longer used or included.
- The isolated roster renderer now lives directly in
  `components/bottom_sheet.py`.
- Replacing `bottom_sheet.py` guarantees the obsolete roster renderer cannot
  execute.
- The roster remains an isolated HTML document with its own scrollbar through
  all 16 slots.

Preserved:
- compact header
- three tray states
- Queue/Roster controls
- R1-R16 board scrolling
- hidden autorefresh
- 180 ms CPU cadence
- existing draft, timer, keeper, trade, queue, and roster logic

GitHub:
1. Replace `app.py`.
2. Replace `components/bottom_sheet.py`.
3. Replace `components/__init__.py`.
4. Delete `components/roster_panel.py`.
