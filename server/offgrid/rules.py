"""Fixed rules that read prices, hours and capacity from a message.

Rules run before any model and take priority over it for these fields. They
only accept clear cases (a currency word or multiplier for prices, a marker
word, minutes or a time-of-day word for hours); anything unclear is left to
the model or to a follow-up question. All words come from the region profile.
"""

from __future__ import annotations

import re

from .region import Region, norm

NUM = r"\d+(?:[.,]\d+)*"
NEVER = r"(?!x)x"


def _alt(words) -> str:
    words = [w for w in words if w]
    return "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)) or NEVER


def _to_number(raw: str, region: Region, has_multiplier: bool) -> float | None:
    """Parse '25', '25.000', '1,5' using the region's separators."""
    dec = region.currency.get("decimal_separator", ".")
    thou = region.currency.get("thousands_separator", ",")
    if has_multiplier:
        m = re.fullmatch(r"(\d+)[.,](\d{1,2})", raw)  # '1,5jt' / '1.5jt'
        if m:
            return float(f"{m.group(1)}.{m.group(2)}")
    if re.fullmatch(r"\d{1,3}(?:" + re.escape(thou) + r"\d{3})+", raw):
        return float(raw.replace(thou, ""))
    if re.fullmatch(r"\d+" + re.escape(dec) + r"\d{1,2}", raw):
        return float(raw.replace(dec, "."))
    if re.fullmatch(r"\d+", raw):
        return float(raw)
    return None


def parse_price(text: str, region: Region, category: str | None = None) -> tuple[dict | None, list[tuple[int, int]]]:
    """Return ({'min', 'max', 'currency', 'unit'}, [span]) or (None, [])."""
    t = text.lower()
    time_words = region.merged("time") or {}
    mults = region.currency.get("multipliers", {})
    mult = _alt(mults)
    sym = _alt(region.currency.get("symbols", []))
    rng = _alt(time_words.get("range", ["-"]) + ["–"])
    thou = re.escape(region.currency.get("thousands_separator", ","))
    pattern = re.compile(
        rf"(?P<sym>(?:{sym})\.?\s*)?(?<![\d.,])(?P<a>{NUM})\s*(?P<am>{mult})?(?![a-z\d])"
        rf"(?:\s*(?:{rng})\s*(?:(?:{sym})\.?\s*)?(?P<b>{NUM})\s*(?P<bm>{mult})?(?![a-z\d]))?"
    )
    for m in pattern.finditer(t):
        am, bm, a_raw, b_raw = m.group("am"), m.group("bm"), m.group("a"), m.group("b")
        thousands_fmt = bool(re.fullmatch(rf"\d{{1,3}}(?:{thou}\d{{3}})+", a_raw))
        if not (am or bm or m.group("sym") or thousands_fmt):
            continue  # a bare small number is more likely hours, rooms or people
        a = _to_number(a_raw, region, bool(am or bm))
        b = _to_number(b_raw, region, bool(am or bm)) if b_raw else None
        if a is None:
            continue
        lo = a * mults.get(am or bm or "", 1)
        hi = b * mults.get(bm or am or "", 1) if b is not None else None
        if hi is not None and hi < lo:
            lo, hi = hi, lo
        return {"min": lo, "max": hi, "currency": region.currency["code"],
                "unit": _price_unit(t[m.end():m.end() + 25], region, category)}, [m.span()]
    return None, []


def _price_unit(tail: str, region: Region, category: str | None) -> str:  # noqa: ARG001
    tokens = norm(tail).split()
    prefixes = {norm(w) for w in (region.merged("price_unit_prefix") or ["per"])}
    if tokens and tokens[0] in prefixes:
        tokens = tokens[1:]
    first, two = (tokens[0] if tokens else ""), " ".join(tokens[:2])
    for unit, unit_words in (region.merged("price_units") or {}).items():
        wn = {norm(w) for w in unit_words}
        if first in wn or two in wn:
            return unit
    return "other"  # no unit word: do not guess


def parse_hours(text: str, region: Region, skip_spans=()) -> dict | None:
    """'buka 7-21', 'jam 8 pagi sampai 8 malam', '07.00-21.00', '24 jam' -> {'open', 'close'}."""
    return parse_hours_detail(text, region, skip_spans)[0]


def parse_hours_detail(text: str, region: Region, skip_spans=()) -> tuple[dict | None, tuple[int, int] | None]:
    t = text.lower()
    for a, b in skip_spans:
        t = t[:a] + " " * (b - a) + t[b:]
    tw = region.merged("time") or {}
    for w in tw.get("all_day", []):
        if norm(w) and f" {norm(w)} " in f" {norm(t)} ":
            pos = t.find(w.lower())
            return {"open": "00:00", "close": "24:00"}, ((pos, pos + len(w)) if pos >= 0 else None)
    am, noon, pm = (tw.get(k, []) for k in ("am", "noon", "pm"))
    period, rng, mk = _alt(am + noon + pm), _alt(tw.get("range", ["-"]) + ["–"]), _alt(tw.get("markers", []))
    pattern = re.compile(
        rf"(?P<mk>\b(?:{mk})\s+)?(?<![\d.,])(?P<h1>\d{{1,2}})(?:[.:](?P<m1>\d{{2}}))?\s*(?P<p1>(?:{period})\b)?\s*"
        rf"(?:{rng})\s*(?:\b(?:{mk})\s+)?(?P<h2>\d{{1,2}})(?:[.:](?P<m2>\d{{2}}))?(?![\d])\s*(?P<p2>(?:{period})\b)?"
    )
    for m in pattern.finditer(t):
        if not (m.group("mk") or m.group("m1") or m.group("p1") or m.group("p2")):
            continue  # '3-4' alone could be rooms or people
        h1 = _apply_period(int(m.group("h1")), m.group("p1"), am, noon, pm)
        h2 = _apply_period(int(m.group("h2")), m.group("p2"), am, noon, pm)
        if h2 <= h1 and h2 < 12 and not m.group("p2"):
            h2 += 12  # 'buka 8-9' most likely means 08:00-21:00
        if h1 > 24 or h2 > 24 or h2 <= h1:
            continue
        return ({"open": f"{h1:02d}:{int(m.group('m1') or 0):02d}",
                 "close": f"{h2:02d}:{int(m.group('m2') or 0):02d}"}, m.span())
    return None, None


def _apply_period(hour: int, word: str | None, am: list, noon: list, pm: list) -> int:
    if not word:
        return hour
    if word in pm and hour < 12:
        return hour + 12
    if word in noon and hour < 11:
        return hour + 12
    if word in am and hour == 12:
        return 0
    return hour


def parse_capacity(text: str, region: Region) -> int | None:
    return parse_capacity_detail(text, region)[0]


def parse_capacity_detail(text: str, region: Region) -> tuple[int | None, tuple[int, int] | None]:
    alt = _alt(region.merged("capacity_units") or [])
    m = re.search(rf"(?<![\d.,])(\d{{1,3}})\s*(?:{alt})\b", text.lower())
    return (int(m.group(1)), m.span()) if m else (None, None)


def parse(text: str, region: Region) -> dict:
    """All rule-based fields found in one message, plus the words each one came from ('evidence')."""
    category, _, word = region.category_match(text)
    price, spans = parse_price(text, region, category)
    hours, hours_span = parse_hours_detail(text, region, spans)
    capacity, cap_span = parse_capacity_detail(text, region)
    place, gram, how = region.match_place_detail(text)
    piece = lambda span: text[span[0]:span[1]].strip() if span else None
    return {
        "category": category,
        "price": price,
        "hours": hours,
        "capacity": capacity,
        "place": place,
        "evidence": {"category": word, "price": piece(spans[0]) if spans else None, "hours": piece(hours_span),
                     "capacity": piece(cap_span), "place": gram, "place_match": how},
    }
