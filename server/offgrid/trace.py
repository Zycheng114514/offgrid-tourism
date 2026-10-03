"""Run one host message through the pipeline without saving anything, and report every step.

Used by the /pipeline demo page. Each step's output comes from the same code the
SMS service uses; nothing here is a hand-written illustration except the sample
webhook body, whose format is taken from the gateway app's documentation.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .dialog import ASK, Dialog, listing_from_extraction, missing_fields
from .extract import extract, system_prompt
from .llm import LLM
from .pack import public_listing
from .region import Region
from .search import find, result_line
from .store import Store

GSM7 = set("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§"
           "¿abcdefghijklmnopqrstuvwxyzäöñüà")
GSM7_EXT = set("^{}\\[~]|€")


def sms_parts(text: str) -> dict:
    gsm = all(c in GSM7 or c in GSM7_EXT for c in text)
    length = sum(2 if c in GSM7_EXT else 1 for c in text) if gsm else len(text)
    single, multi = (160, 153) if gsm else (70, 67)
    parts = 1 if length <= single else -(-length // multi)
    return {"chars": len(text), "encoding": "GSM-7" if gsm else "UCS-2", "parts": parts}


def trace(text: str, region: Region, llm: LLM, store: Store, phone: str = "+620000000999") -> dict:
    text = (text or "").strip()
    cmd, lang, rest = region.command(text)
    route = _route(cmd, rest)
    steps: list[dict] = []
    steps.append({"id": "sms", "title": "SMS arrives", "data": {"from": phone, "text": text, **sms_parts(text)}})
    steps.append({"id": "gateway", "title": "Gateway phone forwards it", "data": {
        "webhook": "POST /webhooks/sms-gate",
        "body": {"event": "sms:received", "payload": {"messageId": "(set by the phone)", "message": text,
                                                       "sender": phone, "receivedAt": datetime.now(timezone.utc).isoformat(timespec="seconds")}},
        "note": "Body format from the SMS Gateway for Android documentation. The server answers at once and works on the message in the background."}})
    steps.append({"id": "route", "title": "What kind of message", "data": {
        "first_word_command": cmd, "language": lang, "route": route}})
    result = {"region": {"id": region.id, "display_name": region.display_name, "host_language": region.host_lang,
                         "currency": region.currency["code"], "places_in_gazetteer": len(region.places)},
              "route": route, "steps": steps}
    if route != "new report":
        result["note"] = ("This message is not a new business report, so the listing steps do not run. "
                          "Try one of the example reports.")
        if route == "traveller search":
            steps.append({"id": "search", "title": "Search reply", "data": {
                "reply": _search_text(rest, lang or region.traveller_lang, region, store.listings(region.id, state="confirmed"))}})
        return result

    ex = extract(text, region, llm)
    steps.append({"id": "rules", "title": "Fixed rules read the clear parts", "data": {
        "category": {"value": ex.sources.get("category") == "rules" and ex.category or None, "from_words": ex.evidence.get("category")},
        "price": {"value": ex.price if ex.sources.get("price") == "rules" else None, "from_words": ex.evidence.get("price")},
        "hours": {"value": ex.hours if ex.sources.get("hours") == "rules" else None, "from_words": ex.evidence.get("hours")},
        "capacity": {"value": ex.capacity if ex.sources.get("capacity") == "rules" else None, "from_words": ex.evidence.get("capacity")},
        "village": {"value": (ex.place or {}).get("name") if ex.sources.get("village") == "rules" else None,
                    "from_words": ex.evidence.get("place"), "match": ex.evidence.get("place_match"),
                    "coordinates": [ex.place["lat"], ex.place["lon"]] if ex.place and ex.sources.get("village") == "rules" else None},
        "evidence": {k: v for k, v in ex.evidence.items() if v and k != "place_match"}}})
    steps.append({"id": "model", "title": "Language model reads the rest", "data": {
        "provider": llm.label if llm.enabled else "none",
        "simulated": llm.config.provider == "simulated",
        "prompt": system_prompt(region) if llm.enabled else None,
        "output": ex.model_output, "error": ex.llm_error}})
    steps.append({"id": "checks", "title": "Checks against the message", "data": {"checks": ex.checks}})

    listing = listing_from_extraction(ex, f"{region.id}-preview", region, {"id": "h-preview"}, phone, text)
    fields = {k: listing.get(k) for k in ("category", "name", "village", "landmark", "offer_original", "offer_en",
                                         "price", "hours", "capacity")}
    steps.append({"id": "merge", "title": "Listing fields and where each came from", "data": {
        "fields": fields, "sources": ex.sources, "missing": missing_fields(listing)}})

    dialog = Dialog(region, store, llm, lambda *_: None)
    missing = missing_fields(listing)
    if missing:
        sms = [{"to": "host", "text": region.template(ASK[missing[0]]), "why": f"missing: {missing[0]}"}]
        sms += [{"to": "host", "text": region.template(ASK[m]), "why": f"then, if still missing: {m}"} for m in missing[1:]]
        sms.append({"to": "host", "text": region.template("confirm", summary="…"), "why": "after all answers: summary to confirm"})
    else:
        sms = [{"to": "host", "text": region.template("confirm", summary=dialog.summary(listing)), "why": "nothing missing: summary to confirm"}]
    sms += [{"to": "service", "text": "1", "why": "host confirms"},
            {"to": "host", "text": region.template("ask_publish_phone"), "why": "first listing from this number: ask consent"},
            {"to": "host", "text": region.template("confirmed", name=listing.get("name") or "…"), "why": "listing goes live"}]
    steps.append({"id": "ask", "title": "Follow-up questions and confirmation by SMS", "data": {"sms": sms}})

    preview = dict(listing)
    preview["status"] = {"state": "confirmed", "open_today": None, "last_confirmed_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    steps.append({"id": "store", "title": "Stored record", "data": {"listing": preview, "note": "Saved in SQLite with the original message. Voice is never stored."}})
    steps.append({"id": "pack", "title": "Region pack for travellers' phones", "data": {
        "entry": public_listing(preview),
        "note": "Only confirmed listings. The phone number is left out until the host replies YA to the consent question."}})

    if not missing and listing.get("village"):
        cat_words = region.lang_words(region.traveller_lang).get("category", {}).get(listing["category"], [])
        query = f"{cat_words[0] if cat_words else ''} {listing['village']}".strip()
        pool = store.listings(region.id, state="confirmed") + [preview]
        ranked = find(query, region, pool)
        rank = next((i + 1 for i, l in enumerate(ranked) if l["id"] == preview["id"]), None)
        steps.append({"id": "traveller", "title": "A traveller finds it", "data": {
            "offline_query": query, "rank": rank, "results": len(ranked),
            "sms_query": f"SEARCH {query}",
            "sms_reply": _search_text(query, region.traveller_lang, region, pool)}})
    else:
        steps.append({"id": "traveller", "title": "A traveller finds it", "data": {
            "note": "Travellers see the listing only after the host answers the questions above and confirms."}})
    return result


def _route(cmd: str | None, rest: str) -> str:
    if cmd == "search":
        return "traveller search"
    if cmd == "help" and not rest:
        return "help"
    if cmd in ("open_today", "closed_today") and len(rest.split()) <= 2:
        return "status update (open or closed today)"
    if cmd in ("confirm_yes", "confirm_no"):
        return "answer to a question"
    return "new report"


def _search_text(query: str, lang: str, region: Region, listings: list[dict]) -> str:
    items = find(query, region, listings)[:3]
    if not items:
        return region.template("no_results", lang)
    return "\n".join([region.template("results_header", lang)] + [result_line(i + 1, l, region, lang) for i, l in enumerate(items)])
