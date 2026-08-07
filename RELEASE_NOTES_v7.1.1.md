# FantasySync v7.1.1 — Safe Folder Tabs

Built directly from known-good v7.0.3.

Only `styles/legacy.css` changed.

## Visual update
- Existing top navigation now appears as matte file-folder / worksheet tabs.
- Active page is raised and blue.
- Inactive tabs are dark slate.
- Tabs have an angled trailing edge and subtle folder index.
- Reset and State remain utility controls.

## Safety
- No Python files changed.
- app.py is byte-for-byte unchanged.
- No draft-board selectors changed.
- No player-tray selectors changed.
- No Queue/Roster selectors changed.
- No CPU/autorefresh selectors changed.
- Avoids the aggressive hidden-content and negative-z-index rules used in v7.1.0.

## GitHub
Replace only:
`styles/legacy.css`
