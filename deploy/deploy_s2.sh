#!/usr/bin/env bash
# Deploy the demo to s2 (Oracle cloud, ARM64, Ubuntu) and expose it through a Cloudflare quick tunnel.
# Usage: deploy/deploy_s2.sh [host] [--reset-data]   (default host alias: s2-ts, the Tailscale address)
#   --reset-data  move the demo database aside (kept as a timestamped copy) and load the seed listings again
# Copies files only (never deletes on the server), restarts the app and the tunnel in tmux, prints the public URL.
set -euo pipefail
HOST="s2-ts"; RESET=0
for arg in "$@"; do case "$arg" in --reset-data) RESET=1 ;; *) HOST="$arg" ;; esac; done
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE_DIR="offgrid-tourism"

rsync -az --relative \
  --exclude '__pycache__' --exclude '*.sqlite' \
  -e ssh -C \
  "$ROOT/./server/offgrid" "$ROOT/./mobile/pwa" "$ROOT/./regions" "$ROOT/./models" "$ROOT/./schemas" \
  "$ROOT/./data/real/osm" "$ROOT/./data/synthetic" \
  "$HOST:$REMOTE_DIR/"

ssh "$HOST" RESET="$RESET" bash -s <<'REMOTE'
set -euo pipefail
cd ~/offgrid-tourism
if [ "${RESET:-0}" = 1 ] && [ -f data/runtime/samosir.sqlite ]; then
  mv data/runtime/samosir.sqlite "data/runtime/samosir.$(date +%Y%m%d-%H%M%S).sqlite.bak"
fi
if [ ! -f .env ]; then
  cat > .env <<'ENV'
REGION_PROFILE=regions/samosir.json
LLM_PROVIDER=simulated
SMS_GATEWAY=simulator
SIMULATOR=1
HOST=127.0.0.1
PORT=8000
ENV
fi
mkdir -p data/runtime ~/bin
if [ ! -s data/runtime/samosir.sqlite ]; then (cd server && python3 -m offgrid seed); fi
if [ ! -x ~/bin/cloudflared ]; then
  curl -fsSL -o ~/bin/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64
  chmod +x ~/bin/cloudflared
fi
tmux kill-session -t offgrid 2>/dev/null || true
tmux new-session -d -s offgrid "cd ~/offgrid-tourism/server && python3 -m offgrid serve 2>&1 | tee -a ~/offgrid-tourism/data/runtime/server.log"
if ! tmux has-session -t tunnel 2>/dev/null; then
  : > ~/offgrid-tourism/data/runtime/tunnel.log
  tmux new-session -d -s tunnel "~/bin/cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8000 2>&1 | tee -a ~/offgrid-tourism/data/runtime/tunnel.log"
fi
for i in $(seq 1 30); do
  URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' ~/offgrid-tourism/data/runtime/tunnel.log | tail -1 || true)
  [ -n "$URL" ] && break; sleep 1
done
sleep 2
curl -s -m 5 http://127.0.0.1:8000/healthz; echo
echo "PUBLIC_URL=${URL:-not found yet, see data/runtime/tunnel.log}"
REMOTE
