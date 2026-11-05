"""Plain CRUD helpers for every table. Phase 0 owns this file.

Workstreams call these functions; they never write SQL themselves. Each table has one writer:
advisor_sessions + handoffs (WS2), quotes (WS1), orders + order_events (WS4), consents + kyc_results (WS3).
WS5 only reads.
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from typing import Any, Optional

from .config import settings
from .contracts import BusinessProfile, Check, ConsentRecord, InstallSlot, LocalText, OrderEvent, Quote
from .db import connect


def now() -> datetime:
    """The app clock: the real time of day on settings.today (the case data's reference date, 2026-07-15 by default),
    so event timestamps line up with order dates, slots and the 90-day address-proof rule."""
    real = datetime.now(timezone.utc)
    return datetime.combine(settings.today, real.timetz())


def _iso(dt: datetime | None = None) -> str:
    return (dt or now()).isoformat()


def new_id(prefix: str) -> str:
    """e.g. new_id('Q') -> 'Q-3F9A1C2B'."""
    return f"{prefix}-{secrets.token_hex(4).upper()}"


# ---------------------------------------------------------------- advisor sessions (WS2 writes)

def create_session(profile: BusinessProfile, mode: str = "rules") -> str:
    sid = new_id("S")
    with connect() as c:
        c.execute(
            "INSERT INTO advisor_sessions (id, profile_json, messages_json, stage, mode, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
            (sid, profile.model_dump_json(), "[]", "asking", mode, _iso(), _iso()),
        )
    return sid


def get_session(session_id: str) -> Optional[dict[str, Any]]:
    """Returns {id, profile: BusinessProfile, messages: list[dict], stage, mode, created_at} or None."""
    with connect() as c:
        row = c.execute("SELECT * FROM advisor_sessions WHERE id = ?", (session_id,)).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "profile": BusinessProfile.model_validate_json(row["profile_json"]),
        "messages": json.loads(row["messages_json"]),
        "stage": row["stage"],
        "mode": row["mode"],
        "created_at": datetime.fromisoformat(row["created_at"]),
    }


def update_session(session_id: str, *, profile: BusinessProfile | None = None, messages: list[dict] | None = None,
                   stage: str | None = None, mode: str | None = None) -> None:
    sets, args = ["updated_at = ?"], [_iso()]
    if profile is not None:
        sets.append("profile_json = ?"); args.append(profile.model_dump_json())
    if messages is not None:
        sets.append("messages_json = ?"); args.append(json.dumps(messages, ensure_ascii=False))
    if stage is not None:
        sets.append("stage = ?"); args.append(stage)
    if mode is not None:
        sets.append("mode = ?"); args.append(mode)
    with connect() as c:
        c.execute(f"UPDATE advisor_sessions SET {', '.join(sets)} WHERE id = ?", (*args, session_id))


# ---------------------------------------------------------------- handoffs (WS2 writes, WS5 reads)

def save_handoff(session_id: str, reason: str, phone: str | None = None) -> str:
    """The phone (optional) is stored encrypted plus masked; only the masked copy is ever returned."""
    hid = new_id("H")
    with connect() as c:
        c.execute("INSERT INTO handoffs (id, session_id, reason, status, created_at) VALUES (?,?,?,?,?)",
                  (hid, session_id, reason, "open", _iso()))
    if phone:
        set_handoff_phone(hid, phone)
    return hid


def set_handoff_phone(handoff_id: str, phone: str) -> None:
    from .common.crypto import encrypt
    from .common.mask import mask_phone
    with connect() as c:
        c.execute("UPDATE handoffs SET phone_enc = ?, phone_masked = ? WHERE id = ?",
                  (encrypt(phone), mask_phone(phone), handoff_id))


def list_handoffs() -> list[dict[str, Any]]:
    with connect() as c:
        rows = c.execute(
            "SELECT h.*, s.profile_json FROM handoffs h LEFT JOIN advisor_sessions s ON s.id = h.session_id ORDER BY h.created_at DESC"
        ).fetchall()
    return [{
        "handoff_id": r["id"], "session_id": r["session_id"], "reason": r["reason"], "status": r["status"],
        "created_at": datetime.fromisoformat(r["created_at"]), "phone_masked": r["phone_masked"],
        "profile": BusinessProfile.model_validate_json(r["profile_json"]) if r["profile_json"] else None,
    } for r in rows]


def update_handoff_status(handoff_id: str, status: str) -> None:
    with connect() as c:
        c.execute("UPDATE handoffs SET status = ? WHERE id = ?", (status, handoff_id))


# ---------------------------------------------------------------- quotes (WS1 writes, WS4 reads)

def save_quote(quote: Quote) -> str:
    with connect() as c:
        c.execute("INSERT OR REPLACE INTO quotes (id, profile_json, quote_json, created_at) VALUES (?,?,?,?)",
                  (quote.quote_id, quote.profile.model_dump_json(), quote.model_dump_json(), _iso()))
    return quote.quote_id


def get_quote(quote_id: str) -> Optional[Quote]:
    with connect() as c:
        row = c.execute("SELECT quote_json FROM quotes WHERE id = ?", (quote_id,)).fetchone()
    return Quote.model_validate_json(row["quote_json"]) if row else None


# ---------------------------------------------------------------- orders + events (WS4 writes, WS3/WS5 read)

def create_order(order_id: str, *, quote_id: str, pin_hash: str, contact_name: str, phone_enc: str,
                 phone_masked: str, status: str) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO orders (id, quote_id, pin_hash, contact_name, phone_enc, phone_masked, status, slot_json, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (order_id, quote_id, pin_hash, contact_name, phone_enc, phone_masked, status, None, _iso(), _iso()),
        )


def count_orders() -> int:
    with connect() as c:
        return int(c.execute("SELECT COUNT(*) FROM orders").fetchone()[0])


def _order_row(r: Any) -> dict[str, Any]:
    return {
        "order_id": r["id"], "quote_id": r["quote_id"], "pin_hash": r["pin_hash"], "contact_name": r["contact_name"],
        "phone_enc": r["phone_enc"], "phone_masked": r["phone_masked"], "status": r["status"],
        "slot": InstallSlot.model_validate_json(r["slot_json"]) if r["slot_json"] else None,
        "created_at": datetime.fromisoformat(r["created_at"]), "updated_at": datetime.fromisoformat(r["updated_at"]),
    }


def get_order(order_id: str) -> Optional[dict[str, Any]]:
    """Returns the raw order row as a dict (includes pin_hash and phone_enc: never send it to a client as is)."""
    with connect() as c:
        row = c.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    return _order_row(row) if row else None


def list_orders() -> list[dict[str, Any]]:
    with connect() as c:
        rows = c.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    return [_order_row(r) for r in rows]


def update_order(order_id: str, *, status: str | None = None, slot: InstallSlot | None = None) -> None:
    sets, args = ["updated_at = ?"], [_iso()]
    if status is not None:
        sets.append("status = ?"); args.append(status)
    if slot is not None:
        sets.append("slot_json = ?"); args.append(slot.model_dump_json())
    with connect() as c:
        c.execute(f"UPDATE orders SET {', '.join(sets)} WHERE id = ?", (*args, order_id))


def add_event(order_id: str, status: str, text: LocalText) -> None:
    with connect() as c:
        c.execute("INSERT INTO order_events (order_id, ts, status, text_json) VALUES (?,?,?,?)",
                  (order_id, _iso(), status, text.model_dump_json()))


def list_events(order_id: str) -> list[OrderEvent]:
    with connect() as c:
        rows = c.execute("SELECT * FROM order_events WHERE order_id = ? ORDER BY id", (order_id,)).fetchall()
    return [OrderEvent(ts=datetime.fromisoformat(r["ts"]), status=r["status"], text=LocalText.model_validate_json(r["text_json"]))
            for r in rows]


# ---------------------------------------------------------------- consents (WS3 writes)

def save_consent(order_id: str, version: str, purposes: list[str]) -> ConsentRecord:
    cid = new_id("C")
    created = now()
    with connect() as c:
        c.execute("INSERT INTO consents (id, order_id, version, purposes_json, created_at, withdrawn_at) VALUES (?,?,?,?,?,NULL)",
                  (cid, order_id, version, json.dumps(purposes), _iso(created)))
    return ConsentRecord(consent_id=cid, order_id=order_id, version=version, purposes_accepted=purposes, created_at=created)


def get_active_consent(order_id: str) -> Optional[ConsentRecord]:
    with connect() as c:
        row = c.execute("SELECT * FROM consents WHERE order_id = ? AND withdrawn_at IS NULL ORDER BY created_at DESC LIMIT 1",
                        (order_id,)).fetchone()
    if not row:
        return None
    return ConsentRecord(consent_id=row["id"], order_id=row["order_id"], version=row["version"],
                         purposes_accepted=json.loads(row["purposes_json"]), created_at=datetime.fromisoformat(row["created_at"]))


def withdraw_consent(order_id: str) -> int:
    """Marks every active consent for the order as withdrawn. Returns how many were withdrawn."""
    with connect() as c:
        cur = c.execute("UPDATE consents SET withdrawn_at = ? WHERE order_id = ? AND withdrawn_at IS NULL", (_iso(), order_id))
        return cur.rowcount


# ---------------------------------------------------------------- KYC results (WS3 writes, WS4/WS5 read)

def save_kyc_result(order_id: str, verdict: str, checks: list[Check], fields_masked: dict[str, str],
                    gst_products_blocked: bool = False) -> None:
    with connect() as c:
        c.execute(
            "INSERT OR REPLACE INTO kyc_results (order_id, verdict, checks_json, fields_masked_json, gst_products_blocked, created_at)"
            " VALUES (?,?,?,?,?,?)",
            (order_id, verdict, json.dumps([ch.model_dump(mode="json") for ch in checks], ensure_ascii=False),
             json.dumps(fields_masked, ensure_ascii=False), int(gst_products_blocked), _iso()),
        )


def _kyc_row(r: Any) -> dict[str, Any]:
    return {
        "order_id": r["order_id"], "verdict": r["verdict"],
        "checks": [Check.model_validate(x) for x in json.loads(r["checks_json"])],
        "fields_masked": json.loads(r["fields_masked_json"]),
        "gst_products_blocked": bool(r["gst_products_blocked"]),
        "created_at": datetime.fromisoformat(r["created_at"]),
    }


def get_kyc_result(order_id: str) -> Optional[dict[str, Any]]:
    with connect() as c:
        row = c.execute("SELECT * FROM kyc_results WHERE order_id = ?", (order_id,)).fetchone()
    return _kyc_row(row) if row else None


def list_kyc_results(verdicts: list[str] | None = None) -> list[dict[str, Any]]:
    with connect() as c:
        if verdicts:
            marks = ",".join("?" * len(verdicts))
            rows = c.execute(f"SELECT * FROM kyc_results WHERE verdict IN ({marks}) ORDER BY created_at DESC", verdicts).fetchall()
        else:
            rows = c.execute("SELECT * FROM kyc_results ORDER BY created_at DESC").fetchall()
    return [_kyc_row(r) for r in rows]


def delete_kyc_result(order_id: str) -> None:
    with connect() as c:
        c.execute("DELETE FROM kyc_results WHERE order_id = ?", (order_id,))
