"""Orders + tracker API. WS4 owns this file. STUB (Phase 0): returns fixtures of the contract shape."""
from __future__ import annotations

from fastapi import APIRouter, Header

from .. import fixtures
from ..contracts import BookSlotRequest, CreateOrderRequest, CreateOrderResponse, Order, SlotsResponse

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", response_model=CreateOrderResponse)
def create_order(req: CreateOrderRequest) -> CreateOrderResponse:
    return fixtures.create_order_response()


@router.get("/{order_id}", response_model=Order)
def get_order(order_id: str, pin: str) -> Order:
    return fixtures.order(order_id)


@router.get("/{order_id}/slots", response_model=SlotsResponse)
def get_slots(order_id: str, pin: str) -> SlotsResponse:
    return fixtures.install_slots()


@router.post("/{order_id}/slots", response_model=Order)
def book_slot(order_id: str, req: BookSlotRequest) -> Order:
    from ..contracts import InstallSlot
    return fixtures.order(order_id).model_copy(update={"status": "INSTALL_SCHEDULED",
                                                       "install_slot": InstallSlot(date=req.date, window=req.window)})


@router.post("/{order_id}/advance", response_model=Order)
def advance(order_id: str, pin: str | None = None, x_backoffice_key: str = Header(default="")) -> Order:
    """DEMO_MODE only. Accepts the owner's PIN or the back-office key."""
    return fixtures.order(order_id)
