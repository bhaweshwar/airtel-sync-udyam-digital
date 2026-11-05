"""Small helpers for bilingual server text. Phase 0 owns this file."""
from __future__ import annotations

from ..contracts import Language, LocalText


def lt(en: str, hi: str) -> LocalText:
    return LocalText(en=en, hi=hi)


def pick(text: LocalText, language: Language) -> str:
    return text.hi if language == "hi" else text.en
