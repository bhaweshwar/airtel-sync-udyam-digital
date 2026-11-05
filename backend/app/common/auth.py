"""Back-office passcode check. Phase 0 owns this file."""
from __future__ import annotations

import hmac

from fastapi import Header, HTTPException

from ..config import settings


def require_backoffice_key(x_backoffice_key: str = Header(default="")) -> None:
    """FastAPI dependency: every /api/backoffice route uses Depends(require_backoffice_key)."""
    if not x_backoffice_key or not hmac.compare_digest(x_backoffice_key, settings.backoffice_key):
        raise HTTPException(status_code=401, detail={"code": "BACKOFFICE_KEY", "message": "Wrong or missing back-office passcode."})


def is_backoffice_key(value: str | None) -> bool:
    return bool(value) and hmac.compare_digest(value, settings.backoffice_key)  # type: ignore[arg-type]
