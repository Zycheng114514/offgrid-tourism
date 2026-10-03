"""Turn one host message into listing fields.

Order: fixed rules first (prices, hours, capacity, place names, category words),
then the model for what rules cannot read (business name, what is offered,
landmark, English translation). A model answer is kept only if it can be traced
back to the message: names and landmarks must appear in it, numbers must match
a number in it, places must be in the region's gazetteer. Anything missing is
asked for by SMS instead of guessed.
"""

from __future__ import annotations

import json
import re
import string
from dataclasses import dataclass, field

from . import rules
from .llm import LLM
from .region import ROOT, Region, norm

PROMPT_PATH = ROOT / "models" / "prompts" / "extract_listing.txt"
FIELDS = ["category", "name", "village", "landmark", "offer", "offer_en",
          "price_min", "price_max", "price_unit", "open", "close", "capacity"]
CATEGORIES = ["food", "lodging", "transport", "guide", "other"]
PRICE_UNITS = ["per_meal", "per_item", "per_night", "per_day", "per_person", "per_trip", "other"]


def output_schema() -> dict:
    def nullable(t: str) -> dict:
        return {"type": [t, "null"]}
    props = {name: nullable("string") for name in FIELDS}
    props.update({
        "category": {"type": ["string", "null"], "enum": CATEGORIES + [None]},
        "price_unit": {"type": ["string", "null"], "enum": PRICE_UNITS + [None]},
        "price_min": nullable("number"),
        "price_max": nullable("number"),
        "capacity": nullable("integer"),
    })
    return {"type": "object", "properties": props, "required": FIELDS, "additionalProperties": False}


def system_prompt(region: Region) -> str:
    example = region.llm_example or {"message": "", "json": {}}
    return string.Template(PROMPT_PATH.read_text()).substitute(
        language_name=region.data.get("language_names", {}).get(region.host_lang, region.host_lang),
        currency_code=region.currency["code"],
        example_message=example["message"],
        example_json=json.dumps(example["json"], ensure_ascii=False),
    )


@dataclass
class Extraction:
    category: str | None = None
    name: str | None = None
    place: dict | None = None
    village_text: str | None = None
    landmark: str | None = None
    offer_original: str | None = None
    offer_en: str | None = None
    price: dict | None = None
    hours: dict | None = None
    capacity: int | None = None
    method: str = "rules"
    model: str | None = None
    llm_seconds: float = 0.0
    llm_error: str | None = None
    model_output: dict | None = None
    rejected: dict = field(default_factory=dict)  # model answers dropped by the checks
    sources: dict = field(default_factory=dict)   # listing field -> 'rules' | 'model' | 'message'
    evidence: dict = field(default_factory=dict)  # the words each rule matched
    checks: list = field(default_factory=list)    # one entry per model value: kept / rejected / not used, and why

    def missing(self) -> list[str]:
        need = ["category", "name", "place", "offer_original", "price"]
        if self.category == "food":
            need.append("hours")
        return [f for f in need if getattr(self, f) in (None, "")]


def _numbers_in(text: str, region: Region) -> set[float]:
    found = set()
    for raw in re.findall(r"\d+(?:[.,]\d+)*", text):
        for has_mult in (False, True):
            value = rules._to_number(raw, region, has_mult)
            if value is not None:
                found.add(value)
    mults = [1.0] + [float(m) for m in region.currency.get("multipliers", {}).values()]
    return {round(v * m, 2) for v in found for m in mults}


def _appears(value: str | None, text: str, min_share: float = 0.6) -> bool:
    """True if most words of value appear in the message (guards against invented names)."""
    words = [w for w in norm(value or "").split() if len(w) > 1]
    if not words:
        return False
    hay = " " + norm(text) + " "
    hits = sum(1 for w in words if f" {w} " in hay or w in hay.replace(" ", ""))
    return hits / len(words) >= min_share


def extract(text: str, region: Region, llm: LLM | None = None) -> Extraction:
    r = rules.parse(text, region)
    ex = Extraction(category=r["category"], price=r["price"], hours=r["hours"],
                    capacity=r["capacity"], place=r["place"], evidence=r["evidence"])
    for attr, name in (("category", "category"), ("price", "price"), ("hours", "hours"),
                       ("capacity", "capacity"), ("place", "village")):
        if getattr(ex, attr) is not None:
            ex.sources[name] = "rules"
    if llm is not None and llm.enabled:
        res = llm.complete_json(system_prompt(region), text, output_schema())
        ex.method, ex.model, ex.llm_seconds, ex.llm_error = "rules+llm", llm.label, res.seconds, res.error
        ex.model_output = res.data
        if res.data:
            _merge_model_answer(ex, res.data, text, region)
    if not ex.offer_original:
        ex.offer_original = text.strip()[:160]  # the host's own words are the fallback description
        ex.sources["offer_original"] = "message"
    if ex.price is not None and _plausible_price(ex.price, ex.category, region) is None:
        ex.checks.append({"field": "price", "value": ex.price, "result": "rejected",
                          "reason": f"outside the plausible range for {ex.category or 'other'} in this region"})
        ex.rejected["price"] = ex.price
        ex.price = None
        ex.sources.pop("price", None)
    return ex


def _merge_model_answer(ex: Extraction, d: dict, text: str, region: Region) -> None:
    """Take model values only where rules found nothing and the value can be traced to the message."""
    ev = ex.evidence or {}

    def check(field_name: str, value, result: str, reason: str):
        ex.checks.append({"field": field_name, "value": value, "result": result, "reason": reason})
        if result == "rejected":
            ex.rejected[field_name] = value
        elif result == "kept":
            ex.sources[field_name] = "model"
        return value if result == "kept" else None

    if d.get("category") is not None:
        if ex.category is not None:
            check("category", d["category"], "not used", f"rules already found '{ex.category}' from the word '{ev.get('category')}'")
        elif d["category"] in CATEGORIES:
            ex.category = check("category", d["category"], "kept", "rules found no category word")
        else:
            check("category", d["category"], "rejected", "not one of the allowed categories")
    for key, share in (("name", 0.6), ("landmark", 0.5)):
        if d.get(key):
            ok = _appears(d[key], text, share)
            setattr(ex, key, check(key, d[key], "kept" if ok else "rejected",
                                   "its words appear in the message" if ok else "not found in the message"))
    if d.get("offer"):
        ex.offer_original = check("offer_original", d["offer"], "kept",
                                  "description in the host's language; the host checks it before confirming")
    if d.get("offer_en"):
        ex.offer_en = check("offer_en", d["offer_en"], "kept",
                            "translation; cannot be checked against the message, so the original is always shown with it")
    ex.village_text = d.get("village")
    if d.get("village"):
        if ex.place is not None:
            check("village", d["village"], "not used", f"rules already matched '{ex.place['name']}' in the village list")
        else:
            place = region.match_place(d["village"])
            if place is None:
                check("village", d["village"], "rejected", "not in the region's village list")
            elif not _appears(place["name"], text, 0.5):
                check("village", d["village"], "rejected", "place not named in the message")
            else:
                check("village", d["village"], "kept", "in the village list and named in the message")
                ex.place = place

    nums = _numbers_in(text, region)
    if isinstance(d.get("price_min"), (int, float)):
        lo, hi = float(d["price_min"]), d.get("price_max")
        hi = float(hi) if isinstance(hi, (int, float)) else None
        unit = d.get("price_unit") if d.get("price_unit") in PRICE_UNITS else "other"
        value = {"min": lo, "max": hi, "currency": region.currency["code"], "unit": unit}
        if ex.price is not None:
            check("price", value, "not used", f"rules already read '{ev.get('price')}'")
        elif round(lo, 2) in nums and (hi is None or round(hi, 2) in nums):
            ex.price = check("price", value, "kept", "the amount matches a number in the message")
        else:
            check("price", value, "rejected", "amount not found in the message")
    if ex.price and ex.price.get("unit") in (None, "other") and d.get("price_unit") in PRICE_UNITS \
            and d["price_unit"] != "other" and ex.sources.get("price") == "rules":
        ex.price["unit"] = d["price_unit"]
        ex.checks.append({"field": "price unit", "value": d["price_unit"], "result": "kept",
                          "reason": "rules read the amount but found no unit word"})
    if d.get("open") and d.get("close"):
        hours = {"open": d["open"], "close": d["close"]}
        if ex.hours is not None:
            check("hours", hours, "not used", f"rules already read '{ev.get('hours')}'")
        else:
            ok = _hours_ok(hours, nums)
            ex.hours = check("hours", hours, "kept" if ok else "rejected",
                             "the hours match numbers in the message" if ok else "hours not found in the message")
    if isinstance(d.get("capacity"), int):
        if ex.capacity is not None:
            check("capacity", d["capacity"], "not used", f"rules already read '{ev.get('capacity')}'")
        else:
            ok = float(d["capacity"]) in nums
            ex.capacity = check("capacity", d["capacity"], "kept" if ok else "rejected",
                                "the number appears in the message" if ok else "number not found in the message")


def _hours_ok(hours: dict, nums: set[float]) -> bool:
    for key in ("open", "close"):
        m = re.fullmatch(r"([01]\d|2[0-4]):([0-5]\d)", str(hours.get(key, "")))
        if not m:
            return False
        h = int(m.group(1))
        if float(h) not in nums and float(h - 12) not in nums and not (h == 0 and 12.0 in nums):
            return False
    return hours["open"] < hours["close"]


def _plausible_price(price: dict | None, category: str | None, region: Region) -> dict | None:
    if not price:
        return None
    lo, hi = region.currency.get("plausible_range", {}).get(category or "other", [0, float("inf")])
    if not (lo <= price["min"] <= hi) or (price.get("max") and not (lo <= price["max"] <= hi)):
        return None
    return price
