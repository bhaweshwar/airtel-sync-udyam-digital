"""Shared test setup. Phase 0 owns this file.

Every test run uses a throwaway SQLite file, so tests never touch backend/udyam.db.
Workstream test files can use the `client` fixture (FastAPI TestClient) and `bo_headers`.
"""
from __future__ import annotations

import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="udyam-test-")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ.setdefault("DEMO_MODE", "1")
os.environ.setdefault("BACKOFFICE_KEY", "test-key")
os.environ["GROQ_API_KEY"] = ""  # tests never call a real LLM
os.environ["GEMINI_API_KEY"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def fresh_db():
    db.reset()
    yield


@pytest.fixture(scope="session")
def bo_headers() -> dict[str, str]:
    return {"X-Backoffice-Key": os.environ["BACKOFFICE_KEY"]}
