# FantasySync v6.4.3 — Filter and Board Scroll Fix

## Position sorting buttons

- Forces dark matte button surfaces in all supported browsers.
- Labels use high-contrast light text.
- Active filter uses a blue selected state.
- Adds explicit fallbacks for ALL, QB, RB, WR, and TE keyed buttons.
- Prevents white-on-white labels.

## Draft-board scrolling

- The board now owns its own HTML scroll viewport.
- No longer depends on Streamlit's nested bounded-container wrappers.
- All rounds 1–16 remain inside the natural-height board content.
- Adds a bottom clearance spacer so Round 16 can scroll above the fixed tray
  handle instead of being hidden beneath it.
- Mouse wheel, trackpad, and the subtle scrollbar are supported.

## Preserved

- Three tray states
- Queue/Roster controls and roster component fix
- Hidden autorefresh
- 180 ms CPU cadence
- Compact header
- Current draft colors, timer, keeper, trade, queue, and roster logic

## GitHub update

Upload the complete package, or replace:

```text
app.py
components/draft_board.py
components/bottom_sheet.py
```
