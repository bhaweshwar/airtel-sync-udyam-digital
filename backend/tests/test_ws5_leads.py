"""WS5: lead score, channel rules and back-office endpoints."""
from __future__ import annotations

from app import contracts as c
from app.leads.channels import suggested_channel
from app.leads.model import FEATURES, INTAKE_COLUMNS, LEAKAGE_COLUMNS, get_model


def test_no_leakage_columns_in_features():
    for col in LEAKAGE_COLUMNS:
        assert col not in FEATURES and col not in INTAKE_COLUMNS
    assert not any(f.startswith(("stage", "outcome", "drop", "bundle", "churn", "nps")) for f in FEATURES)
    assert all(f.split("=")[0] in FEATURES for f, _, _ in get_model().coefficients)


def test_time_split_auc():
    m = get_model()
    assert m.auc_time_split >= 0.65
    assert m.top_decile_lift > 1.5 and m.top20_capture > 0.25
    assert m.train_rows + m.test_rows == 5000


def test_channel_rules():
    base = {"segment": "prof", "city_tier": 1, "preferred_language": "English", "products_of_interest": "", "drop_reason": None}
    assert suggested_channel({**base, "segment": "multi", "drop_reason": "Unreachable after 3 attempts"}) == "SELF_SERVE_LINK"
    assert suggested_channel({**base, "segment": "mfg", "drop_reason": "Quote too complex to understand"}) == "FIELD"
    assert suggested_channel({**base, "city_tier": 2, "preferred_language": "Marathi"}) == "PARTNER"
    assert suggested_channel(base) == "INSIDE_SALES"


def test_endpoints(client, bo_headers):
    assert client.get("/api/backoffice/leads").status_code == 401
    assert client.get("/api/backoffice/model", headers={"X-Backoffice-Key": "wrong"}).status_code == 401

    page = c.LeadsPage.model_validate(client.get("/api/backoffice/leads?limit=20", headers=bo_headers).json())
    assert page.total > 1000 and len(page.items) == 20
    scores = [r.score for r in page.items]
    assert scores == sorted(scores, reverse=True) and page.items[0].band == "HOT"
    assert all(r.drop_reason and r.top_factors for r in page.items)

    field = c.LeadsPage.model_validate(client.get("/api/backoffice/leads?channel=FIELD&segment=mfg", headers=bo_headers).json())
    assert field.total > 0 and all(r.suggested_channel == "FIELD" and r.segment == "mfg" for r in field.items)

    funnel = c.FunnelReport.model_validate(client.get("/api/backoffice/funnel", headers=bo_headers).json())
    assert [s.count for s in funnel.baseline] == [5000, 3406, 1974, 861, 588, 368]

    report = c.ModelReport.model_validate(client.get("/api/backoffice/model", headers=bo_headers).json())
    assert len(report.coefficients) == 10 and "not who activates" in report.caveat.en


def test_queues_read_the_store(client, bo_headers, fresh_db):
    from app import fixtures, store
    from app.common.i18n_server import lt

    sid = store.create_session(c.BusinessProfile(segment="micro"))
    store.save_handoff(sid, "Asked to talk to a person")
    quote = fixtures.quote()
    store.save_quote(quote)
    store.create_order("UD-TEST-1", quote_id=quote.quote_id, pin_hash="x", contact_name="Anita", phone_enc="e",
                       phone_masked="••••••3210", status="KYC_REVIEW")
    store.save_kyc_result("UD-TEST-1", "MANUAL_REVIEW", [
        c.Check(code="GSTIN_ACTIVE", status="PASS", message=lt("ok", "ठीक")),
        c.Check(code="NAME_MATCH", status="FAIL", message=lt("Names differ", "नाम अलग हैं")),
    ], {})

    hs = client.get("/api/backoffice/handoffs", headers=bo_headers).json()
    assert len(hs) == 1 and hs[0]["profile"]["segment"] == "micro"
    ks = client.get("/api/backoffice/kyc-reviews", headers=bo_headers).json()
    assert [ch["code"] for ch in ks[0]["failing_checks"]] == ["NAME_MATCH"]
    os_ = client.get("/api/backoffice/orders", headers=bo_headers).json()
    assert os_[0]["phone_masked"] == "••••••3210" and os_[0]["monthly_total_inr"] == quote.monthly_total_inr
    assert client.get("/api/backoffice/funnel", headers=bo_headers).json()["live"] == {"KYC_REVIEW": 1}
