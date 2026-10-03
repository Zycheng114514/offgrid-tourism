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
                    capacity=r["capacity"], place=r["place"])
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
        ex.rejected["price"] = ex.price
        ex.price = None
        ex.sources.pop("price", None)
    return ex


def _merge_model_answer(ex: Extraction, d: dict, text: str, region: Region) -> None:
    def keep(key: str, value, ok: bool):
        if value in (None, ""):
            return None
        if not ok:
            ex.rejected[key] = value
            return None
        ex.sources[key] = "model"
        return value

    if ex.category is None and d.get("category") in CATEGORIES:
        ex.category = keep("category", d["category"], True)
    ex.name = keep("name", d.get("name"), _appears(d.get("name"), text))
    ex.landmark = keep("landmark", d.get("landmark"), _appears(d.get("landmark"), text, 0.5))
    ex.offer_original = keep("offer_original", d.get("offer"), True)
    ex.offer_en = keep("offer_en", d.get("offer_en"), True)
    ex.village_text = d.get("village")
    if ex.place is None and d.get("village"):
        place = region.match_place(d["village"])
        if place is None:
            ex.rejected["village"] = d["village"]
        else:
            ex.place = keep("village", place, _appears(place["name"], text, 0.5))

    nums = _numbers_in(text, region)
    if ex.price is None and isinstance(d.get("price_min"), (int, float)):
        lo, hi = float(d["price_min"]), d.get("price_max")
        hi = float(hi) if isinstance(hi, (int, float)) else None
        ok = round(lo, 2) in nums and (hi is None or round(hi, 2) in nums)
        unit = d.get("price_unit") if d.get("price_unit") in PRICE_UNITS else "other"
        ex.price = keep("price", {"min": lo, "max": hi, "currency": region.currency["code"], "unit": unit}, ok)
    if ex.price and ex.price.get("unit") in (None, "other") and d.get("price_unit") in PRICE_UNITS:
        ex.price["unit"] = d["price_unit"]  # rules found the amount but no unit word
    if ex.hours is None and d.get("open") and d.get("close"):
        hours = {"open": d["open"], "close": d["close"]}
        ex.hours = keep("hours", hours, _hours_ok(hours, nums))
    if ex.capacity is None and isinstance(d.get("capacity"), int):
        ex.capacity = keep("capacity", d["capacity"], float(d["capacity"]) in nums)


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
