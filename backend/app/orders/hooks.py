"""Hooks other workstreams call into the orders module. WS4 owns this file."""
from __future__ import annotations

import logging

from .. import store
from ..common.i18n_server import lt
from ..contracts import KycResult, LocalText
from .state import can_transition, status_for_verdict

log = logging.getLogger(__name__)

VERDICT_TEXT: dict[str, LocalText] = {
    "VERIFIED": lt("Your business documents are verified.", "आपके व्यवसाय के दस्तावेज़ सत्यापित हो गए।"),
    "ACTION_REQUIRED": lt("Some document photos need a retake.", "कुछ दस्तावेज़ों की फ़ोटो दोबारा लेनी होगी।"),
    "MANUAL_REVIEW": lt("Your documents are with our team for a quick manual check.",
                        "आपके दस्तावेज़ हमारी टीम के पास एक छोटी जाँच के लिए हैं।"),
    "REJECTED": lt("We could not verify your business documents.", "हम आपके व्यवसाय के दस्तावेज़ सत्यापित नहीं कर सके।"),
}

RETAKE_TEXT = lt("New document photos received. Checking them again.", "दस्तावेज़ों की नई फ़ोटो मिल गईं। दोबारा जाँच हो रही है।")


def on_kyc_result(order_id: str, result: KycResult) -> None:
    """Called by WS3 after every KYC submit: maps the verdict to an order transition and writes an event.

    Never raises into the KYC flow: an unknown order or a verdict that no longer applies (say the order is
    already being installed) is logged and ignored.
    """
    row = store.get_order(order_id)
    if row is None:
        log.warning("KYC result for unknown order %s ignored", order_id)
        return
    current, target = row["status"], status_for_verdict(result.verdict)
    text = VERDICT_TEXT[result.verdict]
    if current == "QUOTE_ACCEPTED":
        store.update_order(order_id, status="KYC_PENDING")
        current = "KYC_PENDING"
    if current == target == "KYC_ACTION_REQUIRED":
        # A retake that still needs work: re-run KYC (back to pending), then flag it again.
        store.update_order(order_id, status="KYC_PENDING")
        store.add_event(order_id, "KYC_PENDING", RETAKE_TEXT)
        current = "KYC_PENDING"
    if not can_transition(current, target):
        log.info("KYC verdict %s ignored for order %s in status %s", result.verdict, order_id, current)
        return
    store.update_order(order_id, status=target)
    store.add_event(order_id, target, text)
