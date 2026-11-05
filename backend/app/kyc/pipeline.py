"""KYC pipeline: photo bytes -> parsed document -> checks -> verdict.

Extracted details live only in this process's memory, keyed by order, for at most CACHE_TTL_S seconds. Photos and
extracted details are never written to disk; only the masked summary of a submitted result goes to the database.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path

from ..config import settings
from ..contracts import DocQuality, DocType, DocumentResult, KycResult
from .. import data, store
from .checks import DOC_TYPES, Outcome, document_checks, masked_fields, run_checks
from .ocr import read_image
from .parse import ParsedDoc, parse_document

CACHE_TTL_S = 30 * 60

_cache: dict[str, dict[DocType, tuple[ParsedDoc, float]]] = {}
_cache_lock = threading.Lock()


# ---------------------------------------------------------------- in-memory documents per order

def _purge(now: float) -> None:
    for order_id in list(_cache):
        docs = {t: v for t, v in _cache[order_id].items() if v[1] > now}
        if docs:
            _cache[order_id] = docs
        else:
            del _cache[order_id]


def remember(order_id: str, doc: ParsedDoc) -> None:
    now = time.monotonic()
    with _cache_lock:
        _purge(now)
        _cache.setdefault(order_id, {})[doc.doc_type] = (doc, now + CACHE_TTL_S)


def documents_for(order_id: str) -> dict[DocType, ParsedDoc]:
    now = time.monotonic()
    with _cache_lock:
        _purge(now)
        return {t: d for t, (d, _) in _cache.get(order_id, {}).items()}


def forget(order_id: str) -> None:
    with _cache_lock:
        _cache.pop(order_id, None)


# ---------------------------------------------------------------- pipeline steps

def process_bytes(doc_type: DocType, content: bytes) -> ParsedDoc:
    """OCR + parse one photo. Raises ocr.ImageDecodeError if the bytes are not an image."""
    page = read_image(content)
    return parse_document(doc_type, page.lines, page.width, blurry=page.blurry, blur_score=page.blur_score,
                          skew_deg=page.skew_deg)


def document_result(doc: ParsedDoc) -> DocumentResult:
    issues = [c for c in document_checks(doc, settings.today) if c.status != "PASS"]
    return DocumentResult(
        doc_type=doc.doc_type, detected_type=doc.detected_type, readable=doc.readable,
        quality=DocQuality(blur_score=doc.blur_score, blurry=doc.blurry, skew_deg=doc.skew_deg),
        fields=masked_fields(doc) if not doc.blurry else {}, issues=issues,
    )


def evaluate(docs: dict[DocType, ParsedDoc]) -> Outcome:
    return run_checks(docs, settings.today)


def sample_paths(applicant_id: str) -> dict[DocType, Path]:
    """The specimen files that exist for a sample applicant (K05 has no Udyam certificate)."""
    paths = {t: data.kyc_document_path(applicant_id, t) for t in DOC_TYPES}
    return {t: p for t, p in paths.items() if p.is_file()}


def process_sample(applicant_id: str) -> dict[DocType, ParsedDoc]:
    return {t: process_bytes(t, p.read_bytes()) for t, p in sample_paths(applicant_id).items()}


def submit(order_id: str, docs: dict[DocType, ParsedDoc]) -> KycResult:
    """Run the checks, store the masked result, and tell the orders module."""
    outcome = evaluate(docs)
    store.save_kyc_result(order_id, outcome.verdict, outcome.checks, outcome.fields_masked, outcome.gst_products_blocked)
    result = KycResult(order_id=order_id, verdict=outcome.verdict, checks=outcome.checks,
                       gst_products_blocked=outcome.gst_products_blocked, created_at=store.now())
    from ..orders import hooks  # WS4 owns on_kyc_result; imported late to avoid an import cycle with orders
    hooks.on_kyc_result(order_id, result)
    return result

