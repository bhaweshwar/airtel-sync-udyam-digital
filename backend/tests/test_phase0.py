"""Phase 0 checks: shared helpers, registry lookups, and every stub endpoint answering in its contract shape."""
from __future__ import annotations

import io

from app import contracts as c
from app import data, store
from app.common import gstin as gst
from app.common.mask import mask_gstin, mask_phone, mask_udyam, redact


def test_every_registry_gstin_passes_format_and_checksum():
    reg = data.gstin_registry()
    assert len(reg) == 3534
    bad = [g for g in reg if not gst.is_valid(g)]
    assert bad == []


def test_state_codes_agree_with_registry():
    mismatched = {g[:2] for g, r in data.gstin_registry().items() if gst.state_for(g) != r["state"]}
    assert mismatched == set()


def test_specimen_gstins():
    assert gst.is_valid("27QHJXK0658U1ZL")          # K10: clean
    assert not gst.checksum_valid("08YKZXS8189L1ZO")  # K06: tampered digit
    assert gst.is_valid("08YKZXS5189L1ZO")          # K06's registry entry


def test_udyam_normalisation():
    assert gst.normalize_udyam("udyam kl 00 3078801") == "UDYAM-KL-00-3078801"
    assert gst.udyam_format_valid("UDYAM-KL-00-3078801")


def test_masking():
    assert mask_gstin("27QHJXK0658U1ZL") == "27QH••••••••1ZL"
    assert mask_udyam("UDYAM-KL-00-3078801") == "UDYAM-KL-00-•••8801"
    assert mask_phone("+91 98765 43210") == "••••••3210"
    assert "27QHJXK0658U1ZL" not in redact("GET /api/registry/gstin/27QHJXK0658U1ZL call 9876543210")


def test_data_maps():
    assert len(data.catalogue()) == 25
    assert data.city_tiers()["kochi"]["tier"] == 2
    assert data.business_type_segments()["dental clinic"] == "prof"
    assert data.products_by_id()["P23"].requires_one_of == ["P01", "P02", "P03", "P04", "P05", "P06"]


def test_registry_endpoints(client):
    r = client.get("/api/registry/gstin/27QHJXK0658U1ZL").json()
    assert r["found"] and r["checksum_valid"] and r["status"] == "Active" and r["legal_name"] == "Kaveri Stays LLP"
    r = client.get("/api/registry/gstin/08YKZXS8189L1ZO").json()
    assert r["format_valid"] and not r["checksum_valid"] and not r["found"]
    r = client.get("/api/registry/gstin/37IHKXV5167L1ZS").json()
    assert r["status"] == "Cancelled"
    r = client.get("/api/registry/udyam/UDYAM-KL-00-3078801").json()
    assert r["found"] and r["enterprise_name"] == "Balaji Dental Care LLP"


def test_store_roundtrip(fresh_db):
    from app.fixtures import quote
    q = quote()
    store.save_quote(q)
    assert store.get_quote(q.quote_id).monthly_total_inr == q.monthly_total_inr
    sid = store.create_session(c.BusinessProfile(language="hi"))
    store.update_session(sid, stage="handoff", messages=[{"role": "user", "text": "नमस्ते"}])
    assert store.get_session(sid)["messages"][0]["text"] == "नमस्ते"
    store.create_order("UD-TEST-0001", quote_id=q.quote_id, pin_hash="x", contact_name="A", phone_enc="e",
                       phone_masked="••••3210", status="KYC_PENDING")
    store.add_event("UD-TEST-0001", "KYC_PENDING", c.LocalText(en="ok", hi="ठीक"))
    assert store.list_events("UD-TEST-0001")[0].text.hi == "ठीक"
    store.save_consent("UD-TEST-0001", "v1", ["kyc_verification"])
    assert store.get_active_consent("UD-TEST-0001") is not None
    assert store.withdraw_consent("UD-TEST-0001") == 1


def test_stub_endpoints_answer_in_contract_shape(client, bo_headers):
    from app.fixtures import profile
    p = profile().model_dump(mode="json")
    c.Quote.model_validate(client.post("/api/recommend", json={"profile": p}).json())
    c.Quote.model_validate(client.post("/api/quote", json={"profile": p, "selected": [{"product_id": "P02", "quantity": 1}]}).json())
    assert len(client.get("/api/catalogue").json()) == 25
    c.AdvisorReply.model_validate(client.post("/api/advisor/message", json={"text": "hello"}).json())
    c.HandoffResponse.model_validate(client.post("/api/advisor/handoff", json={"session_id": "S-1", "reason": "x"}).json())
    c.LlmStatus.model_validate(client.get("/api/llm-status").json())
    c.ConsentNotice.model_validate(client.get("/api/kyc/notice").json())
    c.ConsentRecord.model_validate(client.post("/api/kyc/UD-1/consent", json={"version": "v1", "purposes_accepted": ["kyc_verification"]}).json())
    assert client.delete("/api/kyc/UD-1/consent").status_code == 204
    files = {"file": ("x.png", io.BytesIO(b"\x89PNG"), "image/png")}
    c.DocumentResult.model_validate(client.post("/api/kyc/UD-1/documents", data={"doc_type": "gst_certificate"}, files=files).json())
    c.KycResult.model_validate(client.post("/api/kyc/UD-1/submit").json())
    c.KycResult.model_validate(client.post("/api/kyc/UD-1/sample/K03").json())
    c.CreateOrderResponse.model_validate(client.post("/api/orders", json={"quote_id": "Q-1", "contact_name": "A", "phone": "9876543210"}).json())
    c.Order.model_validate(client.get("/api/orders/UD-1", params={"pin": "1234"}).json())
    c.SlotsResponse.model_validate(client.get("/api/orders/UD-1/slots", params={"pin": "1234"}).json())
    c.Order.model_validate(client.post("/api/orders/UD-1/advance", params={"pin": "1234"}).json())
    assert client.get("/api/backoffice/leads").status_code == 401
    c.LeadsPage.model_validate(client.get("/api/backoffice/leads", headers=bo_headers).json())
    for path in ("handoffs", "kyc-reviews", "orders"):
        assert isinstance(client.get(f"/api/backoffice/{path}", headers=bo_headers).json(), list)
    c.ModelReport.model_validate(client.get("/api/backoffice/model", headers=bo_headers).json())
    c.FunnelReport.model_validate(client.get("/api/backoffice/funnel", headers=bo_headers).json())
    c.Meta.model_validate(client.get("/api/meta").json())
    assert client.get("/api/nope").status_code == 404
