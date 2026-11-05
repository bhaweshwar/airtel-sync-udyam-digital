"""One LLM call per turn: read the owner's message into a partial profile + intent + language.

The model only reads; it never picks products or writes prices. Its JSON is validated field by field and anything
unknown is dropped. Identifiers are masked before the text leaves the server, and the rules parser always runs as
well, so GSTINs, product names and hand-off requests never depend on a model.
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from pydantic import BaseModel, ValidationError, field_validator

from ..common.mask import redact
from . import llm, rules_parser
from .rules_parser import INTENTS, INTERNET_CODES, NEED_CODES, Extraction

SYSTEM = f"""You read messages from small-business owners in India who want internet and business services.
They write in English, Hindi or Hinglish. Extract only what the message says; use null when it doesn't say.
Return one JSON object with exactly these keys:
- business_type: short English name of the business, e.g. "kirana store", "dental clinic", "restaurant chain", or null
- city: the city or town name in English, or null
- city_size: "metro", "big_city" or "small_town" if the owner describes the place that way, else null
- employees: integer number of people working there, or null
- sites: integer number of shops/branches/locations, or null
- has_gstin: true if they have GST registration, false if they say they don't, else null
- current_internet: one of {list(INTERNET_CODES)} or null
- needs_add: list of needs they want, from {list(NEED_CODES)}
- needs_remove: list of needs they no longer want, same values
- budget_monthly_inr: integer monthly budget in rupees if stated, else null
- wants_cheaper: true if they ask for a lower price
- intent: one of {list(INTENTS)} ("handoff" = wants to talk to a person; "accept" = happy with the plan;
  "change" = wants to change the plan; "ask_why" = asks why something was suggested)
- language: "hi" if they wrote in Hindi or Hinglish, "en" if English
Do not invent values. Do not recommend products. Output JSON only."""


class _LlmOut(BaseModel):
    """Lenient view of the model's JSON: every field optional, bad values become None/[] instead of errors."""
    business_type: Optional[str] = None
    city: Optional[str] = None
    city_size: Optional[str] = None
    employees: Optional[int] = None
    sites: Optional[int] = None
    has_gstin: Optional[bool] = None
    current_internet: Optional[str] = None
    needs_add: list[str] = []
    needs_remove: list[str] = []
    budget_monthly_inr: Optional[int] = None
    wants_cheaper: Optional[bool] = None
    intent: Optional[str] = None
    language: Optional[str] = None

    @field_validator("needs_add", "needs_remove", mode="before")
    @classmethod
    def _needs(cls, v: Any) -> list[str]:
        if not isinstance(v, list):
            return []
        return [x for x in v if isinstance(x, str) and x in NEED_CODES]

    @field_validator("current_internet", mode="before")
    @classmethod
    def _internet(cls, v: Any) -> Optional[str]:
        return v if v in INTERNET_CODES else None

    @field_validator("city_size", mode="before")
    @classmethod
    def _size(cls, v: Any) -> Optional[str]:
        return v if v in ("metro", "big_city", "small_town") else None

    @field_validator("intent", mode="before")
    @classmethod
    def _intent(cls, v: Any) -> Optional[str]:
        return v if v in INTENTS else None

    @field_validator("language", mode="before")
    @classmethod
    def _lang(cls, v: Any) -> Optional[str]:
        return v if v in ("en", "hi") else None

    @field_validator("employees", "sites", "budget_monthly_inr", mode="before")
    @classmethod
    def _positive_int(cls, v: Any) -> Optional[int]:
        try:
            n = int(v)
        except (TypeError, ValueError):
            return None
        return n if 0 < n < 100000 else None

    @field_validator("has_gstin", "wants_cheaper", mode="before")
    @classmethod
    def _bool(cls, v: Any) -> Optional[bool]:
        return v if isinstance(v, bool) else None

    @field_validator("business_type", "city", mode="before")
    @classmethod
    def _short_str(cls, v: Any) -> Optional[str]:
        if not isinstance(v, str):
            return None
        v = v.strip()
        return v if 0 < len(v) <= 60 else None


def _mask_for_llm(text: str) -> str:
    g = rules_parser.find_gstin(text)
    if g:
        text = re.sub(re.escape(g), "[GSTIN]", text, flags=re.I)
    return redact(text)


def from_llm(raw: dict[str, Any]) -> Optional[Extraction]:
    """Validate the model's JSON into an Extraction (pure, so tests can feed it canned JSON)."""
    try:
        o = _LlmOut.model_validate(raw)
    except ValidationError:
        return None
    ex = Extraction(
        city_size=o.city_size, employees=o.employees, sites=o.sites, has_gstin=o.has_gstin,
        current_internet=o.current_internet, needs_add=o.needs_add, needs_remove=o.needs_remove,
        budget_monthly_inr=o.budget_monthly_inr, cheaper=bool(o.wants_cheaper), intent=o.intent or "other",
        language=o.language,
    )
    if o.business_type:
        btype, seg = rules_parser.canonical_business(o.business_type)
        if btype:
            ex.business_type, ex.segment = btype, seg
    if o.city:
        city = rules_parser.lookup_city(o.city)
        if city:
            ex.city, ex.city_tier, ex.state = str(city["city"]), int(city["tier"]), str(city["state"])  # type: ignore[call-overload]
        elif o.city.lower() not in ("india", "unknown", "null"):
            ex.unknown_city = o.city
    return ex


def _merge(primary: Extraction, rules: Extraction) -> Extraction:
    """LLM first; rules fill the gaps. Deterministic-only signals (GSTIN, product names, hand-off) always come from rules."""
    for name in ("business_type", "segment", "city", "city_tier", "state", "unknown_city", "city_size", "employees",
                 "sites", "has_gstin", "current_internet", "budget_monthly_inr", "language"):
        if getattr(primary, name) is None and getattr(rules, name) is not None:
            setattr(primary, name, getattr(rules, name))
    if primary.city:
        primary.unknown_city = None
    primary.gstin = rules.gstin
    if rules.gstin:
        primary.has_gstin = True
    primary.needs_add = list(dict.fromkeys(primary.needs_add + [n for n in rules.needs_add if n not in primary.needs_remove]))
    primary.needs_remove = list(dict.fromkeys(primary.needs_remove + rules.needs_remove))
    primary.products_asked, primary.products_removed = rules.products_asked, rules.products_removed
    primary.cheaper = primary.cheaper or rules.cheaper
    if rules.intent == "handoff":
        primary.intent = "handoff"
    elif primary.intent == "other" and rules.intent != "other":
        primary.intent = rules.intent
    return primary


def extract(text: str, pending: Optional[str], context: dict[str, Any]) -> tuple[Extraction, str]:
    """Returns (extraction, mode). mode is "llm" when a model answered this turn, else "rules"."""
    rules = rules_parser.parse(text, pending)
    if not llm.any_configured():
        return rules, "rules"
    user = json.dumps({
        "question_we_asked": pending,
        "known_so_far": context,
        "owner_message": _mask_for_llm(text),
    }, ensure_ascii=False)
    raw, _provider = llm.complete_json(SYSTEM, user)
    if raw is None:
        return rules, "rules"
    ex = from_llm(raw)
    if ex is None:
        return rules, "rules"
    return _merge(ex, rules), "llm"


REPHRASE_SYSTEM = """You rewrite one short sentence from a telecom advisor to a small-business owner so it sounds
warm and natural in the requested language (English, or Hindi in Devanagari). Keep the meaning. Never add numbers,
digits, prices, rupee signs or product codes. Return JSON {"text": "..."}."""


def rephrase(template: str, language: str) -> Optional[str]:
    """Optional LLM polish of a template sentence. The caller still runs the number guard on the result."""
    if not llm.any_configured():
        return None
    raw, _ = llm.complete_json(REPHRASE_SYSTEM, json.dumps({"language": language, "sentence": template}, ensure_ascii=False))
    text = raw.get("text") if isinstance(raw, dict) else None
    return text.strip() if isinstance(text, str) and 0 < len(text.strip()) <= 400 else None
