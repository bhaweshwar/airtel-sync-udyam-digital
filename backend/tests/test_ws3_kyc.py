"""WS3 Smart KYC tests. Fast and OCR-free: scripts/kyc_eval.py is the one OCR run."""
from __future__ import annotations

from datetime import date, timedelta

from app.common.gstin import is_valid
from app.config import settings
from app.contracts import Check
from app.common.i18n_server import lt
from app.kyc import checks, ocr
from app.kyc.consent import NOTICE_VERSION
from app.kyc.parse import ParsedDoc, address_pin, repair_gstin, respace, split_proprietor

TODAY = settings.today


# ---------------------------------------------------------------- GSTIN look-alike repair

def test_repair_fixes_letter_o_misreads():
    k02 = repair_gstin("19E0GXH4115Y1ZL")  # PAN letter O read as zero
    assert k02.repaired and k02.value == "19EOGXH4115Y1ZL" and k02.swaps == [4]
    k08 = repair_gstin("24X0RXG9365M1Z3")
    assert k08.repaired and k08.value == "24XORXG9365M1Z3"
    k04 = repair_gstin("27PZSXS193601ZH")  # entity number can't be 0, so it must be the letter O
    assert k04.repaired and k04.value == "27PZSXS1936O1ZH"
    assert not repair_gstin("27QHJXK0658U1ZL").repaired  # already valid (K10): left alone


def test_repair_never_fixes_k06():
    for read in ("08YKZXS8189L1ZO", "08YKZXS8189L1Z0"):  # tampered 5 -> 8 is not an OCR look-alike
        out = repair_gstin(read)
        assert not out.repaired and not is_valid(out.value)


# ---------------------------------------------------------------- verdict mapping

def _c(code: str, status: str = "FAIL") -> Check:
    return Check(code=code, status=status, message=lt("x", "x"))  # type: ignore[arg-type]


def test_verdict_mapping():
    assert checks.verdict_for([_c("DOC_PRESENT", "PASS"), _c("SIGNATORY_MATCH", "WARN")]) == "VERIFIED"
    assert checks.verdict_for([_c("ADDRESS_RECENT")]) == "ACTION_REQUIRED"
    assert checks.verdict_for([_c("IMAGE_READABLE"), _c("NAME_CONSISTENT")]) == "MANUAL_REVIEW"
    assert checks.verdict_for([_c("GSTIN_CHECKSUM"), _c("NAME_CONSISTENT"), _c("DOC_PRESENT")]) == "REJECTED"
    assert checks.verdict_for([_c("GSTIN_ACTIVE")]) == "REJECTED"


def test_address_proof_90_day_boundary():
    assert checks.address_recent_check(TODAY - timedelta(days=90), TODAY).status == "PASS"
    stale = checks.address_recent_check(TODAY - timedelta(days=91), TODAY)
    assert stale.status == "FAIL" and "91 days" in stale.message.en
    assert checks.address_recent_check(TODAY + timedelta(days=1), TODAY).status == "FAIL"
    assert checks.address_recent_check(date(2025, 10, 31), TODAY).message.en.startswith("Your bill is 257 days old")


# ---------------------------------------------------------------- checks on hand-built documents (what OCR would read)

def _docs(gstin: str, legal: str, trade: str, constitution: str, udyam: str, signer: str, address: str) -> dict:
    def doc(t, **fields):
        return ParsedDoc(doc_type=t, detected_type=t, blurry=False, blur_score=900.0, skew_deg=0.0, fields=fields)
    return {
        "gst_certificate": doc("gst_certificate", gstin=gstin, legal_name=legal, trade_name=trade,
                               constitution=constitution, address=address),
        "udyam_certificate": doc("udyam_certificate", udyam_number=udyam, enterprise_name=trade),
        "signatory_id": doc("signatory_id", name=signer, business_name=trade, valid_till="2029-06-01"),
        "address_proof": doc("address_proof", holder_name=trade, supply_address=address, bill_date="2026-06-18"),
    }


def test_k07_name_mismatch_goes_to_manual_review():
    docs = _docs("07CPCXN0398P1ZT", "Neha Banerjee (Prop. Shri Physio Clinic)", "Neelgiri Physio Clinic",
                 "Proprietorship", "UDYAM-DL-00-9565547", "NehaBanerjee",
                 "Shop/Unit 52, Transport Nagar, Delhi, Delhi -334596")
    out = checks.run_checks(docs, TODAY)
    status = {c.code: c.status for c in out.checks}
    assert out.verdict == "MANUAL_REVIEW"
    assert status["NAME_CONSISTENT"] == "FAIL" and status["SIGNATORY_MATCH"] == "PASS"


def test_k10_llp_signatory_is_only_a_warning():
    docs = _docs("27QHJXK0658U1ZL", "Kaveri Stays LLP", "Kaveri Stays LLP", "Limited Liability Partnership",
                 "UDYAM-MH-00-7183141", "Nisha Arora", "Shop/Unit 21, Sector 14, Mumbai, Maharashtra-570043")
    out = checks.run_checks(docs, TODAY)
    assert out.verdict == "VERIFIED"
    assert {c.code: c.status for c in out.checks}["SIGNATORY_MATCH"] == "WARN"
    assert out.fields_masked["gstin"] == "27QH••••••••1ZL"


def test_parse_helpers():
    assert split_proprietor("Joseph Singh (Prop. Ganesh Woodcraft)") == ("Joseph Singh", "Ganesh Woodcraft")
    assert split_proprietor("Kaveri Stays LLP") == (None, "Kaveri Stays LLP")
    assert address_pin("Shop/Unit 38, Civil Lines, Kochi, Kerala - 752083") == "752083"
    assert respace("VindhyaTours &Travels") == "Vindhya Tours & Travels"


# ---------------------------------------------------------------- consent gate (API)

def test_403_without_consent_and_withdrawal(client, fresh_db):
    oid = "UD-WS3-0001"
    files = {"file": ("gst.png", b"not really an image", "image/png")}
    for resp in (client.post(f"/api/kyc/{oid}/documents", data={"doc_type": "gst_certificate"}, files=files),
                 client.post(f"/api/kyc/{oid}/submit"),
                 client.post(f"/api/kyc/{oid}/sample/K03")):
        assert resp.status_code == 403 and resp.json()["detail"]["code"] == "CONSENT_REQUIRED"

    notice = client.get("/api/kyc/notice").json()
    assert notice["version"] == NOTICE_VERSION
    assert [p["required"] for p in notice["purposes"]] == [True, False]
    bad = client.post(f"/api/kyc/{oid}/consent", json={"version": NOTICE_VERSION, "purposes_accepted": ["service_improvement"]})
    assert bad.status_code == 422
    ok = client.post(f"/api/kyc/{oid}/consent", json={"version": NOTICE_VERSION, "purposes_accepted": ["kyc_verification"]})
    assert ok.status_code == 200

    assert client.post(f"/api/kyc/{oid}/documents", data={"doc_type": "gst_certificate"}, files=files).status_code == 422
    result = client.post(f"/api/kyc/{oid}/submit").json()  # nothing uploaded yet: four missing documents
    assert result["verdict"] == "ACTION_REQUIRED"
    assert sum(c["code"] == "DOC_PRESENT" and c["status"] == "FAIL" for c in result["checks"]) == 4

    assert client.delete(f"/api/kyc/{oid}/consent").status_code == 204
    from app import store
    assert store.get_kyc_result(oid) is None and store.get_active_consent(oid) is None
    assert client.post(f"/api/kyc/{oid}/submit").status_code == 403
    assert ocr._engine is None  # nothing above ran OCR
