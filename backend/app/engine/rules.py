"""Eligibility, default quantities and unit prices. Pure functions over the catalogue and a profile."""
from __future__ import annotations

from math import ceil
from typing import Optional

from ..common.i18n_server import lt
from ..contracts import BusinessProfile, Ineligible, Product

# Main internet links. A bundle carries one of them; the others are alternatives, not add-ons.
LINKS = ("P01", "P02", "P03", "P04", "P05", "P06")
MOBILE_LINES = ("P07", "P08")

GST_BLOCKED = ("Cancelled", "Suspended")
_STATUS_HI = {"Cancelled": "रद्द", "Suspended": "निलंबित"}


def tier(profile: BusinessProfile) -> int:
    """Unknown tier counts as 2: never offer a tier-1-only product on a guess."""
    return profile.city_tier or 2


def employees(profile: BusinessProfile) -> int:
    return profile.employees or 1


def sites(profile: BusinessProfile) -> int:
    return profile.sites or 1


def gst_blocked(profile: BusinessProfile) -> bool:
    return profile.gstin_status in GST_BLOCKED


def gst_ok(profile: BusinessProfile) -> bool:
    has = profile.has_gstin or profile.gstin_status == "Active"
    return bool(has) and not gst_blocked(profile)


def unit_price(p: Product) -> int:
    """Midpoint of the price range, rounded half up to the rupee."""
    return (p.price_min_inr + p.price_max_inr + 1) // 2


def default_quantity(p: Product, profile: BusinessProfile) -> int:
    emp, n_sites = employees(profile), sites(profile)
    unit = p.unit
    if unit == "per site" or unit == "per counter":
        return n_sites
    if unit == "per user":
        return emp
    if unit == "per line":
        return min(ceil(emp / 2), 6)
    if unit == "per camera":
        return 2 * n_sites
    if unit == "per device":
        return emp if p.product_id == "P20" else 5
    if unit == "per channel":
        return max(2, ceil(emp / 5))
    return 1  # per IP / number / pack / account / vehicle


def _city(profile: BusinessProfile) -> tuple[str, str]:
    return (profile.city or "your city", profile.city or "आपका शहर")


def ineligibility(p: Product, profile: BusinessProfile) -> Optional[Ineligible]:
    """Why this product can't be sold to this profile (static rules only), or None if it can."""
    t = tier(profile)
    if t not in p.city_tiers:
        city_en, city_hi = _city(profile)
        if t == 3:
            text = lt(f"{p.name} isn't available in {city_en} yet.", f"{p.name} अभी {city_hi} में उपलब्ध नहीं है।")
        elif p.city_tiers == [1]:
            text = lt(f"{p.name} is only sold in tier 1 cities. {city_en} is tier {t}.",
                      f"{p.name} सिर्फ़ टियर 1 शहरों में मिलता है। {city_hi} टियर {t} है।")
        else:
            tiers = " and ".join(str(x) for x in p.city_tiers)
            tiers_hi = " और ".join(str(x) for x in p.city_tiers)
            text = lt(f"{p.name} is only sold in tier {tiers} cities. {city_en} is tier {t}.",
                      f"{p.name} सिर्फ़ टियर {tiers_hi} शहरों में मिलता है। {city_hi} टियर {t} है।")
        return Ineligible(product_id=p.product_id, name=p.name, reason_code="TIER", reason=text)
    emp = employees(profile)
    if emp < p.min_employees:
        return Ineligible(product_id=p.product_id, name=p.name, reason_code="EMPLOYEES", reason=lt(
            f"{p.name} is for businesses with {p.min_employees} or more staff. You have {emp}.",
            f"{p.name} {p.min_employees} या ज़्यादा कर्मचारियों वाले व्यवसायों के लिए है। आपके यहाँ {emp} हैं।"))
    n_sites = sites(profile)
    if n_sites < p.min_sites:
        have = f"You have {n_sites} site." if n_sites == 1 else f"You have {n_sites} sites."
        return Ineligible(product_id=p.product_id, name=p.name, reason_code="SITES", reason=lt(
            f"{p.name} is for businesses with {p.min_sites} or more sites. {have}",
            f"{p.name} {p.min_sites} या ज़्यादा जगहों वाले व्यवसायों के लिए है। आपकी {n_sites} जगह है।"))
    if p.requires_gstin and not gst_ok(profile):
        if gst_blocked(profile):
            status = profile.gstin_status or ""
            text = lt(f"{p.name} needs an active GSTIN. Yours is {status.lower()}, so we can't sell it until it is active again.",
                      f"{p.name} के लिए सक्रिय GSTIN ज़रूरी है। आपका GSTIN {_STATUS_HI.get(status, status)} है, "
                      f"इसलिए दोबारा सक्रिय होने तक हम इसे नहीं बेच सकते।")
        else:
            text = lt(f"{p.name} needs an active GSTIN, and you don't have one yet.",
                      f"{p.name} के लिए सक्रिय GSTIN ज़रूरी है, और अभी आपके पास GSTIN नहीं है।")
        return Ineligible(product_id=p.product_id, name=p.name, reason_code="GSTIN", reason=text)
    return None


def dependency_met(p: Product, ids: set[str]) -> bool:
    return not p.requires_one_of or any(r in ids for r in p.requires_one_of)


def relevant(p: Product, profile: BusinessProfile) -> bool:
    return profile.segment is None or profile.segment in p.target_segments
