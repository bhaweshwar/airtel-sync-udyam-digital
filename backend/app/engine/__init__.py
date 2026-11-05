"""Rules engine public interface. WS1 owns this package and replaces the stub bodies below.

Other workstreams (advisor, orders) call only these two functions and must not import engine internals.
Contract:
- recommend(profile) returns a priced Quote with a default selection (items), toggle-able addons_available,
  and ineligible products with reasons. It never includes an ineligible product or an unmet dependency.
- price(profile, selected) re-prices exactly the selected products, auto-fixing dependencies with notices.
- Both return a Quote with a fresh quote_id; callers save it with store.save_quote().
"""
from __future__ import annotations

from ..contracts import BusinessProfile, Quote, SelectedItem
from ..store import new_id


def recommend(profile: BusinessProfile) -> Quote:
    """STUB (Phase 0): returns the fixture quote with the caller's profile. WS1 replaces this body."""
    from ..fixtures import quote
    return quote().model_copy(update={"profile": profile, "quote_id": new_id("Q")})


def price(profile: BusinessProfile, selected: list[SelectedItem]) -> Quote:
    """STUB (Phase 0): returns the fixture quote with the caller's profile. WS1 replaces this body."""
    from ..fixtures import quote
    return quote().model_copy(update={"profile": profile, "quote_id": new_id("Q")})
