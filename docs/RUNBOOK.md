# Runbook

## Run locally (Mac or Linux, Python 3.10+, no packages to install)

```bash
cd server
DB_PATH=../data/runtime/dev.sqlite python -m offgrid seed
LLM_PROVIDER=simulated DB_PATH=../data/runtime/dev.sqlite PORT=8790 python -m offgrid serve
```

Open http://127.0.0.1:8790/ (landing), `/host` (host side), `/app/` (traveller side).

Tests (no network, simulated model):

```bash
cd server && python -m unittest discover tests
```

## Deploy the demo to s2

```bash
deploy/deploy_s2.sh
```

What it does: copies the code and data to `s2:~/offgrid-tourism` (copy only, nothing is deleted there); writes `.env` the first time (simulated model, simulator gateway); seeds the database the first time; restarts the app in tmux session `offgrid`; starts a Cloudflare quick tunnel in tmux session `tunnel` if none is running; prints the public URL.

- The public URL changes whenever the tunnel restarts. Current URL: `grep trycloudflare ~/offgrid-tourism/data/runtime/tunnel.log | tail -1` on s2.
- Logs on s2: `~/offgrid-tourism/data/runtime/server.log`, `tunnel.log`.
- Start over with fresh demo data: on s2, move `data/runtime/samosir.sqlite` aside and run the deploy script again.

## Connect the Android SMS gateway phone (D4)

A teammate does this on an Android phone with a SIM that can stay on and online.

1. Install "SMS Gateway for Android" (open source, docs at docs.sms-gate.app). Turn on **Cloud server** mode; the app shows a username and password.
2. Register our webhook (replace the values; run from any computer):

   ```bash
   curl -X POST -u USERNAME:PASSWORD -H "Content-Type: application/json" -d '{"url": "https://PUBLIC-URL/webhooks/sms-gate", "event": "sms:received"}' https://api.sms-gate.app/3rdparty/v1/webhooks
   ```

3. On s2, edit `~/offgrid-tourism/.env`: `SMS_GATEWAY=android`, `SMSGATE_USER`, `SMSGATE_PASSWORD`, `SMS_PUBLIC_NUMBER` (the phone's number); then run `deploy/deploy_s2.sh` again to restart.
4. Text the phone from another phone: `CARI makan Garoga` should come back with three listings.

If the tunnel restarts, its URL changes: register the webhook again with the new URL.
