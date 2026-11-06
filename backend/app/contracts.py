"""Shared API contracts (Pydantic). Phase 0 owns this file; workstreams must not edit it.

Mirrored by hand in frontend/src/api/types.ts and documented in docs/CONTRACTS.md.
Conventions:
- Money is whole rupees (int). Dates are ISO dates; timestamps are ISO datetimes (UTC).
- Every user-facing string produced by the server is a LocalText {en, hi}, except advisor
  reply_text / quick_replies, which are already in the conversation's language.
- Identifiers (GSTIN, Udyam, ID numbers, phone) are masked in every response except the
  registry lookups, which echo what the owner typed.
"""
from __future__ import annotations

from datetime import date, datetime
from datetime import date as Date  # for fields that are themselves named `date`
from typing import Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------- shared types

Segment = Literal["micro", "prof", "multi", "mfg"]
Language = Literal["en", "hi"]
CurrentInternet = Literal["none", "mobile_hotspot", "home_broadband", "business_broadband", "mixed", "leased_line"]
Need = Literal[
    "internet", "backup", "payments_pos", "whatsapp", "sms", "email", "cloud_backup", "website",
    "security", "wifi", "cctv", "telephony", "tollfree", "iot", "fleet", "static_ip", "sdwan",
]


class LocalText(BaseModel):
    en: str
    hi: str


class ApiErrorBody(BaseModel):
    """Shape of `detail` in every 4xx/5xx raised by the app: HTTPException(status, detail={code, message})."""
    code: str
    message: str


# ---------------------------------------------------------------- catalogue

class Product(BaseModel):
    product_id: str
    category: str
    name: str
    description: str
    unit: str
    price_min_inr: int
    price_max_inr: int
    setup_inr: int
    min_contract_months: int
    city_tiers: list[int]
    min_employees: int
    min_sites: int
    requires_gstin: bool
    requires_one_of: list[str]
    install_days: int
    target_segments: list[Segment]


# ---------------------------------------------------------------- profile + quote (WS1)

class BusinessProfile(BaseModel):
    business_type: Optional[str] = None
    segment: Optional[Segment] = None
    city: Optional[str] = None
    city_tier: Optional[Literal[1, 2, 3]] = None  # 3 = not served by any product -> advisor hands off
    state: Optional[str] = None
    employees: Optional[int] = Field(default=None, ge=1)
    sites: Optional[int] = Field(default=None, ge=1)
    has_gstin: Optional[bool] = None
    gstin: Optional[str] = None
    gstin_status: Optional[Literal["Active", "Cancelled", "Suspended"]] = None  # set from a registry lookup
    current_internet: Optional[CurrentInternet] = None
    needs: list[Need] = Field(default_factory=list)
    budget_monthly_inr: Optional[int] = Field(default=None, ge=0)
    language: Language = "en"


class LineItem(BaseModel):
    product_id: str
    name: str
    category: str
    unit: str
    quantity: int = Field(ge=1)
    unit_price_inr: int
    monthly_inr: int
    setup_inr: int
    contract_months: int
    install_days: int
    reason: LocalText
    kind: Literal["core", "addon"]


class Ineligible(BaseModel):
    product_id: str
    name: str
    reason_code: Literal["TIER", "EMPLOYEES", "SITES", "GSTIN", "DEPENDENCY"]
    reason: LocalText


class Quote(BaseModel):
    quote_id: str
    profile: BusinessProfile
    items: list[LineItem]
    addons_available: list[LineItem]
    ineligible: list[Ineligible]
    monthly_total_inr: int
    one_time_total_inr: int
    gst_rate: float = 0.18
    monthly_total_with_gst_inr: int
    contract_months: int
    notices: list[LocalText] = Field(default_factory=list)
    valid_until: date
    gst_products_blocked: bool = False


class SelectedItem(BaseModel):
    product_id: str
    quantity: int = Field(ge=1)


class RecommendRequest(BaseModel):
    profile: BusinessProfile


class QuoteRequest(BaseModel):
    profile: BusinessProfile
    selected: list[SelectedItem]
    quote_id: Optional[str] = None  # previous quote being edited; a new quote_id is always returned


# ---------------------------------------------------------------- advisor (WS2)

class AdvisorMessageRequest(BaseModel):
    session_id: Optional[str] = None
    text: str = Field(min_length=1, max_length=2000)
    language: Optional[Language] = None


class AdvisorReply(BaseModel):
    session_id: str
    reply_text: str
    quick_replies: list[str] = Field(default_factory=list)
    profile: BusinessProfile
    missing_fields: list[str] = Field(default_factory=list)
    stage: Literal["asking", "recommended", "handoff"]
    mode: Literal["llm", "rules"]
    quote: Optional[Quote] = None


class HandoffRequest(BaseModel):
    session_id: str
    reason: str = Field(max_length=500)
    phone: Optional[str] = None


class HandoffResponse(BaseModel):
    handoff_id: str
    message: LocalText


class LlmProviderStatus(BaseModel):
    name: str
    configured: bool
    ok: Optional[bool] = None
    model: str
    error: Optional[str] = None


class LlmStatus(BaseModel):
    providers: list[LlmProviderStatus]
    active: Optional[str] = None  # first provider that answered, or None -> rules mode


# ---------------------------------------------------------------- registry (Phase 0)

GstStatus = Literal["Active", "Cancelled", "Suspended"]


class GstinLookup(BaseModel):
    gstin: str
    format_valid: bool
    checksum_valid: bool
    found: bool
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    constitution: Optional[str] = None
    address: Optional[str] = None
    state: Optional[str] = None
    registration_date: Optional[date] = None
    status: Optional[GstStatus] = None


class UdyamLookup(BaseModel):
    udyam_number: str
    format_valid: bool
    found: bool
    enterprise_name: Optional[str] = None
    enterprise_type: Optional[str] = None
    major_activity: Optional[str] = None
    nic_description: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    date_of_registration: Optional[date] = None


# ---------------------------------------------------------------- KYC (WS3)

DocType = Literal["gst_certificate", "udyam_certificate", "signatory_id", "address_proof"]
KycVerdict = Literal["VERIFIED", "ACTION_REQUIRED", "MANUAL_REVIEW", "REJECTED"]


class ConsentPurpose(BaseModel):
    id: str
    required: bool
    text: LocalText


class ConsentNotice(BaseModel):
    version: str
    purposes: list[ConsentPurpose]
    body: LocalText  # full notice: what is collected, why, who sees it, how to withdraw
    retention: LocalText


class ConsentRequest(BaseModel):
    version: str
    purposes_accepted: list[str]


class ConsentRecord(BaseModel):
    consent_id: str
    order_id: str
    version: str
    purposes_accepted: list[str]
    created_at: datetime


class DocQuality(BaseModel):
    blur_score: float
    blurry: bool
    skew_deg: float = 0.0


class Check(BaseModel):
    code: str
    status: Literal["PASS", "WARN", "FAIL"]
    message: LocalText
    fix_hint: Optional[LocalText] = None
    doc_type: Optional[DocType] = None


class DocumentResult(BaseModel):
    doc_type: DocType
    detected_type: Optional[DocType] = None
    readable: bool
    quality: DocQuality
    fields: dict[str, str] = Field(default_factory=dict)  # masked values
    issues: list[Check] = Field(default_factory=list)


class KycResult(BaseModel):
    order_id: str
    verdict: KycVerdict
    checks: list[Check]
    gst_products_blocked: bool = False
    created_at: datetime


# ---------------------------------------------------------------- orders + tracker (WS4)

OrderStatus = Literal[
    "QUOTE_ACCEPTED", "KYC_PENDING", "KYC_ACTION_REQUIRED", "KYC_REVIEW", "KYC_VERIFIED",
    "INSTALL_SCHEDULED", "INSTALLING", "ACTIVE", "REJECTED",
]


class CreateOrderRequest(BaseModel):
    quote_id: str
    contact_name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=10, max_length=15)


class CreateOrderResponse(BaseModel):
    order_id: str
    pin: str  # shown to the owner once; only a hash is stored


class TimelineStep(BaseModel):
    key: str
    label: LocalText
    state: Literal["done", "current", "upcoming", "blocked"]
    date: Optional[Date] = None
    eta: Optional[Date] = None


class OrderEvent(BaseModel):
    ts: datetime
    status: OrderStatus
    text: LocalText


class InstallSlot(BaseModel):
    date: Date
    window: Literal["10-13", "14-18"]


class ItemEta(BaseModel):
    product_id: str
    name: str
    eta: Optional[date] = None


class OrderTotals(BaseModel):
    monthly_inr: int
    one_time_inr: int
    monthly_with_gst_inr: int
    contract_months: int


class Order(BaseModel):
    order_id: str
    status: OrderStatus
    contact_name: str
    phone_masked: str
    items: list[LineItem]
    totals: OrderTotals
    timeline: list[TimelineStep]
    item_etas: list[ItemEta] = Field(default_factory=list)
    eta_activation_date: Optional[date] = None
    install_slot: Optional[InstallSlot] = None
    events: list[OrderEvent] = Field(default_factory=list)
    next_action: Optional[LocalText] = None
    created_at: datetime


class SlotsResponse(BaseModel):
    slots: list[InstallSlot]


class BookSlotRequest(BaseModel):
    pin: str
    date: Date
    window: Literal["10-13", "14-18"]


# ---------------------------------------------------------------- back office (WS5)

LeadBand = Literal["HOT", "WARM", "COLD"]
Channel = Literal["FIELD", "PARTNER", "INSIDE_SALES", "SELF_SERVE_LINK"]


class LeadRow(BaseModel):
    lead_id: str
    business_name: str
    segment: Segment
    city: str
    city_tier: int
    source: str
    preferred_language: str
    stage_reached: str
    drop_reason: Optional[str] = None
    score: float = Field(ge=0, le=1)
    band: LeadBand
    top_factors: list[str]
    suggested_channel: Channel


class LeadsPage(BaseModel):
    total: int
    items: list[LeadRow]


class HandoffRow(BaseModel):
    handoff_id: str
    session_id: str
    reason: str
    status: str
    created_at: datetime
    profile: Optional[BusinessProfile] = None
    phone_masked: Optional[str] = None  # call-back number, if the owner left one


class KycReviewRow(BaseModel):
    order_id: str
    verdict: KycVerdict
    failing_checks: list[Check]
    created_at: datetime


class KycDecisionRequest(BaseModel):
    """A staff decision on an order whose KYC needs a person (status KYC_REVIEW)."""
    decision: Literal["approve", "reject"]


class KycDecisionResponse(BaseModel):
    order_id: str
    status: OrderStatus


class OrderRow(BaseModel):
    order_id: str
    status: OrderStatus
    contact_name: str
    phone_masked: str
    monthly_total_inr: int
    created_at: datetime


class ModelCoefficient(BaseModel):
    feature: str
    weight: float


class ModelReport(BaseModel):
    auc_time_split: float
    top_decile_lift: float
    top20_capture: float
    train_rows: int
    test_rows: int
    coefficients: list[ModelCoefficient]
    caveat: LocalText


class FunnelStage(BaseModel):
    stage: str
    count: int


class FunnelReport(BaseModel):
    baseline: list[FunnelStage]
    live: dict[str, int]  # OrderStatus -> count of live orders


# ---------------------------------------------------------------- meta (Phase 0)

class Meta(BaseModel):
    demo_mode: bool
    today: date
    sample_applicants: list[str]
    version: str
