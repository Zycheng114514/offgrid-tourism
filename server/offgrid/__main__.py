"""Command line.

    python -m offgrid serve            run the HTTP server (settings from .env / environment)
    python -m offgrid seed [file]      load synthetic listings for the region
    python -m offgrid pack [village]   print a region pack as JSON

Run from the server/ folder, or with PYTHONPATH=server.
"""

from __future__ import annotations

import json
import os
import sys

from .region import ROOT


def load_env(path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def main(argv: list[str]) -> None:
    load_env(ROOT / ".env")
    from . import gateway as gw
    from .app import App, serve
    from .llm import LLM, LLMConfig
    from .pack import build_pack
    from .region import Region
    from .seed import load_seed
    from .store import Store

    region = Region(os.environ.get("REGION_PROFILE", "regions/samosir.json"))
    store = Store(os.environ.get("DB_PATH", str(ROOT / "data" / "runtime" / f"{region.id}.sqlite")))
    cmd = argv[0] if argv else "serve"
    if cmd == "serve":
        config = LLMConfig.from_env()
        if os.environ.get("LLM_EXTRA_JSON"):
            config.extra = json.loads(os.environ["LLM_EXTRA_JSON"])
        examples = str(ROOT / "models" / "simulated" / f"{region.id}.json")
        if config.provider == "simulated" and not config.simulated_path:
            config.simulated_path = examples
        app = App(region, store, LLM(config), gw.from_env(),
                  simulator=os.environ.get("SIMULATOR", "1") == "1",
                  signing_key=os.environ.get("SMSGATE_SIGNING_KEY", ""),
                  sms_number=os.environ.get("SMS_PUBLIC_NUMBER", ""),
                  examples_path=examples)
        serve(app, os.environ.get("HOST", "127.0.0.1"), int(os.environ.get("PORT", "8000")))
    elif cmd == "seed":
        path = argv[1] if len(argv) > 1 else str(ROOT / "data" / "synthetic" / f"seed_listings_{region.id}.json")
        print(f"loaded {load_seed(path, region, store)} listings from {path}")
    elif cmd == "pack":
        print(json.dumps(build_pack(region, store, argv[1] if len(argv) > 1 else None), ensure_ascii=False, indent=1))
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv[1:])
