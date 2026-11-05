"""Back office: lead score and queues (WS5)."""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from .. import data
from ..contracts import LeadRow
from .channels import FIXABLE_DROP_REASONS, suggested_channel
from .model import get_model


@lru_cache(maxsize=1)
def call_list() -> tuple[LeadRow, ...]:
    """Dropped leads with a fixable drop reason, highest score first."""
    m = get_model()
    df = data.leads()
    rows = []
    for r in df[df["drop_reason"].isin(FIXABLE_DROP_REASONS)].to_dict("records"):
        score = float(m.scores[r["lead_id"]])
        rows.append(LeadRow(
            lead_id=r["lead_id"], business_name=r["business_name"], segment=r["segment_code"], city=r["city"],
            city_tier=int(r["city_tier"]), source=r["lead_source"], preferred_language=r["preferred_language"],
            stage_reached=r["stage_reached"], drop_reason=r["drop_reason"] or None, score=round(score, 4),
            band=m.band(score), top_factors=m.top_factors[r["lead_id"]],
            suggested_channel=suggested_channel({**r, "segment": r["segment_code"]}),
        ))
    rows.sort(key=lambda x: (-x.score, x.lead_id))
    return tuple(rows)


def query(channel: Optional[str] = None, segment: Optional[str] = None) -> list[LeadRow]:
    return [r for r in call_list() if (not channel or r.suggested_channel == channel) and (not segment or r.segment == segment)]
