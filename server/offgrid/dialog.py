"""What the server does with each incoming SMS.

Hosts: report -> listing draft -> one question per missing field -> summary ->
'1' to confirm -> consent to show the phone number. BUKA / TUTUP mark today's
status. Travellers: messages starting with a search word get the top results.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable
from zoneinfo import ZoneInfo

from . import rules
from .extract import Extraction, extract
from .llm import LLM
from .region import Region
from .search import search_reply
from .store import Store, now

ASK = {"category": "ask_category", "name": "ask_name", "village": "ask_village",
       "offer_original": "ask_offer", "price": "ask_price", "hours": "ask_hours"}
MAX_ATTEMPTS = 2


def missing_fields(listing: dict) -> list[str]:
    need = ["category", "name", "village", "offer_original", "price"]
    if listing.get("category") == "food":
        need.append("hours")
    return [f for f in need if listing.get(f) in (None, "")]


def listing_from_extraction(ex: Extraction, listing_id: str, region: Region, host: dict, phone: str,
                            message_text: str) -> dict:
    place = ex.place
    return {
        "id": listing_id,
        "region_id": region.id,
        "category": ex.category,
        "name": ex.name,
        "village": place["name"] if place else None,
        "landmark": ex.landmark,
        "location": {"lat": place["lat"], "lon": place["lon"], "precision": "village"} if place else None,
        "offer_original": ex.offer_original,
        "offer_en": ex.offer_en,
        "language": region.host_lang,
        "price": ex.price,
        "hours": ex.hours,
        "capacity": ex.capacity,
        "contact": {"phone": phone, "publish_phone": bool(host.get("publish_phone")), "consent_at": host.get("consent_at")},
        "source": {"channel": "sms", "host_id": host["id"], "message_ids": [], "received_at": now(),
                   "data_origin": "synthetic", "text": message_text},
        "status": {"state": "draft", "open_today": None, "last_confirmed_at": None},
        "extraction": {"method": ex.method, "model": ex.model, "missing_fields_asked": [],
                       "llm_seconds": round(ex.llm_seconds, 1), "llm_error": ex.llm_error,
                       "model_output": ex.model_output, "rejected_model_values": ex.rejected,
                       "field_sources": dict(ex.sources)},
    }


class Dialog:
    def __init__(self, region: Region, store: Store, llm: LLM, send: Callable[[str, str], None],
                 data_origin: str = "synthetic"):
        self.region, self.store, self.llm, self._send = region, store, llm, send
        self.data_origin = data_origin

    def reply(self, phone: str, text: str) -> str:
        self.store.log_message("out", phone, text)
        self._send(phone, text)
        return text

    # ---- entry point ---------------------------------------------------------

    def handle(self, phone: str, text: str) -> str:
        text = (text or "").strip()
        r = self.region
        cmd, lang, rest = r.command(text)
        if cmd == "search":
            return self.reply(phone, search_reply(rest, lang or r.traveller_lang, r, self.store))
        if cmd == "help" and not rest:
            return self.reply(phone, r.template("help" if lang == r.traveller_lang else "welcome", lang))

        conv = self.store.conversation(phone)
        if conv:
            handled = self._continue(phone, text, conv)
            if handled is not None:
                return handled

        if cmd in ("open_today", "closed_today") and len(rest.split()) <= 2:
            return self._open_closed(phone, cmd == "open_today")
        if cmd in ("confirm_yes", "confirm_no"):
            return self.reply(phone, r.template("welcome"))
        return self._new_report(phone, text)

    # ---- host flows ----------------------------------------------------------

    def _new_report(self, phone: str, text: str) -> str:
        host = self.store.host_for(phone)
        ex = extract(text, self.region, self.llm)
        listing = listing_from_extraction(ex, self.store.next_listing_id(self.region.id), self.region, host, phone, text)
        listing["source"]["data_origin"] = self.data_origin
        self.store.save_listing(listing)
        return self._next_step(phone, listing)

    def _next_step(self, phone: str, listing: dict) -> str:
        missing = missing_fields(listing)
        if missing:
            field = missing[0]
            listing["extraction"]["missing_fields_asked"].append(field)
            self.store.save_listing(listing)
            self.store.set_conversation(phone, listing["id"], field)
            return self.reply(phone, self.region.template(ASK[field]))
        listing["status"]["state"] = "awaiting_confirmation"
        self.store.save_listing(listing)
        self.store.set_conversation(phone, listing["id"], "confirm")
        return self.reply(phone, self.region.template("confirm", summary=self.summary(listing)))

    def _continue(self, phone: str, text: str, conv: dict) -> str | None:
        """Handle an answer inside an open conversation. None means: treat as a new message."""
        r = self.region
        listing = self.store.listing(conv["listing_id"]) if conv.get("listing_id") else None
        awaiting = conv["awaiting"]
        if listing is None:
            self.store.clear_conversation(phone)
            return None

        if awaiting == "confirm":
            if r.is_yes(text):
                listing["status"].update(state="confirmed", last_confirmed_at=now())
                self.store.save_listing(listing)
                host = self.store.host_for(phone)
                if host.get("publish_phone") is None:
                    self.store.set_conversation(phone, listing["id"], "consent")
                    return self.reply(phone, r.template("ask_publish_phone"))
                self.store.clear_conversation(phone)
                return self.reply(phone, r.template("confirmed", name=listing["name"]))
            if r.is_no(text):
                listing["status"]["state"] = "closed"
                self.store.save_listing(listing)
                self.store.clear_conversation(phone)
                return self.reply(phone, r.template("rejected"))
            listing["status"]["state"] = "closed"  # a new message replaces the unconfirmed draft
            self.store.save_listing(listing)
            self.store.clear_conversation(phone)
            return None

        if awaiting == "consent":
            if r.is_yes(text) or r.is_no(text) or conv["attempts"] >= MAX_ATTEMPTS:
                publish = r.is_yes(text)
                host = self.store.host_for(phone)
                self.store.set_consent(host["id"], publish)
                for l in self.store.listings(host_id=host["id"]):
                    l["contact"].update(publish_phone=publish, consent_at=now())
                    self.store.save_listing(l)
                self.store.clear_conversation(phone)
                return self.reply(phone, r.template("confirmed", name=listing["name"]))
            self.store.set_conversation(phone, listing["id"], "consent", conv["attempts"] + 1)
            return self.reply(phone, r.template("ask_publish_phone"))

        # awaiting a field
        if self._fill(listing, awaiting, text):
            listing["extraction"].setdefault("field_sources", {})[awaiting] = "host_answer"
            self.store.save_listing(listing)
            return self._next_step(phone, listing)
        if conv["attempts"] + 1 >= MAX_ATTEMPTS:
            listing["status"]["state"] = "closed"
            self.store.save_listing(listing)
            self.store.clear_conversation(phone)
            return self.reply(phone, r.template("rejected"))
        self.store.set_conversation(phone, listing["id"], awaiting, conv["attempts"] + 1)
        return self.reply(phone, r.template(ASK[awaiting]))

    def _fill(self, listing: dict, field: str, text: str) -> bool:
        r = self.region
        if field == "category":
            category, _ = r.category_of(text)
            listing["category"] = category
            return category is not None
        if field == "name":
            listing["name"] = text[:80] or None
            return bool(listing["name"])
        if field == "offer_original":
            listing["offer_original"] = text[:160] or None
            return bool(listing["offer_original"])
        if field == "village":
            place = r.match_place(text)
            if place:
                listing["village"] = place["name"]
                listing["location"] = {"lat": place["lat"], "lon": place["lon"], "precision": "village"}
            return place is not None
        if field == "price":
            price, _ = rules.parse_price(text, r, listing.get("category"))
            if price is None and text.replace(".", "").replace(",", "").strip().isdigit():
                price, _ = rules.parse_price(r.currency["symbols"][0] + " " + text, r, listing.get("category"))
            listing["price"] = price
            return price is not None
        if field == "hours":
            markers = r.lang_words(r.host_lang).get("time", {}).get("markers", [""])
            hours = rules.parse_hours(text, r) or rules.parse_hours(f"{markers[0]} {text}", r)
            listing["hours"] = hours
            return hours is not None
        return False

    def _open_closed(self, phone: str, is_open: bool) -> str:
        host = self.store.host_for(phone)
        mine = [l for l in self.store.listings(host_id=host["id"]) if l["status"]["state"] == "confirmed"]
        if not mine:
            return self.reply(phone, self.region.template("no_listing"))
        today = datetime.now(ZoneInfo(self.region.timezone)).date().isoformat()
        for l in mine:
            l["status"].update(open_today=is_open, open_today_date=today, last_confirmed_at=now())
            self.store.save_listing(l)
        return self.reply(phone, self.region.template("open_ack" if is_open else "closed_ack"))

    # ---- text ----------------------------------------------------------------

    def summary(self, listing: dict) -> str:
        r = self.region
        parts = [f"{listing['name']}, {listing['village']}", (listing.get("offer_original") or "")[:60]]
        parts.append(r.format_price(listing.get("price"), r.host_lang))
        if listing.get("hours"):
            parts.append(f"{listing['hours']['open']}-{listing['hours']['close']}")
        return ", ".join(p for p in parts if p)
