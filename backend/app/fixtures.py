"""Example objects for every contract. Phase 0 owns this file.

Stub routers return these until a workstream replaces its stub, and scripts/export_fixtures.py writes them to
frontend/src/api/fixtures/*.json for the frontend's VITE_MOCK mode. The numbers are illustrative (they follow the
midpoint pricing rule) and are not a specification of WS1's engine.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from .config import settings
from .contracts import (
    AdvisorReply, BusinessProfile, Check, ConsentNotice, ConsentPurpose, ConsentRecord, CreateOrderResponse,
    DocQuality, DocumentResult, FunnelReport, FunnelStage, HandoffResponse, HandoffRow, Ineligible, InstallSlot,
    ItemEta, KycResult, KycReviewRow, LeadRow, LeadsPage, LineItem, LlmProviderStatus, LlmStatus, Meta,
    ModelCoefficient, ModelReport, Order, OrderEvent, OrderRow, OrderTotals, Quote, SlotsResponse, TimelineStep,
)
from .common.i18n_server import lt

TODAY = settings.today
NOW = datetime(TODAY.year, TODAY.month, TODAY.day, 10, 30, tzinfo=timezone.utc)


def profile() -> BusinessProfile:
    return BusinessProfile(
        business_type="Dental clinic", segment="prof", city="Kochi", city_tier=2, state="Kerala",
        employees=12, sites=1, has_gstin=True, gstin="32TTNXB7384T1ZW", gstin_status="Active",
        current_internet="home_broadband", needs=["internet", "email", "security", "cloud_backup"], language="en",
    )


def _item(pid, name, cat, unit, qty, price, setup, months, days, en, hi, kind="core") -> LineItem:
    return LineItem(product_id=pid, name=name, category=cat, unit=unit, quantity=qty, unit_price_inr=price,
                    monthly_inr=price * qty, setup_inr=setup * qty, contract_months=months, install_days=days,
                    reason=lt(en, hi), kind=kind)


def quote() -> Quote:
    items = [
        _item("P02", "Biz Fibre 300", "Connectivity", "per site", 1, 1649, 0, 12, 5,
              "Fast fibre for one clinic, with room for X-ray uploads and video calls.",
              "एक क्लिनिक के लिए तेज़ फ़ाइबर, एक्स-रे अपलोड और वीडियो कॉल के लिए काफ़ी।"),
        _item("P16", "Cloud Email & Office Suite", "Cloud & Productivity", "per user", 12, 138, 0, 12, 1,
              "12 staff, so 12 email accounts on your clinic's own domain.",
              "12 कर्मचारी, इसलिए आपके क्लिनिक के डोमेन पर 12 ईमेल खाते।"),
        _item("P20", "Endpoint Security", "Security", "per device", 12, 124, 0, 12, 1,
              "Patient records need protection on every computer.",
              "हर कंप्यूटर पर मरीज़ों के रिकॉर्ड की सुरक्षा ज़रूरी है।"),
        _item("P17", "Cloud Backup 1 TB", "Cloud & Productivity", "per account", 1, 599, 0, 12, 1,
              "A daily copy of your records, so a broken laptop loses nothing.",
              "रिकॉर्ड की रोज़ाना कॉपी, ताकि लैपटॉप ख़राब होने पर कुछ न खोए।"),
    ]
    addons = [
        _item("P23", "Cloud CCTV", "IoT & Physical", "per camera", 2, 249, 1800, 12, 4,
              "Two cameras for the reception and the entrance.", "रिसेप्शन और प्रवेश के लिए दो कैमरे।", kind="addon"),
        _item("P11", "Static IP", "Connectivity", "per IP", 1, 250, 0, 12, 1,
              "Needed if your dental software is reached from outside.", "अगर डेंटल सॉफ़्टवेयर बाहर से खोलना हो तो ज़रूरी।",
              kind="addon"),
        _item("P09", "Backup 4G/5G Failover", "Connectivity", "per site", 1, 549, 1500, 12, 3,
              "Keeps appointments and payments running if the fibre goes down.",
              "फ़ाइबर बंद होने पर भी अपॉइंटमेंट और भुगतान चलते रहें।", kind="addon"),
    ]
    monthly = sum(i.monthly_inr for i in items)
    return Quote(
        quote_id="Q-FIXTURE1", profile=profile(), items=items, addons_available=addons,
        ineligible=[
            Ineligible(product_id="P03", name="Biz Fibre 1G", reason_code="TIER",
                       reason=lt("Biz Fibre 1G is only sold in tier 1 cities. Kochi is tier 2.",
                                 "Biz Fibre 1G सिर्फ़ टियर 1 शहरों में मिलता है। कोच्चि टियर 2 है।")),
            Ineligible(product_id="P10", name="Managed SD-WAN", reason_code="SITES",
                       reason=lt("SD-WAN is for businesses with 3 or more sites.", "SD-WAN तीन या ज़्यादा जगहों वाले व्यवसायों के लिए है।")),
        ],
        monthly_total_inr=monthly, one_time_total_inr=sum(i.setup_inr for i in items),
        monthly_total_with_gst_inr=round(monthly * 1.18), contract_months=12,
        notices=[], valid_until=TODAY + timedelta(days=15),
    )


def advisor_reply() -> AdvisorReply:
    p = BusinessProfile(business_type="Dental clinic", segment="prof", city="Kochi", city_tier=2, state="Kerala", language="en")
    return AdvisorReply(
        session_id="S-FIXTURE1", reply_text="Thanks! How many people work at your clinic, including you?",
        quick_replies=["1–5", "6–20", "21–50", "More than 50"], profile=p,
        missing_fields=["employees", "sites", "has_gstin", "current_internet", "needs"], stage="asking", mode="rules",
    )


def advisor_reply_recommended() -> AdvisorReply:
    return AdvisorReply(
        session_id="S-FIXTURE1", reply_text="Here is a bundle that fits a 12-person clinic. You can switch extras on or off.",
        quick_replies=["Why this?", "Make it cheaper", "Talk to a person"], profile=profile(), missing_fields=[],
        stage="recommended", mode="rules", quote=quote(),
    )


def handoff_response() -> HandoffResponse:
    return HandoffResponse(handoff_id="H-FIXTURE1", message=lt(
        "A local Accel partner will call you within 2 working hours.",
        "Accel के स्थानीय पार्टनर 2 कामकाजी घंटों में आपको कॉल करेंगे।"))


def llm_status() -> LlmStatus:
    return LlmStatus(providers=[
        LlmProviderStatus(name="groq", configured=bool(settings.groq_api_key), model=settings.groq_model),
        LlmProviderStatus(name="gemini", configured=bool(settings.gemini_api_key), model=settings.gemini_model),
    ], active=None)


def consent_notice() -> ConsentNotice:
    return ConsentNotice(
        version="2026-07-v1",
        purposes=[
            ConsentPurpose(id="kyc_verification", required=True, text=lt(
                "Check my business documents for this order.", "इस ऑर्डर के लिए मेरे व्यवसाय के दस्तावेज़ जाँचें।")),
            ConsentPurpose(id="service_improvement", required=False, text=lt(
                "Use my anonymised details to improve the service.", "सेवा बेहतर करने के लिए मेरी पहचान हटाकर जानकारी का उपयोग करें।")),
        ],
        body=lt("We read your GST certificate, Udyam certificate, signatory ID and a recent utility bill only to verify "
                "this order. Photos are read in memory and never stored.",
                "हम आपका GST प्रमाणपत्र, उद्यम प्रमाणपत्र, हस्ताक्षरकर्ता की ID और हाल का बिल सिर्फ़ इस ऑर्डर की जाँच के लिए "
                "पढ़ते हैं। फ़ोटो सिर्फ़ मेमोरी में पढ़ी जाती हैं, सहेजी नहीं जातीं।"),
        retention=lt("Extracted details are kept for 180 days after activation, or 30 days if the order is rejected.",
                     "निकाली गई जानकारी चालू होने के 180 दिन बाद तक, या ऑर्डर अस्वीकार होने पर 30 दिन तक रखी जाती है।"),
    )


def consent_record() -> ConsentRecord:
    return ConsentRecord(consent_id="C-FIXTURE1", order_id="UD-260715-0001", version="2026-07-v1",
                         purposes_accepted=["kyc_verification"], created_at=NOW)


def _check(code, status, en, hi, fix_en=None, fix_hi=None, doc=None) -> Check:
    return Check(code=code, status=status, message=lt(en, hi), fix_hint=lt(fix_en, fix_hi) if fix_en else None, doc_type=doc)


def document_result() -> DocumentResult:
    return DocumentResult(
        doc_type="gst_certificate", detected_type="gst_certificate", readable=True,
        quality=DocQuality(blur_score=812.4, blurry=False, skew_deg=0.0),
        fields={"gstin": "32TT••••••••1ZW", "legal_name": "Balaji Dental Care LLP", "constitution": "Limited Liability Partnership"},
        issues=[],
    )


def kyc_checks() -> list[Check]:
    return [
        _check("GSTIN_ACTIVE", "PASS", "GSTIN is active in the GST registry.", "GSTIN, GST रजिस्ट्री में सक्रिय है।", doc="gst_certificate"),
        _check("NAME_MATCH", "PASS", "Business name matches the registry.", "व्यवसाय का नाम रजिस्ट्री से मेल खाता है।", doc="gst_certificate"),
        _check("ADDRESS_PROOF_RECENT", "FAIL", "Your utility bill is 257 days old. We need one from the last 90 days.",
               "आपका बिल 257 दिन पुराना है। हमें पिछले 90 दिनों का बिल चाहिए।",
               "Upload a bill dated after 16 April 2026.", "16 अप्रैल 2026 के बाद का बिल अपलोड करें।", doc="address_proof"),
    ]


def kyc_result() -> KycResult:
    return KycResult(order_id="UD-260715-0001", verdict="ACTION_REQUIRED", checks=kyc_checks(), gst_products_blocked=False, created_at=NOW)


def create_order_response() -> CreateOrderResponse:
    return CreateOrderResponse(order_id="UD-260715-0001", pin="4821")


def install_slots() -> SlotsResponse:
    start = TODAY + timedelta(days=1)
    days = [start + timedelta(days=i) for i in range(7) if (start + timedelta(days=i)).weekday() < 5][:5]
    return SlotsResponse(slots=[InstallSlot(date=d, window=w) for d in days for w in ("10-13", "14-18")])


def order(order_id: str = "UD-260715-0001") -> Order:
    q = quote()
    eta = TODAY + timedelta(days=6)
    return Order(
        order_id=order_id, status="KYC_PENDING", contact_name="Anita Shah", phone_masked="••••••3210", items=q.items,
        totals=OrderTotals(monthly_inr=q.monthly_total_inr, one_time_inr=q.one_time_total_inr,
                           monthly_with_gst_inr=q.monthly_total_with_gst_inr, contract_months=q.contract_months),
        timeline=[
            TimelineStep(key="ordered", label=lt("Order placed", "ऑर्डर हो गया"), state="done", date=TODAY),
            TimelineStep(key="kyc", label=lt("Documents checked", "दस्तावेज़ जाँचे गए"), state="current"),
            TimelineStep(key="install_scheduled", label=lt("Installation booked", "इंस्टॉलेशन बुक"), state="upcoming"),
            TimelineStep(key="installing", label=lt("Engineer on site", "इंजीनियर साइट पर"), state="upcoming"),
            TimelineStep(key="active", label=lt("Services live", "सेवाएँ चालू"), state="upcoming", eta=eta),
        ],
        item_etas=[ItemEta(product_id=i.product_id, name=i.name, eta=TODAY + timedelta(days=1 + i.install_days)) for i in q.items],
        eta_activation_date=eta, install_slot=None,
        events=[OrderEvent(ts=NOW, status="KYC_PENDING", text=lt("We received your order.", "हमें आपका ऑर्डर मिल गया।"))],
        next_action=lt("Upload your business documents to continue.", "आगे बढ़ने के लिए अपने व्यवसाय के दस्तावेज़ अपलोड करें।"),
        created_at=NOW,
    )


def leads_page() -> LeadsPage:
    return LeadsPage(total=2, items=[
        LeadRow(lead_id="L00001", business_name="Balaji Dental Care LLP", segment="prof", city="Kochi", city_tier=2,
                source="Field sales", preferred_language="Malayalam", stage_reached="KYC complete",
                drop_reason="Installation delayed beyond 21 days", score=0.31, band="HOT",
                top_factors=["has a GSTIN", "professional office"], suggested_channel="PARTNER"),
        LeadRow(lead_id="L00004", business_name="Zenith Diagnostics", segment="prof", city="Nagpur", city_tier=2,
                source="Channel partner", preferred_language="Hindi", stage_reached="Needs assessed",
                drop_reason="Decided to wait", score=0.12, band="WARM",
                top_factors=["has a GSTIN", "came through a channel partner"], suggested_channel="INSIDE_SALES"),
    ])


def handoff_rows() -> list[HandoffRow]:
    return [HandoffRow(handoff_id="H-FIXTURE1", session_id="S-FIXTURE1", reason="Asked to talk to a person",
                       status="open", created_at=NOW, profile=advisor_reply().profile)]


def kyc_review_rows() -> list[KycReviewRow]:
    return [KycReviewRow(order_id="UD-260715-0001", verdict="ACTION_REQUIRED",
                         failing_checks=[c for c in kyc_checks() if c.status != "PASS"], created_at=NOW)]


def order_rows() -> list[OrderRow]:
    q = quote()
    return [OrderRow(order_id="UD-260715-0001", status="KYC_PENDING", contact_name="Anita Shah",
                     phone_masked="••••••3210", monthly_total_inr=q.monthly_total_inr, created_at=NOW)]


def model_report() -> ModelReport:
    return ModelReport(
        auc_time_split=0.70, top_decile_lift=2.1, top20_capture=0.38, train_rows=3300, test_rows=1700,
        coefficients=[ModelCoefficient(feature="lead_source=Referral", weight=1.21),
                      ModelCoefficient(feature="has_gstin=Y", weight=1.05),
                      ModelCoefficient(feature="lead_source=WhatsApp campaign", weight=-0.84)],
        caveat=lt("This ranks who is likely to activate, not who activates because we call.",
                  "यह बताता है कि कौन चालू होने की संभावना रखता है, यह नहीं कि कॉल करने से कौन चालू होगा।"),
    )


def funnel_report() -> FunnelReport:
    return FunnelReport(
        baseline=[FunnelStage(stage=s, count=n) for s, n in [
            ("Lead", 5000), ("Contacted", 3406), ("Needs assessed", 1974), ("Quote accepted", 861),
            ("KYC complete", 588), ("Activated", 368)]],
        live={"KYC_PENDING": 1},
    )


def meta() -> Meta:
    from .data import SAMPLE_APPLICANTS
    return Meta(demo_mode=settings.demo_mode, today=TODAY, sample_applicants=SAMPLE_APPLICANTS, version="0.1.0")


def all_fixtures() -> dict[str, object]:
    """name -> fixture object, for scripts/export_fixtures.py."""
    return {
        "profile": profile(), "quote": quote(), "advisor_reply": advisor_reply(),
        "advisor_reply_recommended": advisor_reply_recommended(), "handoff_response": handoff_response(),
        "llm_status": llm_status(), "consent_notice": consent_notice(), "consent_record": consent_record(),
        "document_result": document_result(), "kyc_result": kyc_result(), "create_order_response": create_order_response(),
        "install_slots": install_slots(), "order": order(), "leads_page": leads_page(), "handoff_rows": handoff_rows(),
        "kyc_review_rows": kyc_review_rows(), "order_rows": order_rows(), "model_report": model_report(),
        "funnel_report": funnel_report(), "meta": meta(),
    }
