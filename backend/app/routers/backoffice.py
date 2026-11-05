"""Back-office API. WS5 owns this file. STUB (Phase 0): returns fixtures of the contract shape."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from .. import fixtures
from ..common.auth import require_backoffice_key
from ..contracts import Channel, FunnelReport, HandoffRow, KycReviewRow, LeadsPage, ModelReport, OrderRow, Segment

router = APIRouter(prefix="/api/backoffice", tags=["backoffice"], dependencies=[Depends(require_backoffice_key)])


@router.get("/leads", response_model=LeadsPage)
def leads(limit: int = 50, offset: int = 0, channel: Optional[Channel] = None, segment: Optional[Segment] = None) -> LeadsPage:
    return fixtures.leads_page()


@router.get("/handoffs", response_model=list[HandoffRow])
def handoffs() -> list[HandoffRow]:
    return fixtures.handoff_rows()


@router.get("/kyc-reviews", response_model=list[KycReviewRow])
def kyc_reviews() -> list[KycReviewRow]:
    return fixtures.kyc_review_rows()


@router.get("/orders", response_model=list[OrderRow])
def orders() -> list[OrderRow]:
    return fixtures.order_rows()


@router.get("/model", response_model=ModelReport)
def model() -> ModelReport:
    return fixtures.model_report()


@router.get("/funnel", response_model=FunnelReport)
def funnel() -> FunnelReport:
    return fixtures.funnel_report()
