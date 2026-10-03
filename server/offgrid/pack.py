"""Region pack: the file a traveller's phone downloads to search offline.

Only confirmed listings; a host's phone number only if the host agreed.
"""

from __future__ import annotations

from .region import Region, km
from .store import Store, now

PACK_FORMAT = "offgrid-pack/1"
PUBLIC_FIELDS = ["id", "category", "name", "village", "landmark", "location", "offer_original", "offer_en",
                 "language", "price", "hours", "capacity"]


def public_listing(l: dict) -> dict:
    out = {k: l.get(k) for k in PUBLIC_FIELDS}
    contact = l.get("contact", {})
    out["phone"] = contact.get("phone") if contact.get("publish_phone") else None
    status = l.get("status", {})
    out["last_confirmed_at"] = status.get("last_confirmed_at")
    out["open_today"] = status.get("open_today")
    out["open_today_date"] = status.get("open_today_date")
    out["data_origin"] = l.get("source", {}).get("data_origin")
    return out


def build_pack(region: Region, store: Store, village: str | None = None, radius_km: float = 10.0) -> dict:
    listings = store.listings(region.id, state="confirmed")
    places = region.places
    if village:
        center = region.match_place(village)
        if center:
            here = (center["lat"], center["lon"])
            listings = [l for l in listings if l.get("location") and
                        km(here, (l["location"]["lat"], l["location"]["lon"])) <= radius_km]
            places = [p for p in places if km(here, (p["lat"], p["lon"])) <= radius_km]
    return {
        "format": PACK_FORMAT,
        "generated_at": now(),
        "region": {
            "id": region.id,
            "display_name": region.display_name,
            "timezone": region.timezone,
            "host_language": region.host_lang,
            "traveller_language": region.traveller_lang,
            "currency": {k: region.currency.get(k) for k in ("code", "display", "thousands_separator")},
            "unit_labels": region.unit_labels,
            "words": {lang: {k: w.get(k) for k in ("category", "cheap", "now")} for lang, w in region.words.items()},
        },
        "villages": [{"name": p["name"], "place": p["place"], "lat": round(p["lat"], 5), "lon": round(p["lon"], 5)}
                     for p in places],
        "listings": [public_listing(l) for l in listings],
    }
