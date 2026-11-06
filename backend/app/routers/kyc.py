"""Smart KYC API. WS3 owns this file.

Consent comes first: uploads, submit and the demo samples return 403 CONSENT_REQUIRED without an active consent.
Photos are read in memory and never written to disk; responses carry masked identifiers only.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from .. import store
from ..config import settings
from ..contracts import ConsentNotice, ConsentRecord, ConsentRequest, DocType, DocumentResult, KycResult
from ..data import SAMPLE_APPLICANTS
from ..kyc import consent, pipeline
from ..kyc.ocr import ImageDecodeError

router = APIRouter(prefix="/api/kyc", tags=["kyc"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
_ORDER_ID_RE = re.compile(r"^[A-Za-z0-9-]{1,40}$")


def _check_order_id(order_id: str) -> None:
    if not _ORDER_ID_RE.match(order_id):
        raise HTTPException(404, detail={"code": "ORDER_NOT_FOUND", "message": "We couldn't find that order."})


def _require_consent(order_id: str) -> None:
    _check_order_id(order_id)
    if store.get_active_consent(order_id) is None:
        raise HTTPException(403, detail={"code": "CONSENT_REQUIRED",
                                         "message": "Please read the notice and give consent before we check your documents."})
    _require_open_kyc(order_id)


# KYC can run (and re-run) only while the order is still at the KYC stage. Once it is verified, with our team for
# review, rejected or further along, a new check could not change the order, so the screen and the tracker would
# disagree; refuse it instead.
KYC_OPEN_STATUSES = frozenset({"QUOTE_ACCEPTED", "KYC_PENDING", "KYC_ACTION_REQUIRED"})
_CLOSED_MESSAGE = {
    "KYC_REVIEW": "Your documents are already with our team for a quick check. Track your order for updates.",
    "REJECTED": "This order could not be verified, so documents can't be checked again. Please call support.",
}


def _require_open_kyc(order_id: str) -> None:
    row = store.get_order(order_id)
    if row is None or row["status"] in KYC_OPEN_STATUSES:
        return
    status = row["status"]
    message = _CLOSED_MESSAGE.get(status, "Your documents are already verified. Track your order for the next step.")
    raise HTTPException(409, detail={"code": "KYC_CLOSED", "message": message, "status": status})


@router.get("/notice", response_model=ConsentNotice)
def notice() -> ConsentNotice:
    return consent.notice()


@router.post("/{order_id}/consent", response_model=ConsentRecord)
def give_consent(order_id: str, req: ConsentRequest) -> ConsentRecord:
    _check_order_id(order_id)
    if req.version != consent.NOTICE_VERSION:
        raise HTTPException(409, detail={"code": "NOTICE_VERSION",
                                         "message": "The notice has changed. Please read the latest version."})
    accepted = list(dict.fromkeys(req.purposes_accepted))
    known = {p.id for p in consent.notice().purposes}
    if any(p not in known for p in accepted):
        raise HTTPException(422, detail={"code": "UNKNOWN_PURPOSE", "message": "Unknown consent purpose."})
    if consent.REQUIRED_PURPOSE not in accepted:
        raise HTTPException(422, detail={"code": "REQUIRED_PURPOSE",
                                         "message": "We need your consent to check the documents for this order."})
    store.withdraw_consent(order_id)  # a new consent replaces any earlier one
    return store.save_consent(order_id, req.version, accepted)


@router.delete("/{order_id}/consent", status_code=204)
def withdraw_consent(order_id: str) -> None:
    _check_order_id(order_id)
    store.withdraw_consent(order_id)
    store.delete_kyc_result(order_id)
    pipeline.forget(order_id)
    return None


@router.post("/{order_id}/documents", response_model=DocumentResult)
async def upload_document(order_id: str, doc_type: DocType = Form(...), file: UploadFile = File(...)) -> DocumentResult:
    _require_consent(order_id)
    content = await file.read(MAX_UPLOAD_BYTES + 1)  # read in memory only; never written to disk
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, detail={"code": "FILE_TOO_LARGE", "message": "The photo is larger than 10 MB."})
    try:
        doc = await run_in_threadpool(pipeline.process_bytes, doc_type, content)
    except ImageDecodeError:
        raise HTTPException(422, detail={"code": "NOT_AN_IMAGE", "message": "That file isn't a photo we can open."})
    finally:
        del content
    pipeline.remember(order_id, doc)
    return pipeline.document_result(doc)


@router.post("/{order_id}/submit", response_model=KycResult)
def submit(order_id: str) -> KycResult:
    _require_consent(order_id)
    return pipeline.submit(order_id, pipeline.documents_for(order_id))


@router.post("/{order_id}/sample/{applicant_id}", response_model=KycResult)
def sample(order_id: str, applicant_id: str) -> KycResult:
    if not settings.demo_mode:
        raise HTTPException(404, detail={"code": "DEMO_ONLY", "message": "Sample applicants are only available in demo mode."})
    applicant = applicant_id.upper()
    if applicant not in SAMPLE_APPLICANTS:
        raise HTTPException(404, detail={"code": "UNKNOWN_APPLICANT", "message": "Sample applicants are K01 to K12."})
    _require_consent(order_id)
    docs = pipeline.process_sample(applicant)
    pipeline.forget(order_id)  # a sample replaces whatever was uploaded before; retakes then replace single slots
    for doc in docs.values():
        pipeline.remember(order_id, doc)
    return pipeline.submit(order_id, docs)
