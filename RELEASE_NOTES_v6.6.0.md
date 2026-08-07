# FantasySync v6.6.0 — Tray-Only Flex Refactor

Built directly from v6.5.2.

## Scope

Only `components/bottom_sheet.py` and the version/support CSS in `app.py`
were changed. The draft-board component and board styling were not modified.

## Dead-space fix

The tray now uses a single flex layout:

```text
v660_tray
├── Player panel
│   ├── toolbar and table header
│   └── independently scrollable player list
└── Utility panel
    ├── Queue / Roster controls
    └── independently scrollable content
```

The drag component measures the real pixel distance from each scroll viewport
to the bottom of its panel. It no longer relies on guessed fixed offsets.

## Collapsed-sidebar scrolling

- Sidebar open/close changes are detected with `MutationObserver`.
- Player and utility viewports are re-measured after the DOM changes.
- Wheel and touch events are isolated inside the player/utility scroll regions.
- The player list remains scrollable with the sidebar fully retracted.

## Preserved

- Existing drag behavior and saved tray height
- Draft board width, colors, cards, and R1–R16 scrolling
- Open- and closed-sidebar board layouts
- Player filters and draft buttons
- Queue and roster logic
- Hidden autorefresh
- 180 ms CPU cadence
- Timer, keepers, trades, and draft logic

## GitHub update

Replace:

```text
app.py
components/bottom_sheet.py
```
