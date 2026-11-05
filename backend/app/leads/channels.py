"""Who should follow up a dropped lead, and which drops are worth following up (WS5).

This is our answer to "what role for the field force and partners": field sales for the big, complex
accounts; partners for tier-2 towns, regional languages and micro shops; inside sales for the rest;
and an SMS/WhatsApp advisor link when the owner simply couldn't be reached or had no time.
"""
from __future__ import annotations

from typing import Mapping

from .. import data

# Drops the digital journey or a simple contact can fix (time, scheduling, quote clarity, paperwork, reachability).
FIXABLE_DROP_REASONS = frozenset({
    "Owner had no time for a visit",
    "Visit not scheduled by sales",
    "Quote too complex to understand",
    "Quote took too long to arrive",
    "Missing GST or Udyam document",
    "Found paperwork too long",
    "Document details did not match",
    "Unreachable after 3 attempts",
    "Wrong or invalid number",
})
SELF_SERVE_REASONS = frozenset({"Unreachable after 3 attempts", "Wrong or invalid number", "Owner had no time for a visit"})
FIELD_BUNDLE_INR = 10_000


def expected_bundle_inr(products_of_interest: str) -> int:
    """Lower-bound monthly value of what the owner said they were interested in at intake (e.g. 'P02;P12')."""
    catalogue = data.products_by_id()
    return sum(catalogue[p].price_min_inr for p in products_of_interest.split(";") if p in catalogue)


def suggested_channel(lead: Mapping[str, object]) -> str:
    """Rules checked in order. `lead` needs drop_reason, segment (code), city_tier, preferred_language, products_of_interest."""
    if lead.get("drop_reason") in SELF_SERVE_REASONS:
        return "SELF_SERVE_LINK"
    segment = lead.get("segment")
    if segment in ("multi", "mfg") or expected_bundle_inr(str(lead.get("products_of_interest") or "")) >= FIELD_BUNDLE_INR:
        return "FIELD"
    if int(lead.get("city_tier") or 0) == 2 or lead.get("preferred_language") not in ("English", "Hindi") or segment == "micro":
        return "PARTNER"
    return "INSIDE_SALES"
