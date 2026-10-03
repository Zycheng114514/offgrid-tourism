#!/usr/bin/env bash
# Deploy the demo to a Linux server over SSH and expose it through a Cloudflare quick tunnel.
# Usage: deploy/deploy.sh <ssh-host> [--reset-data]
#   <ssh-host>    any host SSH can reach (an alias from ~/.ssh/config works); needs Python 3.10+, tmux, curl, rsync
#   --reset-data  move the demo database aside (kept as a timestamped copy) and load the seed listings again
# Copies files only (never deletes on the server), restarts the app and the tunnel in tmux, prints the public URL.
set -euo pipefail
HOST=""; RESET=0
for arg in "$@"; do case "$arg" in --reset-data) RESET=1 ;; *) HOST="$arg" ;; esac; done
[ -n "$HOST" ] || { echo "usage: deploy/deploy.sh <ssh-host> [--reset-data]" >&2; exit 2; }
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
tmux kill-session -t offgrid 2>/dev/null || true   # stop the app before touching its database
if [ "${RESET:-0}" = 1 ]; then
  STAMP=$(date +%Y%m%d-%H%M%S)
  for f in data/runtime/samosir.sqlite data/runtime/samosir.sqlite-journal data/runtime/samosir.sqlite-wal; do
    if [ -f "$f" ]; then mv "$f" "${f/samosir./samosir.$STAMP.}.bak"; fi
  done
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
  case "$(uname -m)" in aarch64|arm64) ARCH=arm64 ;; x86_64) ARCH=amd64 ;; *) echo "unsupported CPU: $(uname -m)" >&2; exit 1 ;; esac
  curl -fsSL -o ~/bin/cloudflared "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-$ARCH"
  chmod +x ~/bin/cloudflared
fi
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
