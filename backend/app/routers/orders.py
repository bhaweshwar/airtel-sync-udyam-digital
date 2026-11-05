"""Orders + tracker API. WS4 owns this file."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException

from .. import store
from ..common.auth import is_backoffice_key
from ..config import settings
from ..contracts import BookSlotRequest, CreateOrderRequest, CreateOrderResponse, InstallSlot, Order, SlotsResponse
from ..orders import service
from ..orders.state import IllegalTransition

router = APIRouter(prefix="/api/orders", tags=["orders"])



def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "No order matches that order ID and PIN."})


def _authorised(order_id: str, pin: Optional[str]) -> dict[str, Any]:
    row = service.authorise(order_id, pin)
    if row is None:
        raise _not_found()
    return row


@router.post("", response_model=CreateOrderResponse)
def create_order(req: CreateOrderRequest) -> CreateOrderResponse:
    resp = service.create_order(req)
    if resp is None:
        raise HTTPException(status_code=404, detail={"code": "QUOTE_NOT_FOUND", "message": "That quote no longer exists."})
    return resp


@router.get("/{order_id}", response_model=Order)
def get_order(order_id: str, pin: str = "") -> Order:
    return service.build_order(_authorised(order_id, pin))


@router.get("/{order_id}/slots", response_model=SlotsResponse)
def get_slots(order_id: str, pin: str = "") -> SlotsResponse:
    _authorised(order_id, pin)
    return SlotsResponse(slots=service.available_slots())


@router.post("/{order_id}/slots", response_model=Order)
def book_slot(order_id: str, req: BookSlotRequest) -> Order:
    _authorised(order_id, req.pin)
    try:
        service.book_slot(order_id, InstallSlot(date=req.date, window=req.window))
    except ValueError as e:
        if isinstance(e, IllegalTransition):
            raise HTTPException(status_code=409, detail={
                "code": "NOT_READY_FOR_SLOT", "message": "An installation slot can be booked once your documents are verified."})
        raise HTTPException(status_code=422, detail={"code": "SLOT_UNAVAILABLE", "message": "That slot is not available. Pick another one."})
    return service.build_order(_authorised(order_id, req.pin))


@router.post("/{order_id}/advance", response_model=Order)
def advance(order_id: str, pin: Optional[str] = None, x_backoffice_key: str = Header(default="")) -> Order:
    """DEMO_MODE only. Accepts the owner's PIN or the back-office key."""
    if not settings.demo_mode:
        raise HTTPException(status_code=403, detail={"code": "DEMO_ONLY", "message": "This control only works in demo mode."})
    if is_backoffice_key(x_backoffice_key):
        if store.get_order(order_id) is None:
            raise _not_found()
    else:
        _authorised(order_id, pin)
    if not service.advance(order_id):
        raise HTTPException(status_code=409, detail={"code": "NO_NEXT_STEP", "message": "This order has no next step."})
    return service.build_order(store.get_order(order_id))
