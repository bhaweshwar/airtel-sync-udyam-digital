"""Recommend + quote API. WS1 owns this file. STUB (Phase 0): delegates to the engine stubs."""
from __future__ import annotations

from fastapi import APIRouter

from .. import engine, store
from ..contracts import Quote, QuoteRequest, RecommendRequest

router = APIRouter(prefix="/api", tags=["quote"])


@router.post("/recommend", response_model=Quote)
def recommend(req: RecommendRequest) -> Quote:
    q = engine.recommend(req.profile)
    store.save_quote(q)
    return q


@router.post("/quote", response_model=Quote)
def quote(req: QuoteRequest) -> Quote:
    q = engine.price(req.profile, req.selected)
    store.save_quote(q)
    return q
