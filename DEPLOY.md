# Deploy to Streamlit Community Cloud

## 1. Create the GitHub repository

1. Sign in to GitHub.
2. Create a new repository.
3. Recommended repository name: `sbas-mock-draft-tool`.
4. Choose **Public** for the simplest shareable deployment.
5. Do not initialize it with another README, `.gitignore`, or license.
6. Upload every file and folder from this package to the repository root.

The repository root should contain:

```text
app.py
requirements.txt
runtime.txt
README.md
DEPLOY.md
.gitignore
.github/
.streamlit/
data/
```

Do not upload `.venv`, `secrets.toml`, ESPN cookies, SWID, or `ESPN_s2`.

## 2. Deploy the app

1. Open Streamlit Community Cloud.
2. Sign in with GitHub and connect the repository.
3. Select:
   - Repository: `sbas-mock-draft-tool`
   - Branch: `main`
   - Main file path: `app.py`
4. Choose an available app URL, for example:
   `sbas-mock-draft-tool.streamlit.app`
5. Click **Deploy**.

## 3. Share it

Once deployment finishes, copy the `streamlit.app` URL and send it to league mates.

Each visitor gets a separate Streamlit browser session. Draft state can be exported and imported with JSON files from the sidebar.

## Updating the website

Edit files in GitHub or push a new commit. Streamlit Community Cloud watches the connected repository and redeploys changes.

## Future live-data credentials

When database or ranking-provider credentials are added, enter them through the Streamlit Cloud app's **Secrets** settings. Never commit credentials to GitHub.
