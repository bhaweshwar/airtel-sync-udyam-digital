"""Smart KYC API. WS3 owns this file. STUB (Phase 0): returns fixtures of the contract shape."""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from .. import fixtures
from ..contracts import ConsentNotice, ConsentRecord, ConsentRequest, DocType, DocumentResult, KycResult
from ..data import SAMPLE_APPLICANTS

router = APIRouter(prefix="/api/kyc", tags=["kyc"])


@router.get("/notice", response_model=ConsentNotice)
def notice() -> ConsentNotice:
    return fixtures.consent_notice()


@router.post("/{order_id}/consent", response_model=ConsentRecord)
def give_consent(order_id: str, req: ConsentRequest) -> ConsentRecord:
    return fixtures.consent_record().model_copy(update={"order_id": order_id, "purposes_accepted": req.purposes_accepted})


@router.delete("/{order_id}/consent", status_code=204)
def withdraw_consent(order_id: str) -> None:
    return None


@router.post("/{order_id}/documents", response_model=DocumentResult)
async def upload_document(order_id: str, doc_type: DocType = Form(...), file: UploadFile = File(...)) -> DocumentResult:
    await file.read()  # read in memory only; never written to disk
    return fixtures.document_result().model_copy(update={"doc_type": doc_type})


@router.post("/{order_id}/submit", response_model=KycResult)
def submit(order_id: str) -> KycResult:
    return fixtures.kyc_result().model_copy(update={"order_id": order_id})


@router.post("/{order_id}/sample/{applicant_id}", response_model=KycResult)
def sample(order_id: str, applicant_id: str) -> KycResult:
    if applicant_id.upper() not in SAMPLE_APPLICANTS:
        raise HTTPException(404, detail={"code": "UNKNOWN_APPLICANT", "message": "Sample applicants are K01 to K12."})
    return fixtures.kyc_result().model_copy(update={"order_id": order_id})
