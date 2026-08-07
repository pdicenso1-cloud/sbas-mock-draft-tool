# GitHub update for FantasySync v7.0.0

For this migration release, upload the full package contents once.

New required folders:

- `fantasysync/`
- `styles/`

Existing required folder:

- `components/`

Replace root `app.py` with the new frozen seven-line entrypoint.

After v7.0.0 is deployed, normal UI releases should not replace `app.py`. Update the owning module instead.
