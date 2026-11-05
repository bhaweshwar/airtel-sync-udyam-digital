"""Mock GSTIN and Udyam registry lookups backed by the case CSVs. Phase 0 owns this file."""
from __future__ import annotations

from datetime import date

from .. import data
from ..contracts import GstinLookup, UdyamLookup
from . import gstin as gst


def _date(value: str) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def lookup_gstin(value: str) -> GstinLookup:
    g = gst.normalize(value)
    row = data.gstin_registry().get(g)
    out = GstinLookup(gstin=g, format_valid=gst.format_valid(g), checksum_valid=gst.checksum_valid(g), found=row is not None)
    if row:
        out.legal_name = row["legal_name"]
        out.trade_name = row["trade_name"]
        out.constitution = row["constitution"]
        out.address = row["principal_place_of_business"]
        out.state = row["state"]
        out.registration_date = _date(row["registration_date"])
        out.status = row["status"]  # type: ignore[assignment]
    return out


def lookup_udyam(value: str) -> UdyamLookup:
    u = gst.normalize_udyam(value)
    row = data.udyam_registry().get(u)
    out = UdyamLookup(udyam_number=u, format_valid=gst.udyam_format_valid(u), found=row is not None)
    if row:
        out.enterprise_name = row["enterprise_name"]
        out.enterprise_type = row["enterprise_type"]
        out.major_activity = row["major_activity"]
        out.nic_description = row["nic_description"]
        out.state = row["state"]
        out.city = row["city"]
        out.date_of_registration = _date(row["date_of_registration"])
    return out
