"""HTTP server: SMS webhook, simulator, region packs, and the traveller web app.

Incoming SMS are queued and handled one at a time by a worker thread, so the
webhook answers the gateway at once even when the model takes tens of seconds.
"""

from __future__ import annotations

import json
import mimetypes
import os
import queue
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .dialog import Dialog
from .gateway import Gateway, parse_smsgate_webhook, verify_signature
from .llm import LLM, LLMConfig
from .pack import build_pack, public_listing
from .trace import trace
from .region import ROOT, Region
from .store import Store

PWA_DIR = ROOT / "mobile" / "pwa"
STATIC_DIR = ROOT / "server" / "offgrid" / "static"
mimetypes.add_type("application/manifest+json", ".webmanifest")
mimetypes.add_type("text/javascript", ".js")


class App:
    def __init__(self, region: Region, store: Store, llm: LLM, gateway: Gateway,
                 simulator: bool = True, signing_key: str = "", sms_number: str = "", examples_path: str = ""):
        self.region, self.store, self.llm, self.gateway = region, store, llm, gateway
        self.examples = json.loads(open(examples_path).read()) if examples_path and os.path.isfile(examples_path) else {}
        self.simulator, self.signing_key, self.sms_number = simulator, signing_key, sms_number
        self.dialog = Dialog(region, store, llm, gateway.send, os.environ.get("DATA_ORIGIN", "synthetic"))
        self.inbox: queue.Queue = queue.Queue()
        threading.Thread(target=self._work, daemon=True).start()

    def receive(self, phone: str, text: str, gateway_id: str | None = None) -> bool:
        """Log and queue one incoming SMS. False if it is a duplicate webhook delivery."""
        if not self.store.log_message("in", phone, text, gateway_id):
            return False
        self.inbox.put((phone, text))
        return True

    def _work(self) -> None:
        while True:
            phone, text = self.inbox.get()
            try:
                self.dialog.handle(phone, text)
            except Exception:
                traceback.print_exc()

    def config(self) -> dict:
        return {"region_id": self.region.id, "display_name": self.region.display_name,
                "sms_number": self.sms_number, "timezone": self.region.timezone,
                "simulator": self.simulator, "gateway": self.gateway.kind,
                "llm": self.llm.label if self.llm.enabled else None,
                "llm_simulated": self.llm.config.provider == "simulated"}


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        server_version = "offgrid/0.1"

        def log_message(self, fmt, *args):
            sys.stderr.write(f"[http] {self.address_string()} {fmt % args}\n")

        def _json(self, obj, status: int = 200):
            body = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _file(self, path):
            if not path.is_file():
                return self._json({"error": "not found"}, 404)
            body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            if path.name == "sw.js":
                self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)

        def _body(self) -> bytes:
            return self.rfile.read(int(self.headers.get("Content-Length") or 0))

        def do_GET(self):
            url = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            path = url.path
            if path == "/healthz":
                return self._json({"ok": True, **app.config()})
            if path == "/api/config":
                return self._json(app.config())
            if path == f"/api/regions/{app.region.id}/pack.json":
                return self._json(build_pack(app.region, app.store, q.get("village"), float(q.get("radius_km", 10))))
            if path == "/api/listings":
                return self._json([{**public_listing(l), "state": l["status"]["state"]}
                                   for l in app.store.listings(app.region.id)])
            if path == "/api/messages" and app.simulator:
                return self._json(app.store.messages(q.get("phone"), int(q.get("after", 0))))
            if path == "/api/examples":
                return self._json(app.examples)
            if path == "/api/debug/host" and app.simulator and q.get("phone"):
                host = app.store.host_for(q["phone"])
                return self._json({"conversation": app.store.conversation(q["phone"]),
                                   "listings": app.store.listings(host_id=host["id"]),
                                   "host": {"publish_phone": host.get("publish_phone")}})
            if path in ("/", "/host", "/host/", "/pipeline", "/pipeline/"):
                page = {"/": "index.html", "/host": "host.html", "/pipeline": "pipeline.html"}[path.rstrip("/") or "/"]
                return self._file(STATIC_DIR / page)
            if path.startswith("/static/"):
                return self._safe_file(STATIC_DIR, path[len("/static/"):])
            if path in ("/app", "/app/"):
                return self._file(PWA_DIR / "index.html")
            if path.startswith("/app/"):
                return self._safe_file(PWA_DIR, path[len("/app/"):])
            return self._json({"error": "not found"}, 404)

        def _safe_file(self, base, rel: str):
            target = (base / rel).resolve()
            if base.resolve() not in target.parents:
                return self._json({"error": "not found"}, 404)
            return self._file(target)

        def do_POST(self):
            path = urlparse(self.path).path
            raw = self._body()
            if path == "/webhooks/sms-gate":
                if app.signing_key and not verify_signature(app.signing_key, raw, self.headers.get("X-Timestamp", ""),
                                                            self.headers.get("X-Signature", "")):
                    return self._json({"error": "bad signature"}, 401)
                try:
                    parsed = parse_smsgate_webhook(json.loads(raw or b"{}"))
                except json.JSONDecodeError:
                    return self._json({"error": "bad json"}, 400)
                if parsed:
                    gateway_id, phone, text = parsed
                    app.receive(phone, text, gateway_id)
                return self._json({"ok": True})
            if path == "/api/pipeline/trace":
                try:
                    body = json.loads(raw or b"{}")
                except json.JSONDecodeError:
                    return self._json({"error": "bad json"}, 400)
                text = str(body.get("text", "")).strip()[:480]
                if not text:
                    return self._json({"error": "text is required"}, 400)
                llm = app.llm if body.get("model", "on") != "off" else LLM(LLMConfig(provider="none"))
                return self._json(trace(text, app.region, llm, app.store))
            if path == "/api/simulate" and app.simulator:
                try:
                    body = json.loads(raw or b"{}")
                except json.JSONDecodeError:
                    return self._json({"error": "bad json"}, 400)
                phone, text = str(body.get("from", "")).strip(), str(body.get("text", "")).strip()
                if not phone or not text:
                    return self._json({"error": "from and text are required"}, 400)
                app.receive(phone, text)
                return self._json({"queued": True}, 202)
            return self._json({"error": "not found"}, 404)

    return Handler


def serve(app: App, host: str, port: int) -> None:
    httpd = ThreadingHTTPServer((host, port), make_handler(app))
    print(f"[offgrid] region={app.region.id} gateway={app.gateway.kind} "
          f"llm={app.llm.config.model if app.llm.enabled else 'none'} listening on http://{host}:{port}", file=sys.stderr)
    httpd.serve_forever()
