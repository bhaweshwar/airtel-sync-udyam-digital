"""Advisor API. WS2 owns this file. STUB (Phase 0): returns fixtures of the contract shape."""
from __future__ import annotations

from fastapi import APIRouter

from .. import fixtures
from ..contracts import AdvisorMessageRequest, AdvisorReply, HandoffRequest, HandoffResponse, LlmStatus

router = APIRouter(prefix="/api", tags=["advisor"])


@router.post("/advisor/message", response_model=AdvisorReply)
def message(req: AdvisorMessageRequest) -> AdvisorReply:
    reply = fixtures.advisor_reply_recommended() if "recommend" in req.text.lower() else fixtures.advisor_reply()
    return reply.model_copy(update={"session_id": req.session_id or reply.session_id})


@router.post("/advisor/handoff", response_model=HandoffResponse)
def handoff(req: HandoffRequest) -> HandoffResponse:
    return fixtures.handoff_response()


@router.get("/llm-status", response_model=LlmStatus)
def llm_status() -> LlmStatus:
    return fixtures.llm_status()
