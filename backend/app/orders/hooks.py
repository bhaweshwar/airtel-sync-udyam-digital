"""Hooks other workstreams call into the orders module. WS4 owns this file and replaces the stub body."""
from __future__ import annotations

from ..contracts import KycResult


def on_kyc_result(order_id: str, result: KycResult) -> None:
    """Called by WS3 after every KYC submit. WS4 maps the verdict to an order status transition and writes an event.

    STUB (Phase 0): does nothing.
    """
    return None
