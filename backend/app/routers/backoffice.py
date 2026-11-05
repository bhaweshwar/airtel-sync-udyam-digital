"""Back-office API. WS5 owns this file. Every route needs the X-Backoffice-Key header."""
from __future__ import annotations

from collections import Counter
from typing import Optional

from fastapi import APIRouter, Depends, Query

from .. import data, store
from ..common.auth import require_backoffice_key
from ..common.i18n_server import lt
from ..common.mask import mask_phone
from ..contracts import (
    Channel, FunnelReport, FunnelStage, HandoffRow, KycReviewRow, LeadsPage, ModelCoefficient, ModelReport, OrderRow,
    Segment,
)
from .. import leads as lead_queue
from ..leads.model import get_model

router = APIRouter(prefix="/api/backoffice", tags=["backoffice"], dependencies=[Depends(require_backoffice_key)])

FUNNEL_STAGES = ["Lead", "Contacted", "Needs assessed", "Quote accepted", "KYC complete", "Activated"]
CAVEAT = lt("This ranks who is likely to activate, not who activates because we call.",
            "यह बताता है कि किसके चालू होने की संभावना ज़्यादा है, यह नहीं कि हमारे कॉल करने से कौन चालू होगा।")


@router.get("/leads", response_model=LeadsPage)
def leads(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
          channel: Optional[Channel] = None, segment: Optional[Segment] = None) -> LeadsPage:
    rows = lead_queue.query(channel, segment)
    return LeadsPage(total=len(rows), items=rows[offset:offset + limit])


@router.get("/handoffs", response_model=list[HandoffRow])
def handoffs() -> list[HandoffRow]:
    return [HandoffRow(**h) for h in store.list_handoffs()]


@router.get("/kyc-reviews", response_model=list[KycReviewRow])
def kyc_reviews() -> list[KycReviewRow]:
    return [KycReviewRow(order_id=k["order_id"], verdict=k["verdict"], created_at=k["created_at"],
                         failing_checks=[c for c in k["checks"] if c.status != "PASS"])
            for k in store.list_kyc_results(["MANUAL_REVIEW", "ACTION_REQUIRED"])]


@router.get("/orders", response_model=list[OrderRow])
def orders() -> list[OrderRow]:
    out = []
    for o in store.list_orders():
        quote = store.get_quote(o["quote_id"]) if o.get("quote_id") else None
        out.append(OrderRow(
            order_id=o["order_id"], status=o["status"], contact_name=o["contact_name"],
            # phone_masked is already masked by WS4; mask again so a raw number can never slip through.
            phone_masked=o["phone_masked"] if "•" in (o["phone_masked"] or "") else mask_phone(o["phone_masked"]),
            monthly_total_inr=quote.monthly_total_inr if quote else 0, created_at=o["created_at"],
        ))
    return out


@router.get("/model", response_model=ModelReport)
def model() -> ModelReport:
    m = get_model()
    return ModelReport(
        auc_time_split=round(m.auc_time_split, 3), top_decile_lift=round(m.top_decile_lift, 2),
        top20_capture=round(m.top20_capture, 3), train_rows=m.train_rows, test_rows=m.test_rows,
        coefficients=[ModelCoefficient(feature=f"{f}={v}", weight=round(w, 3)) for f, v, w in m.coefficients[:10]],
        caveat=CAVEAT,
    )


@router.get("/funnel", response_model=FunnelReport)
def funnel() -> FunnelReport:
    reached = data.leads()["stage_reached"].map(FUNNEL_STAGES.index)
    baseline = [FunnelStage(stage=s, count=int((reached >= i).sum())) for i, s in enumerate(FUNNEL_STAGES)]
    live = Counter(o["status"] for o in store.list_orders())
    return FunnelReport(baseline=baseline, live=dict(live))
