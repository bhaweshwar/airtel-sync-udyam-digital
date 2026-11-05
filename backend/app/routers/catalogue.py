"""Catalogue API. WS1 owns this file."""
from __future__ import annotations

from fastapi import APIRouter

from .. import data
from ..contracts import Product

router = APIRouter(prefix="/api", tags=["catalogue"])


@router.get("/catalogue", response_model=list[Product])
def catalogue() -> list[Product]:
    return data.catalogue()
