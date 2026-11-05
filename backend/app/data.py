"""Cached loaders for the case data pack in DATA_DIR. Phase 0 owns this file.

Everything is read once per process and kept in memory (the whole pack is ~8 MB).
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

import pandas as pd

from .config import settings
from .contracts import CurrentInternet, Product, Segment

SEGMENT_CODES: dict[str, Segment] = {
    "Micro retail & services": "micro",
    "Professional offices": "prof",
    "Small multi-site businesses": "multi",
    "Small manufacturers": "mfg",
}
SEGMENT_NAMES: dict[Segment, str] = {code: name for name, code in SEGMENT_CODES.items()}

CURRENT_INTERNET_CODES: dict[str, CurrentInternet] = {
    "None": "none",
    "Mobile hotspot": "mobile_hotspot",
    "Home broadband": "home_broadband",
    "Business broadband": "business_broadband",
    "Mixed per site": "mixed",
    "Leased line": "leased_line",
}

SAMPLE_APPLICANTS = [f"K{i:02d}" for i in range(1, 13)]


def _path(name: str) -> Path:
    return settings.data_dir / name


def _read_csv(name: str) -> list[dict[str, str]]:
    with _path(name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def catalogue() -> list[Product]:
    products = []
    for r in _read_csv("product_catalogue.csv"):
        products.append(Product(
            product_id=r["product_id"],
            category=r["category"],
            name=r["product_name"],
            description=r["description"],
            unit=r["unit"],
            price_min_inr=int(r["price_min_inr_per_month"]),
            price_max_inr=int(r["price_max_inr_per_month"]),
            setup_inr=int(r["one_time_setup_inr"]),
            min_contract_months=int(r["min_contract_months"]),
            city_tiers=[int(t) for t in r["available_city_tiers"].split(";") if t],
            min_employees=int(r["min_employees"]),
            min_sites=int(r["min_sites"]),
            requires_gstin=r["requires_gstin"].strip().upper() == "Y",
            requires_one_of=[p for p in r["requires_one_of"].split("|") if p],
            install_days=int(r["typical_install_days"]),
            target_segments=[s for s in r["target_segments"].split(";") if s],  # type: ignore[misc]
        ))
    return products


@lru_cache(maxsize=1)
def products_by_id() -> dict[str, Product]:
    return {p.product_id: p for p in catalogue()}


@lru_cache(maxsize=1)
def leads() -> pd.DataFrame:
    """smb_leads.csv as a DataFrame. Treat as read-only (it is shared across requests)."""
    df = pd.read_csv(_path("smb_leads.csv"), dtype=str, keep_default_na=False)
    for col in ("employee_count", "num_sites", "city_tier", "monthly_telecom_spend_inr", "customer_follow_up_calls"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    for col in ("days_lead_to_activation", "monthly_bundle_value_inr", "one_time_setup_inr",
                "contract_months", "nps_score", "acquisition_cost_inr"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["segment_code"] = df["segment"].map(SEGMENT_CODES)
    return df


@lru_cache(maxsize=1)
def gstin_registry() -> dict[str, dict[str, str]]:
    return {r["gstin"].strip().upper(): r for r in _read_csv("mock_gstin_registry.csv")}


@lru_cache(maxsize=1)
def udyam_registry() -> dict[str, dict[str, str]]:
    return {r["udyam_number"].strip().upper(): r for r in _read_csv("mock_udyam_registry.csv")}


@lru_cache(maxsize=1)
def city_tiers() -> dict[str, dict[str, object]]:
    """Lower-cased city name -> {city, tier, state}, from the cities that appear in smb_leads.csv."""
    out: dict[str, dict[str, object]] = {}
    for r in _read_csv("smb_leads.csv"):
        key = r["city"].strip().lower()
        if key and key not in out:
            out[key] = {"city": r["city"].strip(), "tier": int(r["city_tier"]), "state": r["state"].strip()}
    return out


@lru_cache(maxsize=1)
def business_type_segments() -> dict[str, Segment]:
    """Lower-cased business_type (e.g. 'dental clinic') -> segment code, the most common pairing in the leads."""
    counts: dict[str, dict[str, int]] = {}
    for r in _read_csv("smb_leads.csv"):
        bt = r["business_type"].strip().lower()
        seg = SEGMENT_CODES.get(r["segment"])
        if bt and seg:
            counts.setdefault(bt, {}).setdefault(seg, 0)
            counts[bt][seg] += 1
    return {bt: max(c, key=c.get) for bt, c in counts.items()}  # type: ignore[arg-type,misc]


def kyc_document_path(applicant_id: str, doc_type: str) -> Path:
    """Path of a specimen document, e.g. ('K03', 'gst_certificate'). The file may not exist (K05 has no Udyam)."""
    return settings.kyc_documents_dir / f"{applicant_id}_{doc_type}.png"


def warm() -> None:
    """Load everything once at startup so the first request is fast."""
    catalogue(); products_by_id(); leads(); gstin_registry(); udyam_registry(); city_tiers(); business_type_segments()
