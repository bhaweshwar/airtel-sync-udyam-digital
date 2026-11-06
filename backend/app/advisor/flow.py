"""Conversation flow: fill the required slots one question at a time, then hand the profile to the rules engine.

Products and prices come only from app.engine.recommend() / price(). This module decides what to ask next, which
items the owner explicitly removed or asked for, and when to hand off to a person.

Per-session state (the slot we asked about, misses in a row, an unknown place name, excluded/asked products) is
kept on the latest assistant message in the session's message history.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from .. import data, engine, store
from ..common import registry
from ..common.i18n_server import pick
from ..common.mask import mask_gstin, redact
from ..contracts import AdvisorMessageRequest, AdvisorReply, BusinessProfile, LineItem, Quote, SelectedItem
from . import extract as extractor
from . import templates as tpl
from .rules_parser import NEED_PRODUCTS, Extraction, detect_language, reply_language

# Slots the advisor stops asking after two tries, with the value it assumes (and says so).
ASSUMABLE = ("current_internet", "needs")
MAX_COUNT = 100000

REQUIRED = ["business_type", "city", "employees", "sites", "has_gstin", "current_internet", "needs"]
TIER_FOR_SIZE = {"metro": 1, "big_city": 2, "small_town": 3}
CHAIN_OF = {"restaurant": "Restaurant chain", "bakery": "Bakery chain", "pharmacy": "Pharmacy chain", "gym": "Gym chain"}
_GREETING = re.compile(r"\s*(?:hi+|hello|hey|namaste|namaskar|नमस्ते|नमस्कार|good (?:morning|afternoon|evening))[\s!.]*", re.I)


def missing_fields(p: BusinessProfile) -> list[str]:
    checks = {
        "business_type": p.business_type is not None and p.segment is not None,
        "city": p.city_tier is not None,
        "employees": p.employees is not None,
        "sites": p.sites is not None,
        "has_gstin": p.has_gstin is not None,
        "current_internet": p.current_internet is not None,
        "needs": len(p.needs) > 0,
    }
    return [k for k in REQUIRED if not checks[k]]


def _initial_state() -> dict[str, Any]:
    return {"pending": None, "misses": 0, "place": None, "excluded": [], "asked": [], "explained": [], "quote_id": None,
            "handoff_id": None, "repeats": 0, "target": None, "mode": "rules"}


def _state(messages: list[dict]) -> dict[str, Any]:
    for m in reversed(messages):
        if m.get("role") == "assistant" and isinstance(m.get("state"), dict):
            return {**_initial_state(), **m["state"]}
    return _initial_state()


def _public_profile(p: BusinessProfile) -> BusinessProfile:
    return p.model_copy(update={"gstin": mask_gstin(p.gstin) if p.gstin else None})


def _context(p: BusinessProfile) -> dict[str, Any]:
    """What the LLM may know: the business description only, never identifiers."""
    return p.model_dump(include={"business_type", "segment", "city", "employees", "sites", "has_gstin", "current_internet",
                                 "needs"}, exclude_none=True)


def _add_unique(items: list[str], *new: str) -> list[str]:
    return list(dict.fromkeys([*items, *new]))


# ---------------------------------------------------------------- apply one extraction to the profile

def _apply(p: BusinessProfile, ex: Extraction, state: dict[str, Any], lang: str, parts: list[str]) -> BusinessProfile:
    upd: dict[str, Any] = {}
    if ex.gstin:
        look = registry.lookup_gstin(ex.gstin)
        if not (look.format_valid and look.checksum_valid):
            parts.append(tpl.gstin_invalid(lang))
            ex.has_gstin = None
        elif look.found:
            upd.update(has_gstin=True, gstin=look.gstin, gstin_status=look.status)
            if look.state and not (ex.state or p.state):
                upd["state"] = look.state
            parts.append(tpl.gstin_found(look.status or "Active", look.trade_name or look.legal_name or "", lang))
        else:
            upd.update(has_gstin=True, gstin=look.gstin, gstin_status=None)
            parts.append(tpl.gstin_unknown(lang))
    if ex.business_type:
        upd.update(business_type=ex.business_type, segment=ex.segment)
    if ex.city:
        upd.update(city=ex.city, city_tier=ex.city_tier, state=ex.state)
        state["place"] = None
    elif ex.unknown_city and p.city_tier is None:
        state["place"] = ex.unknown_city
    if ex.city_size and state.get("place"):
        upd.update(city=state["place"], city_tier=TIER_FOR_SIZE[ex.city_size])
        state["place"] = None
    for name in ("employees", "sites"):
        value = getattr(ex, name)
        if value is not None:
            if 1 <= value <= MAX_COUNT:
                upd[name] = value
            else:
                ex.bad_number = True
    if ex.bad_number:
        parts.append(tpl.bad_number(lang))
    for name in ("current_internet", "budget_monthly_inr"):
        if getattr(ex, name) is not None:
            upd[name] = getattr(ex, name)
    if ex.has_gstin is not None and "has_gstin" not in upd:
        upd["has_gstin"] = ex.has_gstin
        if ex.has_gstin is False:
            upd.update(gstin=None, gstin_status=None)
    # A price question ("how much is WhatsApp API?") asks about a product; it doesn't add it to the plan.
    asking_price = ex.intent == "ask_price"
    needs_add = [] if asking_price else ex.needs_add
    products_asked = [] if asking_price else ex.products_asked
    needs = [n for n in p.needs if n not in ex.needs_remove]
    needs = _add_unique(needs, *needs_add)
    if products_asked and "internet" not in needs and any(pid in ("P01", "P02", "P03", "P04", "P05", "P06") for pid in products_asked):
        needs = _add_unique(needs, "internet")
    upd["needs"] = needs

    removed = [NEED_PRODUCTS[n] for n in ex.needs_remove if n in NEED_PRODUCTS] + ex.products_removed
    readded = [NEED_PRODUCTS[n] for n in needs_add if n in NEED_PRODUCTS] + products_asked
    state["excluded"] = [pid for pid in _add_unique(state["excluded"], *removed) if pid not in readded]
    state["asked"] = [pid for pid in _add_unique(state["asked"], *products_asked) if pid not in removed]

    p = p.model_copy(update=upd)
    # "A restaurant with 4 outlets" is a restaurant chain.
    base = (p.business_type or "").lower()
    if (p.sites or 0) >= 2 and base in CHAIN_OF:
        p = p.model_copy(update={"business_type": CHAIN_OF[base], "segment": "multi"})
    return BusinessProfile.model_validate(p.model_dump())


# ---------------------------------------------------------------- quote

def _build_quote(p: BusinessProfile, state: dict[str, Any], cheaper: bool) -> tuple[Quote, bool]:
    """engine.recommend, then engine.price if the owner removed or asked for specific products. Returns (quote, trimmed)."""
    q = engine.recommend(p)
    in_quote = {i.product_id for i in q.items}
    ineligible = {i.product_id for i in q.ineligible}
    trimmed = False
    if cheaper:
        # Cut extras, but never something the owner asked for (a stated need or a product they named).
        wanted = {NEED_PRODUCTS[n] for n in p.needs if n in NEED_PRODUCTS} | set(state["asked"])
        addon_ids = [i.product_id for i in q.items if i.kind == "addon" and i.product_id not in wanted]
        trimmed = bool(addon_ids)
        state["excluded"] = _add_unique(state["excluded"], *addon_ids)
    selected = [SelectedItem(product_id=i.product_id, quantity=i.quantity) for i in q.items if i.product_id not in state["excluded"]]
    addons = {a.product_id: a for a in q.addons_available}
    for pid in state["asked"]:
        if pid in in_quote or pid in ineligible or pid in state["excluded"]:
            continue
        selected.append(SelectedItem(product_id=pid, quantity=addons[pid].quantity if pid in addons else 1))
    if [s.product_id for s in selected] != [i.product_id for i in q.items]:
        q = engine.price(p, selected)
    store.save_quote(q)
    return q, trimmed


def _explain_unavailable(q: Quote, p: BusinessProfile, state: dict[str, Any], lang: str) -> list[str]:
    """Plain-words reasons for things the owner asked for that the engine says can't be sold."""
    wanted = _add_unique(state["asked"], *[NEED_PRODUCTS[n] for n in p.needs if n in NEED_PRODUCTS])
    out = []
    for item in q.ineligible:
        if item.product_id in wanted and item.product_id not in state["explained"]:
            out.append(pick(item.reason, lang))  # type: ignore[arg-type]
            state["explained"].append(item.product_id)
    return out


# ---------------------------------------------------------------- main entry

def _reply(sid: str, messages: list[dict], p: BusinessProfile, state: dict[str, Any], *, text: str, quick: list[str],
           stage: str, mode: str, quote: Optional[Quote] = None) -> AdvisorReply:
    # Owners writing Tamil, Telugu, Hinglish in English letters, etc. get the reply translated (numbers are guarded).
    if mode == "llm" and state.get("target") in extractor.LANGUAGE_NAMES:
        text = extractor.localize(text, state["target"]) or text
    messages.append({"role": "assistant", "text": text, "ts": store.now().isoformat(), "stage": stage, "mode": mode,
                     "quote_id": quote.quote_id if quote else None, "state": state})
    store.update_session(sid, profile=p, messages=messages, stage=stage, mode=mode)
    return AdvisorReply(session_id=sid, reply_text=text, quick_replies=quick, profile=_public_profile(p),
                        missing_fields=missing_fields(p), stage=stage, mode=mode,  # type: ignore[arg-type]
                        quote=_public_quote(quote) if quote else None)


def _public_quote(q: Quote) -> Quote:
    return q.model_copy(update={"profile": _public_profile(q.profile)})


def _product_name(pid: str) -> str:
    product = data.products_by_id().get(pid)
    return product.name if product else pid


def _price_answer(ex: Extraction, q: Optional[Quote], lang: str) -> str:
    """Answer "how much is X?" from the engine's numbers: the owner's own line if it's in (or can be added to) their
    plan, else the catalogue's standard monthly price. The LLM never writes these numbers."""
    pids = list(dict.fromkeys(ex.products_asked + [NEED_PRODUCTS[n] for n in ex.needs_add if n in NEED_PRODUCTS]))
    if not pids:
        return tpl.price_unknown(lang)
    lines = []
    for pid in pids[:3]:
        line: Optional[LineItem] = None
        in_plan = False
        if q:
            line = next((i for i in q.items if i.product_id == pid), None)
            in_plan = line is not None
            line = line or next((a for a in q.addons_available if a.product_id == pid), None)
            blocked = next((i for i in q.ineligible if i.product_id == pid), None)
            if line is None and blocked:
                product = data.products_by_id().get(pid)
                price = ""
                if product:
                    unit = round((product.price_min_inr + product.price_max_inr) / 2)
                    price = tpl.price_line(product.name, unit, unit, 1, product.setup_inr, True, lang).rstrip("।.") + ". "
                lines.append(price + pick(blocked.reason, lang) if price else f"{blocked.name}: {pick(blocked.reason, lang)}")  # type: ignore[arg-type]
                continue
        if line:
            lines.append(tpl.price_line(line.name, line.monthly_inr, line.unit_price_inr, line.quantity, line.setup_inr,
                                        in_plan, lang))
            continue
        product = data.products_by_id().get(pid)
        if product:
            unit = round((product.price_min_inr + product.price_max_inr) / 2)
            lines.append(tpl.price_line(product.name, unit, unit, 1, product.setup_inr, q is None, lang))
    return "\n".join(f"• {l}" for l in lines) if lines else tpl.price_unknown(lang)


def _change_summary(prev: Optional[Quote], q: Quote, ex: Extraction, lang: str) -> str:
    """Say exactly what changed between the previous and the new plan, or that nothing did."""
    if prev is None:
        return tpl.updated(lang)
    if (prev.profile.city or "") != (q.profile.city or "") and q.profile.city:
        return tpl.plan_moved(q.profile.city, lang)
    old = {i.product_id: i for i in prev.items}
    new = {i.product_id: i for i in q.items}
    added = [new[p].name for p in new if p not in old]
    removed = [old[p].name for p in old if p not in new]
    changed = [f"{new[p].name} ×{new[p].quantity}" for p in new if p in old and new[p].quantity != old[p].quantity]
    if added or removed or changed:
        return tpl.plan_changes(added, removed, changed, lang)
    asked_off = [*ex.products_removed, *[NEED_PRODUCTS[n] for n in ex.needs_remove if n in NEED_PRODUCTS]]
    absent = [_product_name(pid) for pid in dict.fromkeys(asked_off) if pid not in old]
    return tpl.not_in_plan(absent, lang) if absent else tpl.no_change(lang)


HANDOFF_REASONS = {
    "asked": "Owner asked to talk to a person",
    "tier3": "Area not served: {place}",
    "not_understood": "Advisor could not understand two messages in a row",
}


def _handoff(sid: str, messages: list[dict], p: BusinessProfile, state: dict[str, Any], code: str, lang: str, mode: str,
             prefix: list[str]) -> AdvisorReply:
    if not state.get("handoff_id"):
        state["handoff_id"] = store.save_handoff(sid, HANDOFF_REASONS[code].format(place=p.city or "unknown"))
    text = "\n\n".join([*prefix, tpl.handoff(code, lang)])
    return _reply(sid, messages, p, state, text=text, quick=[], stage="handoff", mode=mode)


def handle_message(req: AdvisorMessageRequest) -> AdvisorReply:
    session = store.get_session(req.session_id) if req.session_id else None
    if session is None:
        sid = store.create_session(BusinessProfile(language=req.language or "en"))
        session = store.get_session(sid)
    assert session is not None
    sid = session["id"]
    messages: list[dict] = session["messages"]
    p: BusinessProfile = session["profile"]
    state = _state(messages)
    first_turn = not messages

    text = req.text.strip()
    messages.append({"role": "user", "text": redact(text), "ts": store.now().isoformat()})
    ex, mode = extractor.extract(text, state["pending"], _context(p))

    detected = detect_language(text)
    if mode == "llm" and ex.language and len(text.split()) >= 3:
        detected = ex.language
    lang = detected or (req.language if first_turn else None) or p.language or "en"
    # Answer in the owner's own language and script. Templates cover English and Hindi (Devanagari); for anything
    # else the reply is written in English and translated by the LLM in _reply. Without an LLM, Hinglish gets Hindi.
    target = reply_language(text) or state.get("target")
    state["target"] = target
    if mode == "llm" and target in extractor.LANGUAGE_NAMES:
        lang = "en"
    p = p.model_copy(update={"language": lang})

    if ex.intent == "handoff":
        return _handoff(sid, messages, p, state, "asked", lang, mode, [])
    if session["stage"] == "handoff":
        return _reply(sid, messages, p, state, text=tpl.handoff_done(lang), quick=[], stage="handoff", mode=mode)

    parts: list[str] = []
    had_business = p.business_type is not None
    p = _apply(p, ex, state, lang, parts)

    understood = ex.understood() or bool(ex.gstin) or bool(_GREETING.fullmatch(text))
    state["misses"] = 0 if understood else state["misses"] + 1
    if state["misses"] >= 2:
        return _handoff(sid, messages, p, state, "not_understood", lang, mode, [])
    if p.city_tier == 3:
        return _handoff(sid, messages, p, state, "tier3", lang, mode, parts)

    if not understood:
        parts.insert(0, tpl.not_understood(lang))
    elif not had_business and p.business_type and p.city:
        parts.insert(0, tpl.greeting_ack(p, lang))
    if ex.unsupported:
        parts.append(tpl.unsupported(ex.unsupported, lang))

    missing = missing_fields(p)
    if state.get("place") and p.city_tier is None:
        state["pending"] = "city_size"
        parts.append(tpl.question("city_size", p, lang, place=state["place"]))
        return _reply(sid, messages, p, state, text="\n\n".join(parts), quick=tpl.quick_replies("city_size", p, lang),
                      stage="asking", mode=mode)
    # Asked twice and still unanswered: assume a sensible value, say so, and move on (no question loops).
    while missing and missing[0] in ASSUMABLE and missing[0] == state["pending"] and state.get("repeats", 0) >= 1:
        if missing[0] == "current_internet":
            mixed = (p.sites or 1) >= 2
            p = p.model_copy(update={"current_internet": "mixed" if mixed else "none"})
            parts.append(tpl.assumed_internet(lang, mixed))
        else:
            p = p.model_copy(update={"needs": ["internet"]})
        state["repeats"] = 0
        missing = missing_fields(p)
    if missing:
        slot = missing[0]
        state["repeats"] = state.get("repeats", 0) + 1 if slot == state["pending"] else 0
        state["pending"] = slot
        if ex.intent == "ask_price":
            parts.append(_price_answer(ex, None, lang))
        parts.append(tpl.question(slot, p, lang))
        return _reply(sid, messages, p, state, text="\n\n".join(parts), quick=tpl.quick_replies(slot, p, lang),
                      stage="asking", mode=mode)

    # Every slot is filled: the rules engine decides the products and prices.
    state["pending"] = None
    state["repeats"] = 0
    was_recommended = session["stage"] == "recommended"
    excluded_before = list(state["excluded"])
    prev = store.get_quote(state["quote_id"]) if state.get("quote_id") else None
    q, trimmed = _build_quote(p, state, cheaper=ex.cheaper)
    state["quote_id"] = q.quote_id

    if ex.intent == "ask_why" and was_recommended:
        lines = [f"• {i.name}: {pick(i.reason, lang)}" for i in q.items]  # type: ignore[arg-type]
        parts.append(tpl.why_header(lang) + "\n" + "\n".join(lines))
    elif ex.intent == "ask_price" and was_recommended:
        parts.append(_price_answer(ex, q, lang))
    elif ex.intent == "accept" and was_recommended:
        parts.append(tpl.accepted(lang))
    elif ex.cheaper and was_recommended:
        if trimmed or state["excluded"] != excluded_before:
            parts.append(tpl.cheaper(lang) + "\n" + _change_summary(prev, q, ex, lang))
        else:
            parts.append(tpl.kept_requested(lang))
    elif was_recommended:
        parts.append(_change_summary(prev, q, ex, lang))
    else:
        template = tpl.intro(p, lang)
        parts.append(tpl.safe_text(extractor.rephrase(template, lang) if mode == "llm" else None, template))

    unavailable = _explain_unavailable(q, p, state, lang)
    if unavailable:
        parts.append(tpl.product_unavailable_intro(lang) + "\n" + "\n".join(f"• {r}" for r in unavailable))
    if p.budget_monthly_inr and ex.budget_monthly_inr:
        parts.append(tpl.over_budget(lang) if q.monthly_total_inr > p.budget_monthly_inr else tpl.within_budget(lang))
    return _reply(sid, messages, p, state, text="\n\n".join(parts), quick=tpl.after_quote_quick_replies(lang),
                  stage="recommended", mode=mode, quote=q)


def handoff_request(session_id: str, reason: str, phone: str | None = None) -> str:
    """Explicit "Talk to a person" button. Works even if the session is unknown (the back office still sees the row).
    A call-back phone, if given, is stored encrypted on the hand-off."""
    session = store.get_session(session_id)
    clean = redact(reason)[:500] or HANDOFF_REASONS["asked"]
    if session is None:
        return store.save_handoff(session_id, clean, phone)
    messages = session["messages"]
    state = _state(messages)
    if not state.get("handoff_id"):
        state["handoff_id"] = store.save_handoff(session_id, clean, phone)
    elif phone:
        store.set_handoff_phone(state["handoff_id"], phone)
    p = session["profile"]
    messages.append({"role": "assistant", "text": tpl.handoff("asked", p.language), "ts": store.now().isoformat(),
                     "stage": "handoff", "mode": session["mode"], "state": state})
    store.update_session(session_id, messages=messages, stage="handoff")
    return state["handoff_id"]
