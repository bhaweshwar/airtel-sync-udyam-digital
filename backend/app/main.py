"""FastAPI app: registers every router, serves the built React app, masks identifiers in access logs.

Phase 0 owns this file. Workstreams never edit it: every router is already included below.
Run: cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import data, db, fixtures
from .common.mask import redact
from .config import settings
from .contracts import Meta
from .routers import advisor, backoffice, catalogue, kyc, orders, quote, registry

log = logging.getLogger("udyam")


class RedactFilter(logging.Filter):
    """Masks GSTINs, Udyam numbers and phone numbers in log lines (access logs include URL paths)."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact(record.msg)
        if record.args:
            record.args = tuple(redact(a) if isinstance(a, str) else a for a in record.args)  # type: ignore[assignment]
        return True


for name in ("uvicorn.access", "uvicorn.error", "udyam"):
    logging.getLogger(name).addFilter(RedactFilter())


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init()
    data.warm()
    if settings.warm_ocr:
        def _warm_ocr() -> None:
            try:
                from .kyc import ocr
                ocr._get_engine()
            except Exception:  # never block startup on the OCR models
                log.exception("OCR warm-up failed; models will load on the first KYC check")
        threading.Thread(target=_warm_ocr, name="warm-ocr", daemon=True).start()
    if settings.using_dev_secrets:
        log.warning("Using development secrets (BACKOFFICE_KEY / FERNET_KEY). Set them before any real deployment.")
    yield


app = FastAPI(title="Udyam Digital API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (registry.router, catalogue.router, quote.router, advisor.router, kyc.router, orders.router, backoffice.router):
    app.include_router(r)


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/meta", response_model=Meta, tags=["meta"])
def meta() -> Meta:
    return fixtures.meta()


# ---------------------------------------------------------------- built frontend (single deploy)

_dist = settings.frontend_dist
if (_dist / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def spa(path: str):
    if path.startswith("api/"):
        raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "No such API route."})
    index = _dist / "index.html"
    if not index.is_file():
        return JSONResponse({"message": "Frontend not built. Run `npm run build` in frontend/, or use the Vite dev server on :5173."})
    candidate = (_dist / path).resolve()
    if path and candidate.is_file() and _dist.resolve() in candidate.parents:
        return FileResponse(candidate)
    return FileResponse(index)
