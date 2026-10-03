"""Region profile: every place-specific word, rule input and reply text.

The rest of the server never hard-codes a language, currency or place name; it
asks a Region object. A new region is a new JSON file in regions/.

A region can accept several languages: some for hosts, some for travellers.
Every incoming message is matched against the words of all of them; replies use
the sender's language if the region has reply texts for it, otherwise the
fallback named in the profile (e.g. Batak Toba -> Indonesian).
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
# Scripts written without spaces between words (Chinese, Japanese, Korean): match words as substrings.
CJK_CLASS = r"぀-ヿ㐀-䶿一-鿿가-힯"
CJK = re.compile(rf"[{CJK_CLASS}]")
CJK_EDGE = re.compile(rf"(?<=[{CJK_CLASS}])(?=[^\s{CJK_CLASS}])|(?<=[^\s{CJK_CLASS}])(?=[{CJK_CLASS}])")


def norm(text: str) -> str:
    """Lowercase, strip accents, keep letters and digits of any script, turn the rest into single spaces."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = re.sub(r"[^\w?？]+|_", " ", text)
    text = CJK_EDGE.sub(" ", text)  # '搜索Tomok' -> '搜索 Tomok', so place names stay separate words
    return re.sub(r"\s+", " ", text).strip()


def term_pos(text_norm: str, word: str) -> int:
    """Position of a word or phrase in normalized text, -1 if absent. Substring match for CJK words."""
    w = norm(word)
    if not w:
        return -1
    if CJK.search(w):
        return text_norm.replace(" ", "").find(w.replace(" ", ""))
    pos = f" {text_norm} ".find(f" {w} ")
    return pos


def has_term(text_norm: str, word: str) -> bool:
    return term_pos(text_norm, word) != -1


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def _as_list(value) -> list[str]:
    return value if isinstance(value, list) else [value]


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
        langs = d["languages"]
        self.host_langs: list[str] = _as_list(langs["host"])
        self.traveller_langs: list[str] = _as_list(langs["traveller"])
        self.host_lang: str = langs.get("default_host", self.host_langs[0])
        self.traveller_lang: str = langs.get("default_traveller", self.traveller_langs[0])
        self.words: dict = d["words"]
        self.langs: list[str] = list(dict.fromkeys(self.host_langs + self.traveller_langs + list(self.words)))
        self.language_names: dict = d.get("language_names", {})
        self.fallback: dict = d.get("language_fallback", {})
        self.currency: dict = d["currency"]
        self.templates: dict = d["templates"]
        self.unit_labels: dict = d.get("unit_labels", {})
        self.llm_example: dict | None = d.get("llm_example")
        self.places = self._load_gazetteer(d.get("gazetteer", {}).get("source"))
        self._alias_index = self._build_alias_index()

    # ---- words -------------------------------------------------------------

    def lang_words(self, lang: str) -> dict:
        return self.words.get(lang, {})

    def all_langs(self) -> list[str]:
        return self.langs

    def merged(self, key: str):
        """One word list (or dict of word lists) for `key`, combining every language of the region."""
        out: dict | list | None = None
        for lang in self.langs:
            value = self.lang_words(lang).get(key)
            if value is None:
                continue
            if isinstance(value, dict):
                out = out if isinstance(out, dict) else {}
                for k, words in value.items():
                    out.setdefault(k, [])
                    out[k] += [w for w in words if w not in out[k]]
            else:
                out = out if isinstance(out, list) else []
                out += [w for w in value if w not in out]
        return out if out is not None else []

    def command(self, text: str) -> tuple[str | None, str | None, str]:
        """(command, language, rest of the message) if the message starts with a command word."""
        t = norm(text)
        found = None
        for lang in self.langs:
            for cmd, words in self.lang_words(lang).get("commands", {}).items():
                for w in words:
                    wn = w if w in ("?", "？") else norm(w)
                    if not wn:
                        continue
                    if CJK.search(wn):
                        hit = t.startswith(wn)
                        rest = t[len(wn):].strip() if hit else ""
                    else:
                        hit = t == wn or t.startswith(wn + " ")
                        rest = t[len(wn):].strip() if hit else ""
                    if hit and (found is None or len(wn) > len(found[3])):
                        found = (cmd, lang, rest, wn)
        return (found[0], found[1], found[2]) if found else (None, None, t)

    def _answer(self, text: str, key: str) -> bool:
        t = norm(text)
        return any(t == norm(w) for lang in self.langs for w in self.lang_words(lang).get("commands", {}).get(key, []))

    def is_yes(self, text: str) -> bool:
        return self._answer(text, "confirm_yes")

    def is_no(self, text: str) -> bool:
        return self._answer(text, "confirm_no")

    def category_match(self, text: str) -> tuple[str | None, str | None, str | None]:
        """(category, language, word) for the earliest category word in the text, in any language."""
        t = norm(text)
        best: tuple[int, int, str, str, str] | None = None
        for lang in self.langs:
            for cat, words in self.lang_words(lang).get("category", {}).items():
                for w in words:
                    pos = term_pos(t, w)
                    key = (pos, -len(w))
                    if pos != -1 and (best is None or key < best[:2]):
                        best = (pos, -len(w), cat, lang, w)
        return (best[2], best[3], best[4]) if best else (None, None, None)

    def category_of(self, text: str) -> tuple[str | None, str | None]:
        cat, lang, _ = self.category_match(text)
        return cat, lang

    def has_word(self, text: str, key: str) -> bool:
        t = norm(text)
        return any(has_term(t, w) for lang in self.langs for w in self.lang_words(lang).get(key, []))

    def is_question(self, text: str) -> bool:
        return "?" in text or "？" in text or self.has_word(text, "question")

    def detect_language(self, text: str, candidates: list[str] | None = None) -> tuple[str | None, dict]:
        """Language whose words appear most in the text: (language or None, score per language)."""
        t = norm(text)
        scores = {}
        for lang in candidates or self.langs:
            w = self.lang_words(lang)
            vocab = set(w.get("detect", [])) | set(w.get("question", [])) | set(w.get("cheap", [])) | set(w.get("now", []))
            for group in ("category", "commands", "price_units", "time"):
                for words in w.get(group, {}).values():
                    vocab |= {x for x in words if not x.isdigit() and x not in ("-", "?")}
            scores[lang] = sum(1 for word in vocab if has_term(t, word))
            if CJK.search(text) and any(CJK.search(x) for x in vocab):
                scores[lang] += 5
        if not scores or max(scores.values()) == 0:
            return None, scores
        order = {lang: i for i, lang in enumerate(candidates or self.langs)}
        return max(scores, key=lambda l: (scores[l], -order[l])), scores

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
        candidates = [c for c in candidates if len(c) >= 5 and not CJK.search(c)]
        for c in candidates:
            close = difflib.get_close_matches(c, self._alias_index.keys(), n=1, cutoff=0.85)
            if close:
                return self._alias_index[close[0]][0], c, "close spelling"
        return None, None, None

    def match_place(self, text: str | None) -> dict | None:
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
        labels = next((self.unit_labels[l] for l in self.lang_chain(lang) if l in self.unit_labels), {})
        return text + labels.get(price.get("unit") or "other", "")

    def lang_chain(self, lang: str | None) -> list[str]:
        """Languages to try for a reply: the sender's, its fallback, then the region defaults."""
        chain = [lang, self.fallback.get(lang or ""), self.host_lang, self.traveller_lang] + list(self.templates)
        return [l for l in dict.fromkeys(chain) if l]

    def reply_lang(self, lang: str | None, key: str = "welcome") -> str:
        return next(l for l in self.lang_chain(lang) if key in self.templates.get(l, {}))

    def template(self, key: str, lang: str | None = None, **values) -> str:
        for l in self.lang_chain(lang):
            text = self.templates.get(l, {}).get(key)
            if text:
                return text.format(**values)
        raise KeyError(key)

    def language_name(self, lang: str | None) -> str:
        return self.language_names.get(lang or "", lang or "unknown")
