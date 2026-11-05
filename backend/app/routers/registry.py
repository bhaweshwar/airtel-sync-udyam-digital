"""Mock GSTIN and Udyam lookup API (Phase 0, real implementation)."""
from __future__ import annotations

from fastapi import APIRouter

from ..common.registry import lookup_gstin, lookup_udyam
from ..contracts import GstinLookup, UdyamLookup

router = APIRouter(prefix="/api/registry", tags=["registry"])


@router.get("/gstin/{gstin}", response_model=GstinLookup)
def gstin(gstin: str) -> GstinLookup:
    return lookup_gstin(gstin)


@router.get("/udyam/{udyam}", response_model=UdyamLookup)
def udyam(udyam: str) -> UdyamLookup:
    return lookup_udyam(udyam)
