"""Load synthetic listings so the demo has data before any host has texted.

Seed file: a JSON list of listings with the fields a host would have sent. The
village must exist in the region gazetteer; coordinates come from there.
"""

from __future__ import annotations

import json
import pathlib

from .region import Region
from .store import Store, now


def load_seed(path: str | pathlib.Path, region: Region, store: Store) -> int:
    items = json.loads(pathlib.Path(path).read_text())
    count = 0
    for item in items:
        place = region.match_place(item["village"])
        if place is None:
            raise ValueError(f"village not in gazetteer: {item['village']}")
        host = store.host_for(item["phone"])
        publish = item.get("publish_phone", True)
        store.set_consent(host["id"], publish)
        listing = {
            "id": store.next_listing_id(region.id),
            "region_id": region.id,
            "category": item["category"],
            "name": item["name"],
            "village": place["name"],
            "landmark": item.get("landmark"),
            "location": {"lat": place["lat"], "lon": place["lon"], "precision": "village"},
            "offer_original": item["offer_original"],
            "offer_en": item.get("offer_en"),
            "language": region.host_lang,
            "price": {**item["price"], "currency": region.currency["code"]} if item.get("price") else None,
            "hours": item.get("hours"),
            "capacity": item.get("capacity"),
            "contact": {"phone": item["phone"], "publish_phone": publish, "consent_at": now()},
            "source": {"channel": "seed", "host_id": host["id"], "message_ids": [], "received_at": now(),
                       "data_origin": "synthetic"},
            "status": {"state": "confirmed", "open_today": None, "last_confirmed_at": item.get("last_confirmed_at", now())},
            "extraction": {"method": "manual", "model": None, "missing_fields_asked": []},
        }
        store.save_listing(listing)
        count += 1
    return count
