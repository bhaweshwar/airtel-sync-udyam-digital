"""Write every backend fixture to frontend/src/api/fixtures/<name>.json for the frontend's VITE_MOCK mode.

Run from the repo root after changing backend/app/fixtures.py:
    backend/.venv/bin/python scripts/export_fixtures.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from pydantic import BaseModel  # noqa: E402

from app.fixtures import all_fixtures  # noqa: E402

OUT = ROOT / "frontend" / "src" / "api" / "fixtures"


def dump(obj: object) -> object:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, list):
        return [dump(x) for x in obj]
    return obj


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, obj in all_fixtures().items():
        (OUT / f"{name}.json").write_text(json.dumps(dump(obj), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(all_fixtures())} fixtures to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
