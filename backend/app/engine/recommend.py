"""Recommendation: segment base bundle from the activated leads + the right link + need-based add-ons."""
from __future__ import annotations

from collections import Counter
from functools import lru_cache
from typing import Optional

from .. import data
from ..contracts import BusinessProfile, Ineligible, Product, Segment
from . import rules, text

NEED_PRODUCTS: dict[str, str] = {
    "cctv": "P23", "payments_pos": "P19", "whatsapp": "P15", "email": "P16", "backup": "P09", "security": "P20",
    "wifi": "P22", "website": "P18", "cloud_backup": "P17", "telephony": "P12", "tollfree": "P13", "sms": "P14",
    "static_ip": "P11", "iot": "P24", "fleet": "P25", "sdwan": "P10",
}


def _ids(bundle: str) -> list[str]:
    return [part.split("x")[0] for part in bundle.split(";") if part]


@lru_cache(maxsize=1)
def segment_bundles() -> dict[Segment, list[str]]:
    """Each segment's most common activated bundle (as a product set). Ties go to the bundle whose products are
    most common across that segment's activations, so a sparse segment still gets a representative bundle."""
    df = data.leads()
    act = df[(df["outcome"] == "Activated") & (df["bundle_products"] != "")]
    out: dict[Segment, list[str]] = {}
    for seg, group in act.groupby("segment_code"):
        sets = [tuple(sorted(set(_ids(b)))) for b in group["bundle_products"]]
        freq = Counter(pid for s in sets for pid in s)
        counts = Counter(sets)
        best = max(counts, key=lambda s: (counts[s], sum(freq[p] for p in s), s))
        out[seg] = list(best)  # type: ignore[index]
    return out


def choose_link(profile: BusinessProfile, eligible: dict[str, Product]) -> Optional[str]:
    """Pick the one main internet link. Order of preference, falling back to whatever is eligible."""
    seg = profile.segment
    single = rules.sites(profile) == 1
    prefs: list[str] = []
    # A dedicated line for manufacturers (or anyone already on one). P05 itself needs 10+ staff and an active GSTIN.
    # The activated leads never put a leased line in a prof or multi bundle, so staff count alone doesn't trigger it.
    if seg == "mfg" or profile.current_internet == "leased_line":
        prefs.append("P05")
    if seg == "micro" and single and profile.current_internet in ("mobile_hotspot", "none"):
        prefs.append("P04")
    if seg in ("prof", "multi", "mfg"):
        prefs.append("P02")
    prefs += ["P01", "P02", "P04"]
    return next((pid for pid in prefs if pid in eligible), None)


class Selection:
    """Product ids in a recommended bundle, with their kind, plus extra ineligible rows found on the way."""

    def __init__(self) -> None:
        self.kinds: dict[str, str] = {}
        self.link: Optional[str] = None
        self.dependency_ineligible: list[Ineligible] = []


def select(profile: BusinessProfile) -> Selection:
    products = data.products_by_id()
    eligible = {pid: p for pid, p in products.items() if rules.ineligibility(p, profile) is None}
    sel = Selection()
    sel.link = choose_link(profile, eligible)
    if sel.link:
        sel.kinds[sel.link] = "core"

    base = segment_bundles().get(profile.segment or "micro", [])  # type: ignore[arg-type]
    wanted: list[tuple[str, str, bool]] = [(pid, "core", False) for pid in base if pid not in rules.LINKS]
    if not any(pid in rules.MOBILE_LINES for pid, _, _ in wanted):
        wanted.insert(0, ("P07", "core", False))
    wanted += [(NEED_PRODUCTS[n], "addon", True) for n in profile.needs if n in NEED_PRODUCTS]

    for pid, kind, asked in wanted:
        if pid in sel.kinds or pid not in eligible:
            continue
        p = eligible[pid]
        ids = set(sel.kinds)
        if not rules.dependency_met(p, ids):
            # AirFiber can't carry this add-on (e.g. Static IP): step up to fibre if we can.
            if sel.link == "P04" and "P01" in eligible and "P01" in p.requires_one_of:
                del sel.kinds["P04"]
                sel.kinds = {"P01": "core", **sel.kinds}
                sel.link = "P01"
            else:
                if asked:
                    sel.dependency_ineligible.append(Ineligible(
                        product_id=pid, name=p.name, reason_code="DEPENDENCY",
                        reason=text.dependency_ineligible(p, products.get(sel.link) if sel.link else None)))
                continue
        sel.kinds[pid] = kind
    return sel
