# FantasySync v6.4.0 — Layout Refactor

## Structural changes

### Compact header component
New file:

```text
components/draft_header.py
```

The Draft Room title, league chips, CPU status, timer, and Start/Pause control
are now rendered in one 54 px strip. The board begins directly beneath it.

### Scrollable roster component
New file:

```text
components/roster_panel.py
```

The full roster is rendered as one HTML scroll viewport rather than many
nested Streamlit elements. This provides a reliable internal scrollbar through
all starter and bench slots.

## Preserved

- Three bottom-sheet states
- Persistent Queue/Roster controls
- R1–R16 board scrolling
- Hidden autorefresh
- 180 ms CPU cadence
- Existing draft, timer, queue, roster, keeper, and trade logic
- Current colors and player-card styling

## GitHub update

Upload the complete package. New required files:

```text
components/draft_header.py
components/roster_panel.py
```
