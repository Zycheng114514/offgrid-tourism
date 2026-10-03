"""Search confirmed listings: used by the traveller SMS service and the region pack.

Fixed rules only: category words, a place name, 'cheap', 'now'. The web app
runs the same logic in JavaScript on the downloaded pack.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from .region import Region, km, norm
from .store import Store

MAX_RESULTS = 3
NEARBY_KM = 15


def is_open_now(listing: dict, region: Region, when: datetime | None = None) -> bool | None:
    local = when or datetime.now(ZoneInfo(region.timezone))
    status = listing.get("status", {})
    if status.get("open_today_date") == local.date().isoformat() and status.get("open_today") is not None:
        if status["open_today"] is False:
            return False
    hours = listing.get("hours")
    if not hours:
        return status.get("open_today") if status.get("open_today_date") == local.date().isoformat() else None
    hhmm = local.strftime("%H:%M")
    return hours["open"] <= hhmm < hours["close"]


def relevance(query: str, listing: dict) -> int:
    hay = " " + norm(" ".join(str(listing.get(k) or "") for k in ("name", "offer_original", "offer_en", "landmark"))) + " "
    return sum(1 for w in set(norm(query).split()) if len(w) >= 3 and f" {w} " in hay)


def find(query: str, region: Region, listings: list[dict], when: datetime | None = None) -> list[dict]:
    category, _ = region.category_of(query)
    place = region.match_place(query)
    cheap = region.has_word(query, "cheap")
    now_only = region.has_word(query, "now")
    items = [l for l in listings if l.get("status", {}).get("state") == "confirmed"]
    if category:
        items = [l for l in items if l.get("category") == category]
    if now_only:
        items = [l for l in items if is_open_now(l, region, when) is not False]
    if place:
        here = (place["lat"], place["lon"])

        def dist(l):
            loc = l.get("location")
            return km(here, (loc["lat"], loc["lon"])) if loc else 9e9
        items = [l for l in items if dist(l) <= NEARBY_KM]
        items.sort(key=lambda l: (0 if l.get("village") == place["name"] else 1, -relevance(query, l), dist(l)))
    else:
        items.sort(key=lambda l: -relevance(query, l))
    if cheap:
        items.sort(key=lambda l: (l.get("price") or {}).get("min", 9e18))
    return items


def result_line(i: int, l: dict, region: Region, lang: str) -> str:
    offer = l.get("offer_en") if lang != region.host_lang and l.get("offer_en") else l.get("offer_original") or ""
    parts = [f"{i}. {l['name']} ({l['village']})", offer[:40], region.format_price(l.get("price"), lang)]
    if l.get("hours"):
        parts.append(f"{l['hours']['open']}-{l['hours']['close']}")
    phone = l.get("contact", {}).get("phone") if l.get("contact", {}).get("publish_phone") else None
    if phone:
        parts.append(phone)
    return " ".join(p for p in parts if p)


def search_reply(query: str, lang: str, region: Region, store: Store) -> str:
    items = find(query, region, store.listings(region.id, state="confirmed"))[:MAX_RESULTS]
    if not items:
        return region.template("no_results", lang)
    return "\n".join([region.template("results_header", lang)] +
                     [result_line(i + 1, l, region, lang) for i, l in enumerate(items)])
