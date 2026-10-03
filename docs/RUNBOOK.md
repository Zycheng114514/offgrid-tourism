# Runbook

## Run locally (Mac or Linux, Python 3.10+, no packages to install)

```bash
cd server
DB_PATH=../data/runtime/dev.sqlite python -m offgrid seed
LLM_PROVIDER=simulated DB_PATH=../data/runtime/dev.sqlite PORT=8790 python -m offgrid serve
```

Open http://127.0.0.1:8790/ (landing), `/host` (host side), `/pipeline` (pipeline walkthrough), `/app/` (traveller side).

Tests (no network, simulated model):

```bash
cd server && python -m unittest discover tests
```

## Deploy the demo to a server

```bash
deploy/deploy.sh <ssh-host>
```

What it does: copies the code and data to `~/offgrid-tourism` on the server (copy only, nothing is deleted there); writes `.env` the first time (simulated model, simulator gateway); seeds the database the first time; restarts the app in tmux session `offgrid`; starts a Cloudflare quick tunnel in tmux session `tunnel` if none is running; prints the public URL.

- The public URL changes whenever the tunnel restarts. Current URL: `grep trycloudflare ~/offgrid-tourism/data/runtime/tunnel.log | tail -1` on the server.
- Logs on the server: `~/offgrid-tourism/data/runtime/server.log`, `tunnel.log`.
- Start over with fresh demo data: `deploy/deploy.sh <ssh-host> --reset-data` (the old database is kept as a timestamped `.bak` copy on the server).

## Connect the Android SMS gateway phone (D4)

A teammate does this on an Android phone with a SIM that can stay on and online.

1. Install "SMS Gateway for Android" (open source, docs at docs.sms-gate.app). Turn on **Cloud server** mode; the app shows a username and password.
2. Register our webhook (replace the values; run from any computer):

   ```bash
   curl -X POST -u USERNAME:PASSWORD -H "Content-Type: application/json" -d '{"url": "https://PUBLIC-URL/webhooks/sms-gate", "event": "sms:received"}' https://api.sms-gate.app/3rdparty/v1/webhooks
   ```

3. On the server, edit `~/offgrid-tourism/.env`: `SMS_GATEWAY=android`, `SMSGATE_USER`, `SMSGATE_PASSWORD`, `SMS_PUBLIC_NUMBER` (the phone's number); then run `deploy/deploy.sh <ssh-host>` again to restart.
4. Text the phone from another phone: `CARI makan Garoga` should come back with three listings.

If the tunnel restarts, its URL changes: register the webhook again with the new URL.

## Vercel (permanent link for the parts that keep no state)

Files: `vercel.json` (sends every request to `api/index.py`), `api/index.py`, `server/offgrid/wsgi.py`. No build step and no dependencies.

Local test of the same app: `cd server && PORT=8791 python -m offgrid.wsgi`, then open http://127.0.0.1:8791/.

First deploy (done once, by the GitHub account that owns the repo):

1. Sign in at vercel.com with GitHub (free Hobby plan).
2. Add New → Project → import `Zycheng114514/offgrid-tourism`. If the repo is not listed, use "Adjust GitHub App Permissions" to give Vercel access to it.
3. Framework Preset: **Other**. Leave Root Directory, build and output settings, and environment variables empty. Deploy.
4. Use the address under **Domains** (e.g. `offgrid-tourism.vercel.app`); the long per-deployment addresses may ask visitors to log in.

After that, every push to `main` redeploys automatically. When our own server's tunnel address changes, update `deploy/live_server_url.txt` and push, so `/host` on Vercel points to the new address.

