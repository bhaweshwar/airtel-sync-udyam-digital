"""Order status machine (WS4). Only the transitions listed in docs/CONTRACTS.md are allowed."""
from __future__ import annotations

from ..contracts import KycVerdict, OrderStatus

TRANSITIONS: dict[str, frozenset[str]] = {
    "QUOTE_ACCEPTED": frozenset({"KYC_PENDING"}),
    "KYC_PENDING": frozenset({"KYC_ACTION_REQUIRED", "KYC_REVIEW", "KYC_VERIFIED", "REJECTED"}),
    # A retake re-runs KYC, so ACTION_REQUIRED can go back to PENDING or straight to a new verdict.
    "KYC_ACTION_REQUIRED": frozenset({"KYC_PENDING", "KYC_VERIFIED", "KYC_REVIEW", "REJECTED"}),
    "KYC_REVIEW": frozenset({"KYC_VERIFIED", "REJECTED"}),
    "KYC_VERIFIED": frozenset({"INSTALL_SCHEDULED"}),
    "INSTALL_SCHEDULED": frozenset({"INSTALLING"}),
    "INSTALLING": frozenset({"ACTIVE"}),
    "ACTIVE": frozenset(),
    "REJECTED": frozenset(),
}

VERDICT_STATUS: dict[str, OrderStatus] = {
    "VERIFIED": "KYC_VERIFIED",
    "ACTION_REQUIRED": "KYC_ACTION_REQUIRED",
    "MANUAL_REVIEW": "KYC_REVIEW",
    "REJECTED": "REJECTED",
}

# The "happy path" step the demo advance button takes from each status.
NEXT_STATUS: dict[str, OrderStatus] = {
    "QUOTE_ACCEPTED": "KYC_PENDING",
    "KYC_PENDING": "KYC_VERIFIED",
    "KYC_ACTION_REQUIRED": "KYC_VERIFIED",
    "KYC_REVIEW": "KYC_VERIFIED",
    "KYC_VERIFIED": "INSTALL_SCHEDULED",
    "INSTALL_SCHEDULED": "INSTALLING",
    "INSTALLING": "ACTIVE",
}


class IllegalTransition(ValueError):
    pass


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, frozenset())


def check_transition(current: str, target: str) -> None:
    if not can_transition(current, target):
        raise IllegalTransition(f"{current} -> {target} is not allowed")


def status_for_verdict(verdict: KycVerdict) -> OrderStatus:
    return VERDICT_STATUS[verdict]
