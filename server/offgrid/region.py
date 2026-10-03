"""Region profile: every place-specific word, rule input and reply text.

The rest of the server never hard-codes a language, currency or place name; it
asks a Region object. A new region is a new JSON file in regions/.
"""

from __future__ import annotations

import csv
import difflib
import json
import math
import pathlib
import re
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[2]
PLACE_RANK = {"town": 0, "village": 0, "suburb": 1, "hamlet": 2, "neighbourhood": 3}


def norm(text: str) -> str:
    """Lowercase, strip accents, turn everything except letters/digits into single spaces."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9?]+", " ", text).strip()


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


class Region:
    def __init__(self, path: str | pathlib.Path):
        self.path = pathlib.Path(path)
        if not self.path.is_absolute():
            self.path = ROOT / self.path
        self.data = json.loads(self.path.read_text())
        d = self.data
        self.id: str = d["id"]
        self.display_name: str = d["display_name"]
        self.timezone: str = d.get("timezone", "UTC")
        self.host_lang: str = d["languages"]["host"]
        self.traveller_lang: str = d["languages"]["traveller"]
        self.currency: dict = d["currency"]
        self.words: dict = d["words"]
        self.templates: dict = d["templates"]
        self.unit_labels: dict = d.get("unit_labels", {})
        self.llm_example: dict | None = d.get("llm_example")
        self.places = self._load_gazetteer(d.get("gazetteer", {}).get("source"))
        self._alias_index = self._build_alias_index()

    # ---- words -------------------------------------------------------------

    def lang_words(self, lang: str) -> dict:
        return self.words.get(lang, {})

    def all_langs(self) -> list[str]:
        return [self.host_lang] + [l for l in self.words if l != self.host_lang]

    def command(self, text: str) -> tuple[str | None, str | None, str]:
        """Return (command, language, rest) if the message starts with a command word."""
        t = norm(text)
        for lang in self.all_langs():
            for cmd, words in self.lang_words(lang).get("commands", {}).items():
                for w in sorted(words, key=len, reverse=True):
                    wn = norm(w) if w != "?" else "?"
                    if t == wn or t.startswith(wn + " "):
                        return cmd, lang, t[len(wn):].strip()
        return None, None, t

    def is_yes(self, text: str) -> bool:
        return norm(text) in {norm(w) for w in self.lang_words(self.host_lang)["commands"].get("confirm_yes", [])}

    def is_no(self, text: str) -> bool:
        return norm(text) in {norm(w) for w in self.lang_words(self.host_lang)["commands"].get("confirm_no", [])}

    def category_match(self, text: str) -> tuple[str | None, str | None, str | None]:
        """(category, language, word) for the first category word in the text."""
        t = " " + norm(text) + " "
        best: tuple[int, str, str, str] | None = None
        for lang in self.all_langs():
            for cat, words in self.lang_words(lang).get("category", {}).items():
                for w in words:
                    pos = t.find(" " + norm(w) + " ")
                    if pos != -1 and (best is None or pos < best[0]):
                        best = (pos, cat, lang, w)
        return (best[1], best[2], best[3]) if best else (None, None, None)

    def category_of(self, text: str) -> tuple[str | None, str | None]:
        """First category word found in the text, checking the start of the message first."""
        cat, lang, _ = self.category_match(text)
        return cat, lang

    def has_word(self, text: str, key: str) -> bool:
        t = " " + norm(text) + " "
        return any(" " + norm(w) + " " in t for lang in self.all_langs() for w in self.lang_words(lang).get(key, []))

    # ---- places ------------------------------------------------------------

    def _load_gazetteer(self, source: str | None) -> list[dict]:
        if not source:
            return []
        path = ROOT / source
        if not path.exists():
            return []
        places = []
        with open(path) as f:
            for row in csv.DictReader(f):
                if not row.get("name"):
                    continue
                places.append({"name": row["name"], "place": row.get("place", "village"),
                               "lat": float(row["lat"]), "lon": float(row["lon"])})
        return places

    def _build_alias_index(self) -> dict[str, list[dict]]:
        index: dict[str, list[dict]] = {}
        for p in self.places:
            for alias in {norm(p["name"]), norm(p["name"]).replace(" ", "")}:
                if len(alias) >= 3:
                    index.setdefault(alias, []).append(p)
        for alias in index:
            index[alias].sort(key=lambda p: PLACE_RANK.get(p["place"], 9))
        return index

    def match_place_detail(self, text: str | None) -> tuple[dict | None, str | None, str | None]:
        """(place, words matched, 'exact' or 'close spelling') for a gazetteer place named in the text."""
        if not text or not self.places:
            return None, None, None
        tokens = norm(text).split()
        for n in (4, 3, 2, 1):
            for i in range(len(tokens) - n + 1):
                gram = " ".join(tokens[i:i + n])
                for key in (gram, gram.replace(" ", "")):
                    if key in self._alias_index:
                        return self._alias_index[key][0], gram, "exact"
        candidates = [" ".join(tokens[i:i + n]) for n in (2, 1) for i in range(len(tokens) - n + 1)]
        candidates = [c for c in candidates if len(c) >= 5]
        for c in candidates:
            close = difflib.get_close_matches(c, self._alias_index.keys(), n=1, cutoff=0.85)
            if close:
                return self._alias_index[close[0]][0], c, "close spelling"
        return None, None, None

    def match_place(self, text: str | None) -> dict | None:
        """Find a gazetteer place named in free text. Exact n-gram match first, then close spelling."""
        return self.match_place_detail(text)[0]

    # ---- money and text ------------------------------------------------------

    def format_amount(self, amount: float) -> str:
        sep = self.currency.get("thousands_separator", ",")
        whole = f"{int(round(amount)):,}".replace(",", sep)
        return self.currency.get("display", "{amount}").format(amount=whole)

    def format_price(self, price: dict | None, lang: str) -> str:
        if not price:
            return ""
        text = self.format_amount(price["min"])
        if price.get("max"):
            text += "-" + self.format_amount(price["max"]).replace(self.currency.get("display", "").split("{")[0], "")
        return text + self.unit_labels.get(lang, {}).get(price.get("unit") or "other", "")

    def template(self, key: str, lang: str | None = None, **values) -> str:
        lang = lang or self.host_lang
        text = self.templates.get(lang, {}).get(key) or self.templates[self.host_lang][key]
        return text.format(**values)
