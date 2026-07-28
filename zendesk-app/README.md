# Trend Detection — Zendesk Sidebar App (ZAF v2)

Sidebar app for Zendesk Agent Workspace. Calls the FastAPI backend (`../api/`) for similarity search, trend detection, ARR impact, and engineering drafts.

## Prerequisites

- [Zendesk CLI (ZCLI)](https://developer.zendesk.com/documentation/apps/app-developer-guide/zcli/) — `npm install -g @zendesk/zcli`
- FastAPI backend running on port **8000** (see `../README.md`)
- Zendesk **trial or sponsored dev account** for live ticket testing ([free for development](https://developer.zendesk.com/documentation/api-basics/getting-started/getting-a-trial-or-sponsored-account-for-development/))

Without a Zendesk account, use **Demo mode** in the iframe (hardcoded `T-0004`) or the Streamlit demo (`streamlit run app.py`).

## Local development

From the repository root:

```bash
# Terminal 1 — API
pip install -r requirements.txt
uvicorn api.main:app --host 127.0.0.1 --port 8000

# Terminal 2 — ZAF app server
cd zendesk-app
zcli apps:server
```

ZCLI prints a local URL (typically `http://localhost:4567`). To load the app in Zendesk Agent Workspace, append `?zcli_apps=true` to any ticket URL, for example:

```
https://yoursubdomain.zendesk.com/agent/tickets/123?zcli_apps=true
```

## Demo mode (no Zendesk)

1. Start the API on port 8000.
2. Open `assets/iframe.html` in a browser, or run `zcli apps:server` and open the preview URL.
3. Click **Demo mode (T-0004)** — calls `POST /analyze` with the API demo ticket.

## Production notes

- Point `API_BASE` in `assets/iframe.html` to your deployed backend (Vercel, Railway, etc.).
- For production Zendesk, use `client.request()` with a secure proxy instead of direct `fetch` to localhost.
- Upload as a **private app** via ZCLI or Admin Center — Marketplace publish is optional for portfolio use.

## Files

| File | Purpose |
|---|---|
| `manifest.json` | ZAF v2 app config — `ticket_sidebar`, flexible layout |
| `assets/iframe.html` | Sidebar UI — loading, similar tickets, trend, ARR, engineering draft |
