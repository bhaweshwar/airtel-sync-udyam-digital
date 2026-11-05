"""WS4: orders, status machine, KYC hook, ETAs and PIN handling."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app import store
from app.config import settings
from app.contracts import Check, KycResult, LocalText
from app.fixtures import quote as fixture_quote
from app.orders import service
from app.orders.hooks import on_kyc_result
from app.orders.state import IllegalTransition, check_transition, status_for_verdict

TODAY = settings.today


@pytest.fixture()
def three_item_quote(fresh_db, monkeypatch):
    """A saved 3-product quote (fibre 5 days, email 1 day, CCTV 4 days); engine.price echoes it back re-priced."""
    q = fixture_quote()
    items = [q.items[0], q.items[1], q.addons_available[0].model_copy(update={"kind": "core"})]
    q = q.model_copy(update={"quote_id": "Q-WS4TEST", "items": items})
    store.save_quote(q)
    monkeypatch.setattr(service.engine, "price", lambda profile, selected: q.model_copy(update={"quote_id": store.new_id("Q")}))
    service.reset_attempts()
    return q


def _place(client) -> tuple[str, str]:
    r = client.post("/api/orders", json={"quote_id": "Q-WS4TEST", "contact_name": "Anita Shah", "phone": "9876543210"})
    assert r.status_code == 200, r.text
    body = r.json()
    return body["order_id"], body["pin"]


def _kyc(order_id: str, verdict: str, doc_type: str | None = None) -> None:
    checks = [Check(code="BLUR", status="FAIL", message=LocalText(en="Blurry", hi="धुंधला"), doc_type=doc_type)] if doc_type else []
    on_kyc_result(order_id, KycResult(order_id=order_id, verdict=verdict, checks=checks, created_at=datetime.now(timezone.utc)))
    if checks:
        store.save_kyc_result(order_id, verdict, checks, {})


def test_illegal_transitions_rejected():
    check_transition("KYC_PENDING", "KYC_VERIFIED")
    check_transition("KYC_ACTION_REQUIRED", "KYC_PENDING")
    for current, target in [("KYC_PENDING", "ACTIVE"), ("KYC_REVIEW", "KYC_PENDING"), ("KYC_VERIFIED", "INSTALLING"),
                            ("REJECTED", "KYC_VERIFIED"), ("ACTIVE", "INSTALLING"), ("QUOTE_ACCEPTED", "KYC_VERIFIED")]:
        with pytest.raises(IllegalTransition):
            check_transition(current, target)


def test_create_order_stores_only_hash_and_encrypted_phone(client, three_item_quote):
    order_id, pin = _place(client)
    assert order_id == f"UD-{TODAY:%y%m%d}-0001" and len(pin) == 4 and pin.isdigit()
    row = store.get_order(order_id)
    assert pin not in row["pin_hash"] and service.verify_pin(pin, row["pin_hash"])
    assert "9876543210" not in row["phone_enc"] and service.decrypt_phone(row["phone_enc"]) == "9876543210"
    assert row["phone_masked"].endswith("3210") and row["status"] == "KYC_PENDING"
    assert row["quote_id"] != "Q-WS4TEST"  # re-priced copy
    assert [e.status for e in store.list_events(order_id)] == ["QUOTE_ACCEPTED", "KYC_PENDING"]
    assert client.post("/api/orders", json={"quote_id": "Q-NOPE", "contact_name": "A", "phone": "9876543210"}).status_code == 404


def test_kyc_verdict_mapping(client, three_item_quote):
    assert status_for_verdict("VERIFIED") == "KYC_VERIFIED"
    assert status_for_verdict("MANUAL_REVIEW") == "KYC_REVIEW"
    order_id, pin = _place(client)
    _kyc(order_id, "ACTION_REQUIRED", doc_type="gst_certificate")
    o = client.get(f"/api/orders/{order_id}", params={"pin": pin}).json()
    assert o["status"] == "KYC_ACTION_REQUIRED"
    assert o["next_action"]["en"] == "Retake your GST certificate photo."
    assert [s["state"] for s in o["timeline"]][:2] == ["done", "blocked"]
    _kyc(order_id, "ACTION_REQUIRED", doc_type="gst_certificate")  # still wrong after a retake
    assert store.get_order(order_id)["status"] == "KYC_ACTION_REQUIRED"
    _kyc(order_id, "MANUAL_REVIEW")
    assert store.get_order(order_id)["status"] == "KYC_REVIEW"
    _kyc(order_id, "VERIFIED")
    o = client.get(f"/api/orders/{order_id}", params={"pin": pin}).json()
    assert o["status"] == "KYC_VERIFIED" and o["next_action"]["en"] == "Pick an installation slot."
    _kyc(order_id, "REJECTED")  # too late: ignored, never raises
    assert store.get_order(order_id)["status"] == "KYC_VERIFIED"


def test_eta_for_three_product_bundle(client, three_item_quote):
    order_id, pin = _place(client)
    o = client.get(f"/api/orders/{order_id}", params={"pin": pin}).json()
    start = TODAY + timedelta(days=2)  # before KYC: today + 2
    assert {e["product_id"]: e["eta"] for e in o["item_etas"]} == {
        "P02": str(start + timedelta(days=5)), "P16": str(start + timedelta(days=1)), "P23": str(start + timedelta(days=4))}
    assert o["eta_activation_date"] == str(start + timedelta(days=5))

    _kyc(order_id, "VERIFIED")
    slots = client.get(f"/api/orders/{order_id}/slots", params={"pin": pin}).json()["slots"]
    assert len(slots) == 10 and all(datetime.fromisoformat(s["date"]).weekday() < 5 for s in slots)
    assert slots[0]["date"] > str(TODAY)
    pick = slots[3]
    o = client.post(f"/api/orders/{order_id}/slots", json={"pin": pin, **pick}).json()
    booked = datetime.fromisoformat(pick["date"]).date()
    assert o["status"] == "INSTALL_SCHEDULED" and o["install_slot"] == pick
    assert o["eta_activation_date"] == str(booked + timedelta(days=5))

    for expected in ("INSTALLING", "ACTIVE"):
        o = client.post(f"/api/orders/{order_id}/advance", params={"pin": pin}).json()
        assert o["status"] == expected
    assert all(s["state"] == "done" for s in o["timeline"])
    assert client.post(f"/api/orders/{order_id}/advance", params={"pin": pin}).status_code == 409


def test_wrong_pin_is_404_and_rate_limited(client, three_item_quote, bo_headers):
    order_id, pin = _place(client)
    wrong = "0000" if pin != "0000" else "1111"
    assert client.get(f"/api/orders/{order_id}", params={"pin": wrong}).status_code == 404
    assert client.get(f"/api/orders/{order_id}").status_code == 404
    missing = client.get("/api/orders/UD-000000-9999", params={"pin": pin})
    assert missing.status_code == 404 and missing.json() == client.get(f"/api/orders/{order_id}", params={"pin": wrong}).json()
    assert client.get(f"/api/orders/{order_id}/slots", params={"pin": wrong}).status_code == 404
    for _ in range(10):
        client.get(f"/api/orders/{order_id}", params={"pin": wrong})
    assert client.get(f"/api/orders/{order_id}", params={"pin": pin}).status_code == 404  # locked for a minute
    # the back office can still advance it
    assert client.post(f"/api/orders/{order_id}/advance", headers=bo_headers).json()["status"] == "KYC_VERIFIED"
