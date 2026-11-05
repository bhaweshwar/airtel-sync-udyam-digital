"""Settings read from environment variables (and an optional .env file at the repo root or in backend/).

Phase 0 owns this file. Workstreams read settings through `settings`; they never read os.environ directly.
"""
from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent


def _load_dotenv() -> None:
    """Minimal .env loader: KEY=VALUE lines, no export, no interpolation. Real env vars win."""
    for path in (REPO_DIR / ".env", BACKEND_DIR / ".env"):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _dev_fernet_key() -> str:
    # Deterministic key for local demos only. Production must set FERNET_KEY.
    return base64.urlsafe_b64encode(hashlib.sha256(b"udyam-digital-dev-key").digest()).decode()


@dataclass(frozen=True)
class Settings:
    today: date
    demo_mode: bool
    backoffice_key: str
    fernet_key: str
    groq_api_key: str
    groq_model: str
    gemini_api_key: str
    gemini_model: str
    llm_order: tuple[str, ...]
    llm_timeout_s: float
    data_dir: Path
    db_path: Path
    frontend_dist: Path

    @property
    def kyc_documents_dir(self) -> Path:
        return self.data_dir / "kyc_documents"

    @property
    def using_dev_secrets(self) -> bool:
        return self.backoffice_key == "accel-demo" or not os.environ.get("FERNET_KEY")


def load_settings() -> Settings:
    return Settings(
        today=date.fromisoformat(os.environ.get("TODAY", "2026-07-15")),
        demo_mode=_bool("DEMO_MODE", True),
        backoffice_key=os.environ.get("BACKOFFICE_KEY", "accel-demo"),
        fernet_key=os.environ.get("FERNET_KEY") or _dev_fernet_key(),
        groq_api_key=os.environ.get("GROQ_API_KEY", ""),
        groq_model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
        gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
        llm_order=tuple(p.strip() for p in os.environ.get("LLM_ORDER", "groq,gemini").split(",") if p.strip()),
        llm_timeout_s=float(os.environ.get("LLM_TIMEOUT_S", "8")),
        data_dir=Path(os.environ.get("DATA_DIR", REPO_DIR / "data")),
        db_path=Path(os.environ.get("DB_PATH", BACKEND_DIR / "udyam.db")),
        frontend_dist=Path(os.environ.get("FRONTEND_DIST", REPO_DIR / "frontend" / "dist")),
    )


settings = load_settings()
