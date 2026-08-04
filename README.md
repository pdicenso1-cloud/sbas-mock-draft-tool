# Susan Boyles Ass Sweat — Mock Draft Tool

A custom 10-team fantasy-football mock draft application featuring:

- Animated snake drafting
- Clickable team selection
- Keeper and traded-pick support
- Position-colored draft tiles
- Available-player rankings and ADP
- Team-aware recommendations
- Live roster tracking
- User pick clock and automatic CPU selections
- Browser-safe draft-state export/import

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

On macOS, you can also run:

```bash
chmod +x launch_mac.command
./launch_mac.command
```

## Deploy

See [`DEPLOY.md`](DEPLOY.md) for GitHub and Streamlit Community Cloud instructions.

## Security

Never commit:

- `.streamlit/secrets.toml`
- ESPN `SWID`
- ESPN `ESPN_s2`
- API keys
- Database service-role keys
