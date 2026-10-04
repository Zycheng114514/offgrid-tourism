"""Answer a traveller's question in their own words, from the listings only.

1. Fixed rules pick the candidate listings (the same search the app and SMS use).
2. The language model writes a short answer from those candidates only and
   names the listing IDs it used (through the LLM port; simulated in the demo).
3. Checks: the cited IDs must be among the candidates, every cited business
   must be named in the answer, and the answer may not name any business or
   place that is not cited or in the village list. If a check fails, or there
   is no model answer, the reply is built from the listing rows by a template.
"""

from __future__ import annotations

import json
import re
import string

from .llm import LLM
from .pack import public_listing
from .region import ROOT, Region, norm
from .search import find, relevance, result_line, searchable

PROMPT_PATH = ROOT / "models" / "prompts" / "answer_question.txt"
MAX_CANDIDATES = 5
MAX_ANSWER_CHARS = 400
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}, "listing_ids": {"type": "array", "items": {"type": "string"}}},
    "required": ["answer", "listing_ids"],
    "additionalProperties": False,
}
# Two or more capitalised words in a row look like a name ("Tuk Tuk Sunrise Cafe").
NAME_LIKE = re.compile(r"\b[A-Z][\w'’-]*(?:\s+[A-Z][\w'’-]*)+")


def _row(l: dict, region: Region, lang: str) -> str:
    offer = l.get("offer_en") if lang != l.get("language") and l.get("offer_en") else l.get("offer_original")
    hours = f"{l['hours']['open']}-{l['hours']['close']}" if l.get("hours") else "hours not given"
    phone = "phone shown" if l.get("contact", {}).get("publish_phone") else "no phone shown"
    where = l["village"] + (f" ({l['landmark']})" if l.get("landmark") else "")
    return " | ".join([l["id"], l["name"], l["category"], where, offer or "", region.format_price(l.get("price"), lang) or "price not given",
                       hours, phone])


def system_prompt(region: Region, lang: str, candidates: list[dict]) -> str:
    return string.Template(PROMPT_PATH.read_text()).substitute(
        region_name=region.display_name,
        language_name=region.language_name(lang),
        listings="\n".join(_row(l, region, lang) for l in candidates) or "(no listings match)",
    )


def check_answer(data: dict, candidates: list[dict], all_listings: list[dict], region: Region) -> list[dict]:
    """Return the failed checks (empty list = the answer can be used)."""
    fails = []
    answer = str(data.get("answer") or "").strip()
    ids = [i for i in data.get("listing_ids") or [] if isinstance(i, str)]
    by_id = {l["id"]: l for l in candidates}
    if not answer:
        fails.append({"check": "answer is not empty", "detail": "empty"})
    if len(answer) > MAX_ANSWER_CHARS:
        fails.append({"check": f"answer is at most {MAX_ANSWER_CHARS} characters", "detail": str(len(answer))})
    outside = [i for i in ids if i not in by_id]
    if outside:
        fails.append({"check": "cited listings are among the candidates", "detail": ", ".join(outside)})
    cited = [by_id[i] for i in ids if i in by_id]
    low = answer.lower()
    unnamed = [l["name"] for l in cited if l["name"].lower() not in low]
    if unnamed:
        fails.append({"check": "every cited business is named in the answer", "detail": ", ".join(unnamed)})
    cited_names = {l["name"].lower() for l in cited}
    uncited = [l["name"] for l in all_listings if l["name"].lower() in low and l["name"].lower() not in cited_names]
    if uncited:
        fails.append({"check": "no business is named without being cited", "detail": ", ".join(uncited)})
    places = {norm(p["name"]) for p in region.places}
    common = {w.lower() for w in region.merged("common_words")}

    def known(name: str) -> bool:
        n = name.lower()
        return any(n in c for c in cited_names) or norm(name) in places or n in region.display_name.lower()

    for name in NAME_LIKE.findall(answer):
        first, _, rest = name.partition(" ")
        if first.lower() in common:  # a sentence starter such as "Try" or "Coba" is not part of a name
            name = rest
        if " " not in name.strip() or known(name):
            continue
        fails.append({"check": "no names that are not in the listings or the village list", "detail": name})
    return fails


def answer(question: str, region: Region, listings: list[dict], llm: LLM | None, lang: str | None = None) -> dict:
    question = (question or "").strip()[:300]
    detected, _ = region.detect_language(question)
    lang = region.reply_lang(detected or lang or region.traveller_lang, "results_header")
    confirmed = [l for l in listings if l.get("status", {}).get("state") == "confirmed"]
    has_hits = searchable(question, region) or any(relevance(question, l) for l in confirmed)
    candidates = find(question, region, confirmed)[:MAX_CANDIDATES] if has_hits else []
    out = {"question": question, "lang": lang, "candidate_ids": [l["id"] for l in candidates],
           "method": "rules", "model": None, "model_output": None, "checks_failed": [], "note": None}

    if llm is not None and llm.enabled and candidates:
        res = llm.complete_json(system_prompt(region, lang, candidates), question, OUTPUT_SCHEMA, max_tokens=300)
        out["model"], out["model_output"] = llm.label, res.data
        if res.data:
            fails = check_answer(res.data, candidates, confirmed, region)
            out["checks_failed"] = fails
            if not fails:
                ids = [i for i in res.data["listing_ids"] if i in out["candidate_ids"]]
                cited = [l for l in candidates if l["id"] in ids]
                cited.sort(key=lambda l: ids.index(l["id"]))
                out.update(method="simulated" if llm.config.provider == "simulated" else "model",
                           answer=res.data["answer"].strip(), listing_ids=ids,
                           listings=[public_listing(l) for l in cited])
                return out
            out["note"] = "The model's answer failed a check, so the answer was built from the listings by rules."
        else:
            out["note"] = f"No model answer ({res.error}), so the answer was built from the listings by rules."
    elif not candidates:
        out["note"] = "Nothing in the listings matches the question."

    top = candidates[:3]
    if top:
        text = "\n".join([region.template("chat_rules_header", lang)] +
                         [result_line(i + 1, l, region, lang) for i, l in enumerate(top)])
    else:
        text = region.template("chat_nothing", lang)
    out.update(answer=text, listing_ids=[l["id"] for l in top], listings=[public_listing(l) for l in top])
    return out


def sms_text(result: dict) -> str:
    """The answer as an SMS: the text, then a phone number for each cited business that agreed to show one."""
    if result["method"] == "rules":
        return result["answer"]
    phones = [f"{l['name']}: {l['phone']}" for l in result.get("listings", []) if l.get("phone")]
    return "\n".join([result["answer"]] + phones)
