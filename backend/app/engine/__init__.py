"""Rules engine public interface. WS1 owns this package.

Other workstreams (advisor, orders) call only these two functions and must not import engine internals.
Contract:
- recommend(profile) returns a priced Quote with a default selection (items), toggle-able addons_available,
  and ineligible products with reasons. It never includes an ineligible product or an unmet dependency.
- price(profile, selected) re-prices exactly the selected products, auto-fixing dependencies with notices.
- Both return a Quote with a fresh quote_id; callers save it with store.save_quote().

Logic lives in rules.py (eligibility, quantities, prices), recommend.py (bundle choice), quote.py (pricing) and
text.py (EN/HI reasons and notices).
"""
from __future__ import annotations

from typing import Optional

from ..contracts import BusinessProfile, Quote, SelectedItem
from . import quote as _quote


def recommend(profile: BusinessProfile) -> Quote:
    return _quote.recommend(profile)


def price(profile: BusinessProfile, selected: list[SelectedItem], previous: Optional[Quote] = None) -> Quote:
    """`previous` (optional) is the quote being edited; with it, removing a prerequisite also removes its dependants
    instead of re-adding the prerequisite."""
    return _quote.price(profile, selected, previous)
