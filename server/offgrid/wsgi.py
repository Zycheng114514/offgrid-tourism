"""WSGI app for hosts that run code only per request and keep no disk (e.g. Vercel).

Serves the parts of the demo that keep no state: landing page, pipeline
walkthrough, traveller app, region pack, examples. The demo listings are loaded
into memory at start-up and only read afterwards. The host demo and the SMS
simulator need a server that keeps conversations; requests for them are sent to
our own server (deploy/live_server_url.txt) when its address is known.
"""

from __future__ import annotations

import json
import mimetypes
import os
from urllib.parse import parse_qs

from .llm import LLM, LLMConfig
from .pack import build_pack
from .region import ROOT, Region
from .seed import load_seed
from .store import Store
from .chat import answer as chat_answer
from .trace import trace

REGION = Region(os.environ.get("REGION_PROFILE", "regions/samosir.json"))
EXAMPLES_PATH = ROOT / "models" / "simulated" / f"{REGION.id}.json"
STATIC_DIR = ROOT / "server" / "offgrid" / "static"
PWA_DIR = ROOT / "mobile" / "pwa"
STORE = Store(":memory:")
load_seed(ROOT / "data" / "synthetic" / f"seed_listings_{REGION.id}.json", REGION, STORE)
LLM_SIMULATED = LLM(LLMConfig(provider="simulated", simulated_path=str(EXAMPLES_PATH)))
LLM_OFF = LLM(LLMConfig(provider="none"))
mimetypes.add_type("application/manifest+json", ".webmanifest")
mimetypes.add_type("text/javascript", ".js")


def live_server_url() -> str:
    url = os.environ.get("LIVE_SERVER_URL", "")
    path = ROOT / "deploy" / "live_server_url.txt"
    if not url and path.is_file():
        url = path.read_text().strip()
    return url.rstrip("/")


def _json(start, obj, status="200 OK"):
    body = json.dumps(obj, ensure_ascii=False).encode()
    start(status, [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body))),
                   ("Cache-Control", "no-store")])
    return [body]


def _file(start, base, rel: str):
    target = (base / rel).resolve()
    if base.resolve() not in target.parents or not target.is_file():
        return _json(start, {"error": "not found"}, "404 Not Found")
    body = target.read_bytes()
    headers = [("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream"),
               ("Content-Length", str(len(body)))]
    if target.name in ("sw.js", "index.html", "pipeline.html"):
        headers.append(("Cache-Control", "no-cache"))
    start("200 OK", headers)
    return [body]


def _redirect(start, location: str):
    start("302 Found", [("Location", location), ("Content-Length", "0")])
    return [b""]


def config() -> dict:
    return {"region_id": REGION.id, "display_name": REGION.display_name, "timezone": REGION.timezone,
            "sms_number": "", "simulator": False, "stateless": True, "gateway": "none",
            "llm": LLM_SIMULATED.label, "llm_simulated": True, "live_server_url": live_server_url()}


def app(environ, start_response):
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "/") or "/"
    query = {k: v[0] for k, v in parse_qs(environ.get("QUERY_STRING", "")).items()}

    if method == "GET":
        if path in ("/", ""):
            return _file(start_response, STATIC_DIR, "index.html")
        if path.rstrip("/") == "/pipeline":
            return _file(start_response, STATIC_DIR, "pipeline.html")
        if path.startswith("/static/"):
            return _file(start_response, STATIC_DIR, path[len("/static/"):])
        if path == "/app":
            return _redirect(start_response, "/app/")
        if path == "/app/":
            return _file(start_response, PWA_DIR, "index.html")
        if path.startswith("/app/"):
            return _file(start_response, PWA_DIR, path[len("/app/"):])
        if path.rstrip("/") == "/host":
            live = live_server_url()
            if live:
                return _redirect(start_response, live + "/host")
            return _json(start_response, {"error": "the host demo runs on our own server"}, "404 Not Found")
        if path == "/api/config":
            return _json(start_response, config())
        if path == "/api/examples":
            return _json(start_response, json.loads(EXAMPLES_PATH.read_text()))
        if path == f"/api/regions/{REGION.id}/pack.json":
            return _json(start_response, build_pack(REGION, STORE, query.get("village"), float(query.get("radius_km", 10))))
        if path == "/healthz":
            return _json(start_response, {"ok": True, **config()})

    if method == "POST" and path == "/api/chat":
        try:
            size = int(environ.get("CONTENT_LENGTH") or 0)
            body = json.loads(environ["wsgi.input"].read(size) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return _json(start_response, {"error": "bad json"}, "400 Bad Request")
        question = str(body.get("question", "")).strip()
        if not question:
            return _json(start_response, {"error": "question is required"}, "400 Bad Request")
        return _json(start_response, chat_answer(question, REGION, STORE.listings(REGION.id), LLM_SIMULATED, body.get("lang")))

    if method == "POST" and path == "/api/pipeline/trace":
        try:
            size = int(environ.get("CONTENT_LENGTH") or 0)
            body = json.loads(environ["wsgi.input"].read(size) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return _json(start_response, {"error": "bad json"}, "400 Bad Request")
        text = str(body.get("text", "")).strip()[:480]
        if not text:
            return _json(start_response, {"error": "text is required"}, "400 Bad Request")
        llm = LLM_OFF if body.get("model") == "off" else LLM_SIMULATED
        return _json(start_response, trace(text, REGION, llm, STORE))

    return _json(start_response, {"error": "not found"}, "404 Not Found")


if __name__ == "__main__":  # local test: python -m offgrid.wsgi  (from server/)
    from wsgiref.simple_server import make_server
    port = int(os.environ.get("PORT", "8791"))
    print(f"serving the stateless demo on http://127.0.0.1:{port}")
    make_server("127.0.0.1", port, app).serve_forever()
