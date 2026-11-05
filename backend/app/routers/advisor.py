"""Advisor API. WS2 owns this file.

POST /api/advisor/message runs one conversation turn (LLM extraction with the rules parser as fallback; products and
prices only from the rules engine). POST /api/advisor/handoff records a request for a person. GET /api/llm-status
reports each LLM provider.
"""
from __future__ import annotations

from fastapi import APIRouter

from ..advisor import flow, llm
from ..common.i18n_server import lt
from ..contracts import AdvisorMessageRequest, AdvisorReply, HandoffRequest, HandoffResponse, LlmStatus

router = APIRouter(prefix="/api", tags=["advisor"])


@router.post("/advisor/message", response_model=AdvisorReply)
def message(req: AdvisorMessageRequest) -> AdvisorReply:
    return flow.handle_message(req)


@router.post("/advisor/handoff", response_model=HandoffResponse)
def handoff(req: HandoffRequest) -> HandoffResponse:
    hid = flow.handoff_request(req.session_id, req.reason, req.phone)
    return HandoffResponse(handoff_id=hid, message=lt(
        "Thanks. A person from Accel will call you back within 2 working hours.",
        "धन्यवाद। Accel का एक व्यक्ति 2 कामकाजी घंटों में आपको वापस कॉल करेगा।"))


@router.get("/llm-status", response_model=LlmStatus)
def llm_status(probe: bool = False) -> LlmStatus:
    return llm.status(probe=probe)
