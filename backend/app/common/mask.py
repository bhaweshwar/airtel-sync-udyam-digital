"""Masking helpers for identifiers shown in responses, back office and logs. Phase 0 owns this file."""
from __future__ import annotations

import re

DOT = "•"

_GSTIN_IN_TEXT = re.compile(r"\b[0-9]{2}[A-Z0-9]{10}[1-9A-Z]Z[0-9A-Z]\b")
_UDYAM_IN_TEXT = re.compile(r"\bUDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}\b")
_PHONE_IN_TEXT = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)")


def mask_gstin(gstin: str | None) -> str:
    """27QHJXK0658U1ZL -> 27QH••••••••1ZL (state + 2 PAN letters, then the last 3)."""
    if not gstin:
        return ""
    g = gstin.strip().upper()
    return g if len(g) < 8 else g[:4] + DOT * (len(g) - 7) + g[-3:]


def mask_udyam(number: str | None) -> str:
    """UDYAM-KL-00-3078801 -> UDYAM-KL-00-•••8801."""
    if not number:
        return ""
    n = number.strip().upper()
    head, _, tail = n.rpartition("-")
    if not head or len(tail) < 4:
        return DOT * len(n)
    return f"{head}-{DOT * (len(tail) - 4)}{tail[-4:]}"


def mask_phone(phone: str | None) -> str:
    """9876543210 / +91 98765 43210 -> ••••••3210."""
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) < 4:
        return DOT * len(digits)
    digits = digits[-10:]
    return DOT * (len(digits) - 4) + digits[-4:]


def mask_id(value: str | None) -> str:
    """Generic ID number: keep the last 4 characters. SYN-ID-393148 -> •••••••••3148."""
    if not value:
        return ""
    v = value.strip()
    return v if len(v) <= 4 else DOT * (len(v) - 4) + v[-4:]


def redact(text: str | None) -> str:
    """Mask any GSTIN, Udyam number or Indian mobile number found inside free text (use before logging)."""
    if not text:
        return ""
    out = _UDYAM_IN_TEXT.sub(lambda m: mask_udyam(m.group(0)), text)
    out = _GSTIN_IN_TEXT.sub(lambda m: mask_gstin(m.group(0)), out)
    return _PHONE_IN_TEXT.sub(lambda m: mask_phone(m.group(0)), out)
