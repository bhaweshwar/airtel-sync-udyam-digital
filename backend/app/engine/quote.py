"""Turn a selection into a priced Quote, and re-price an owner's edited selection (price())."""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

from .. import data
from ..config import settings
from ..contracts import BusinessProfile, Ineligible, LineItem, LocalText, Product, Quote, SelectedItem
from ..store import new_id
from . import rules, text
from .recommend import choose_link, select

GST_RATE = 0.18
VALID_DAYS = 15


def line_item(p: Product, qty: int, profile: BusinessProfile, kind: str) -> LineItem:
    unit = rules.unit_price(p)
    return LineItem(
        product_id=p.product_id, name=p.name, category=p.category, unit=p.unit, quantity=qty,
        unit_price_inr=unit, monthly_inr=unit * qty, setup_inr=p.setup_inr * qty,
        contract_months=p.min_contract_months, install_days=p.install_days,
        reason=text.reason(p, qty, profile), kind=kind,  # type: ignore[arg-type]
    )


def _ineligible(profile: BusinessProfile) -> list[Ineligible]:
    return [x for p in data.catalogue() if (x := rules.ineligibility(p, profile)) is not None]


def _addons(profile: BusinessProfile, chosen: set[str]) -> list[LineItem]:
    """Eligible, relevant products the owner can switch on without anything else changing. Other links are
    alternatives, not add-ons, unless the owner removed their link: then the recommended one is offered back."""
    out = []
    eligible = {p.product_id: p for p in data.catalogue() if rules.ineligibility(p, profile) is None}
    offer_link = None if chosen & set(rules.LINKS) else choose_link(profile, eligible)
    for p in data.catalogue():
        pid = p.product_id
        if pid == offer_link:
            out.append(line_item(p, rules.default_quantity(p, profile), profile, "core"))
            continue
        if pid in chosen or pid in rules.LINKS:
            continue
        if pid in rules.MOBILE_LINES and chosen & set(rules.MOBILE_LINES):
            continue
        if not rules.relevant(p, profile) or rules.ineligibility(p, profile) is not None:
            continue
        if not rules.dependency_met(p, chosen):
            continue
        out.append(line_item(p, rules.default_quantity(p, profile), profile, "addon"))
    return out


def build(profile: BusinessProfile, items: list[LineItem], notices: list[LocalText],
          extra_ineligible: Optional[list[Ineligible]] = None) -> Quote:
    chosen = {i.product_id for i in items}
    monthly = sum(i.monthly_inr for i in items)
    with_gst = (monthly * 118 + 50) // 100
    notices = list(notices)
    if rules.gst_blocked(profile):
        notices.insert(0, text.gst_blocked_notice(profile))
    if profile.city_tier == 3:
        notices.insert(0, text.not_served_notice(profile))
    if profile.budget_monthly_inr and items and with_gst > profile.budget_monthly_inr:
        notices.append(text.budget_notice(with_gst, profile.budget_monthly_inr))
    ineligible = _ineligible(profile) + [x for x in (extra_ineligible or []) if x.product_id not in chosen]
    return Quote(
        quote_id=new_id("Q"), profile=profile, items=items, addons_available=_addons(profile, chosen),
        ineligible=ineligible, monthly_total_inr=monthly, one_time_total_inr=sum(i.setup_inr for i in items),
        gst_rate=GST_RATE, monthly_total_with_gst_inr=with_gst,
        contract_months=max((i.contract_months for i in items), default=0),
        notices=notices, valid_until=settings.today + timedelta(days=VALID_DAYS),
        gst_products_blocked=rules.gst_blocked(profile),
    )


def recommend(profile: BusinessProfile) -> Quote:
    products = data.products_by_id()
    sel = select(profile)
    items = [line_item(products[pid], rules.default_quantity(products[pid], profile), profile, kind)
             for pid, kind in sel.kinds.items()]
    return build(profile, items, [], sel.dependency_ineligible)


def price(profile: BusinessProfile, selected: list[SelectedItem], previous: Optional[Quote] = None) -> Quote:
    """Price exactly the selection. Ineligible products are dropped; a dependant whose prerequisite was just removed
    (relative to `previous`) is dropped too; any other unmet dependency gets the cheapest eligible prerequisite."""
    products = data.products_by_id()
    notices: list[LocalText] = []

    qty: dict[str, int] = {}
    for s in selected:
        pid = s.product_id.strip().upper()
        if pid not in products:
            notices.append(text.unknown_product(s.product_id))
            continue
        qty[pid] = s.quantity
    for pid in list(qty):
        why = rules.ineligibility(products[pid], profile)
        if why is not None:
            notices.append(text.removed_ineligible(products[pid], why.reason))
            del qty[pid]

    # Prerequisites the owner just removed take their dependants with them.
    removed = {i.product_id for i in previous.items} - set(qty) if previous else set()
    changed = True
    while changed:
        changed = False
        for pid in list(qty):
            p = products[pid]
            if rules.dependency_met(p, set(qty)):
                continue
            gone = [products[r] for r in p.requires_one_of if r in removed]
            if gone:
                del qty[pid]
                removed.add(pid)
                notices.append(text.removed_dependant(p, gone))
                changed = True

    # Anything still unmet: add the prerequisite that satisfies the most dependants, cheapest first.
    while True:
        unmet = [products[pid] for pid in qty if not rules.dependency_met(products[pid], set(qty))]
        if not unmet:
            break
        candidates = {r for p in unmet for r in p.requires_one_of
                      if r in products and rules.ineligibility(products[r], profile) is None}
        if not candidates:
            for p in unmet:
                del qty[p.product_id]
                notices.append(text.removed_ineligible(p, text.dependency_ineligible(p, None)))
            continue

        def score(r: str) -> tuple[int, int]:
            served = sum(1 for p in unmet if r in p.requires_one_of)
            return (-served, rules.unit_price(products[r]) * rules.default_quantity(products[r], profile))

        add = min(sorted(candidates), key=score)
        p_add = products[add]
        qty[add] = rules.default_quantity(p_add, profile)
        notices.append(text.added_prerequisite(p_add, [p for p in unmet if add in p.requires_one_of]))

    prev_kinds = {i.product_id: i.kind for i in previous.items} if previous else {}
    core = {pid for pid, k in select(profile).kinds.items() if k == "core"}
    items = []
    for pid, q in qty.items():
        kind = prev_kinds.get(pid) or ("core" if pid in core or pid in rules.LINKS else "addon")
        items.append(line_item(products[pid], q, profile, kind))
    # Links first, then catalogue order, so the quote reads the same however it was edited.
    items.sort(key=lambda i: (i.product_id not in rules.LINKS, i.product_id))
    return build(profile, items, notices)
