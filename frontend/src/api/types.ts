// Hand-written mirror of backend/app/contracts.py. Phase 0 owns this file; workstreams must not edit it.
// Money is whole rupees. Dates are "YYYY-MM-DD" strings; timestamps are ISO datetime strings.

export type Segment = "micro" | "prof" | "multi" | "mfg";
export type Language = "en" | "hi";
export type CurrentInternet = "none" | "mobile_hotspot" | "home_broadband" | "business_broadband" | "mixed" | "leased_line";
export type Need =
  | "internet" | "backup" | "payments_pos" | "whatsapp" | "sms" | "email" | "cloud_backup" | "website"
  | "security" | "wifi" | "cctv" | "telephony" | "tollfree" | "iot" | "fleet" | "static_ip" | "sdwan";

export interface LocalText { en: string; hi: string }
export interface ApiErrorBody { code: string; message: string }

// ---------------------------------------------------------------- catalogue
export interface Product {
  product_id: string;
  category: string;
  name: string;
  description: string;
  unit: string;
  price_min_inr: number;
  price_max_inr: number;
  setup_inr: number;
  min_contract_months: number;
  city_tiers: number[];
  min_employees: number;
  min_sites: number;
  requires_gstin: boolean;
  requires_one_of: string[];
  install_days: number;
  target_segments: Segment[];
}

// ---------------------------------------------------------------- profile + quote (WS1)
export type GstStatus = "Active" | "Cancelled" | "Suspended";

export interface BusinessProfile {
  business_type?: string | null;
  segment?: Segment | null;
  city?: string | null;
  city_tier?: 1 | 2 | 3 | null; // 3 = not served -> advisor hands off
  state?: string | null;
  employees?: number | null;
  sites?: number | null;
  has_gstin?: boolean | null;
  gstin?: string | null;
  gstin_status?: GstStatus | null;
  current_internet?: CurrentInternet | null;
  needs: Need[];
  budget_monthly_inr?: number | null;
  language: Language;
}

export interface LineItem {
  product_id: string;
  name: string;
  category: string;
  unit: string;
  quantity: number;
  unit_price_inr: number;
  monthly_inr: number;
  setup_inr: number;
  contract_months: number;
  install_days: number;
  reason: LocalText;
  kind: "core" | "addon";
}

export interface Ineligible {
  product_id: string;
  name: string;
  reason_code: "TIER" | "EMPLOYEES" | "SITES" | "GSTIN" | "DEPENDENCY";
  reason: LocalText;
}

export interface Quote {
  quote_id: string;
  profile: BusinessProfile;
  items: LineItem[];
  addons_available: LineItem[];
  ineligible: Ineligible[];
  monthly_total_inr: number;
  one_time_total_inr: number;
  gst_rate: number;
  monthly_total_with_gst_inr: number;
  contract_months: number;
  notices: LocalText[];
  valid_until: string;
  gst_products_blocked: boolean;
}

export interface SelectedItem { product_id: string; quantity: number }
export interface RecommendRequest { profile: BusinessProfile }
export interface QuoteRequest { profile: BusinessProfile; selected: SelectedItem[]; quote_id?: string | null }

// ---------------------------------------------------------------- advisor (WS2)
export interface AdvisorMessageRequest { session_id?: string | null; text: string; language?: Language | null }

export interface AdvisorReply {
  session_id: string;
  reply_text: string;
  quick_replies: string[];
  profile: BusinessProfile;
  missing_fields: string[];
  stage: "asking" | "recommended" | "handoff";
  mode: "llm" | "rules";
  quote?: Quote | null;
}

export interface HandoffRequest { session_id: string; reason: string; phone?: string | null }
export interface HandoffResponse { handoff_id: string; message: LocalText }

export interface LlmProviderStatus { name: string; configured: boolean; ok?: boolean | null; model: string; error?: string | null }
export interface LlmStatus { providers: LlmProviderStatus[]; active?: string | null }

// ---------------------------------------------------------------- registry (Phase 0)
export interface GstinLookup {
  gstin: string;
  format_valid: boolean;
  checksum_valid: boolean;
  found: boolean;
  legal_name?: string | null;
  trade_name?: string | null;
  constitution?: string | null;
  address?: string | null;
  state?: string | null;
  registration_date?: string | null;
  status?: GstStatus | null;
}

export interface UdyamLookup {
  udyam_number: string;
  format_valid: boolean;
  found: boolean;
  enterprise_name?: string | null;
  enterprise_type?: string | null;
  major_activity?: string | null;
  nic_description?: string | null;
  state?: string | null;
  city?: string | null;
  date_of_registration?: string | null;
}

// ---------------------------------------------------------------- KYC (WS3)
export type DocType = "gst_certificate" | "udyam_certificate" | "signatory_id" | "address_proof";
export type KycVerdict = "VERIFIED" | "ACTION_REQUIRED" | "MANUAL_REVIEW" | "REJECTED";

export interface ConsentPurpose { id: string; required: boolean; text: LocalText }
export interface ConsentNotice { version: string; purposes: ConsentPurpose[]; body: LocalText; retention: LocalText }
export interface ConsentRequest { version: string; purposes_accepted: string[] }
export interface ConsentRecord { consent_id: string; order_id: string; version: string; purposes_accepted: string[]; created_at: string }

export interface DocQuality { blur_score: number; blurry: boolean; skew_deg: number }

export interface Check {
  code: string;
  status: "PASS" | "WARN" | "FAIL";
  message: LocalText;
  fix_hint?: LocalText | null;
  doc_type?: DocType | null;
}

export interface DocumentResult {
  doc_type: DocType;
  detected_type?: DocType | null;
  readable: boolean;
  quality: DocQuality;
  fields: Record<string, string>; // masked values
  issues: Check[];
}

export interface KycResult { order_id: string; verdict: KycVerdict; checks: Check[]; gst_products_blocked: boolean; created_at: string }

// ---------------------------------------------------------------- orders + tracker (WS4)
export type OrderStatus =
  | "QUOTE_ACCEPTED" | "KYC_PENDING" | "KYC_ACTION_REQUIRED" | "KYC_REVIEW" | "KYC_VERIFIED"
  | "INSTALL_SCHEDULED" | "INSTALLING" | "ACTIVE" | "REJECTED";

export interface CreateOrderRequest { quote_id: string; contact_name: string; phone: string }
export interface CreateOrderResponse { order_id: string; pin: string }

export interface TimelineStep {
  key: string;
  label: LocalText;
  state: "done" | "current" | "upcoming" | "blocked";
  date?: string | null;
  eta?: string | null;
}

export interface OrderEvent { ts: string; status: OrderStatus; text: LocalText }
export type SlotWindow = "10-13" | "14-18";
export interface InstallSlot { date: string; window: SlotWindow }
export interface ItemEta { product_id: string; name: string; eta?: string | null }
export interface OrderTotals { monthly_inr: number; one_time_inr: number; monthly_with_gst_inr: number; contract_months: number }

export interface Order {
  order_id: string;
  status: OrderStatus;
  contact_name: string;
  phone_masked: string;
  items: LineItem[];
  totals: OrderTotals;
  timeline: TimelineStep[];
  item_etas: ItemEta[];
  eta_activation_date?: string | null;
  install_slot?: InstallSlot | null;
  events: OrderEvent[];
  next_action?: LocalText | null;
  created_at: string;
}

export interface SlotsResponse { slots: InstallSlot[] }
export interface BookSlotRequest { pin: string; date: string; window: SlotWindow }

// ---------------------------------------------------------------- back office (WS5)
export type LeadBand = "HOT" | "WARM" | "COLD";
export type Channel = "FIELD" | "PARTNER" | "INSIDE_SALES" | "SELF_SERVE_LINK";

export interface LeadRow {
  lead_id: string;
  business_name: string;
  segment: Segment;
  city: string;
  city_tier: number;
  source: string;
  preferred_language: string;
  stage_reached: string;
  drop_reason?: string | null;
  score: number;
  band: LeadBand;
  top_factors: string[];
  suggested_channel: Channel;
}

export interface LeadsPage { total: number; items: LeadRow[] }
export interface LeadsQuery { limit?: number; offset?: number; channel?: Channel; segment?: Segment }

export interface HandoffRow { handoff_id: string; session_id: string; reason: string; status: string; created_at: string; profile?: BusinessProfile | null; phone_masked?: string | null }
export interface KycReviewRow { order_id: string; verdict: KycVerdict; failing_checks: Check[]; created_at: string }
export interface OrderRow { order_id: string; status: OrderStatus; contact_name: string; phone_masked: string; monthly_total_inr: number; created_at: string }

export interface ModelCoefficient { feature: string; weight: number }
export interface ModelReport {
  auc_time_split: number;
  top_decile_lift: number;
  top20_capture: number;
  train_rows: number;
  test_rows: number;
  coefficients: ModelCoefficient[];
  caveat: LocalText;
}

export interface FunnelStage { stage: string; count: number }
export interface FunnelReport { baseline: FunnelStage[]; live: Record<string, number> }

// ---------------------------------------------------------------- meta (Phase 0)
export interface Meta { demo_mode: boolean; today: string; sample_applicants: string[]; version: string }
