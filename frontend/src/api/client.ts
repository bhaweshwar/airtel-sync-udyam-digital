// Typed API client for every endpoint. Phase 0 owns this file; workstreams call `api.*` and never use fetch directly.
// With VITE_MOCK=1 (`npm run mock`) every call returns the fixture JSON exported from the backend, so pages can be
// built before their backend exists.
import type {
  AdvisorMessageRequest, AdvisorReply, BookSlotRequest, ConsentNotice, ConsentRecord, ConsentRequest,
  CreateOrderRequest, CreateOrderResponse, DocType, DocumentResult, FunnelReport, GstinLookup, HandoffRequest,
  HandoffResponse, HandoffRow, KycResult, KycReviewRow, LeadsPage, LeadsQuery, LlmStatus, Meta, ModelReport, Order,
  OrderRow, Product, Quote, QuoteRequest, RecommendRequest, SlotsResponse, UdyamLookup, BusinessProfile,
} from "./types";

import fxAdvisorReply from "./fixtures/advisor_reply.json";
import fxAdvisorReplyRecommended from "./fixtures/advisor_reply_recommended.json";
import fxConsentNotice from "./fixtures/consent_notice.json";
import fxConsentRecord from "./fixtures/consent_record.json";
import fxCreateOrder from "./fixtures/create_order_response.json";
import fxDocumentResult from "./fixtures/document_result.json";
import fxFunnel from "./fixtures/funnel_report.json";
import fxHandoff from "./fixtures/handoff_response.json";
import fxHandoffRows from "./fixtures/handoff_rows.json";
import fxSlots from "./fixtures/install_slots.json";
import fxKycResult from "./fixtures/kyc_result.json";
import fxKycReviews from "./fixtures/kyc_review_rows.json";
import fxLeads from "./fixtures/leads_page.json";
import fxLlmStatus from "./fixtures/llm_status.json";
import fxMeta from "./fixtures/meta.json";
import fxModel from "./fixtures/model_report.json";
import fxOrder from "./fixtures/order.json";
import fxOrderRows from "./fixtures/order_rows.json";
import fxQuote from "./fixtures/quote.json";

export const MOCK = import.meta.env.VITE_MOCK === "1";

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

type Json = Record<string, unknown> | unknown[];

async function request<T>(method: string, path: string, opts: { body?: Json | FormData; headers?: Record<string, string>; query?: Record<string, string | number | undefined | null> } = {}): Promise<T> {
  const url = new URL(path, window.location.origin);
  for (const [k, v] of Object.entries(opts.query ?? {})) if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
  const headers: Record<string, string> = { ...(opts.headers ?? {}) };
  let body: BodyInit | undefined;
  if (opts.body instanceof FormData) body = opts.body;
  else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  let res: Response;
  try {
    res = await fetch(url.pathname + url.search, { method, headers, body });
  } catch {
    throw new ApiError(0, "NETWORK", "Can't reach the server. Check your connection and try again.");
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = data?.detail;
    if (detail && typeof detail === "object" && "code" in detail) throw new ApiError(res.status, detail.code, detail.message);
    throw new ApiError(res.status, "HTTP_" + res.status, typeof detail === "string" ? detail : "Something went wrong. Please try again.");
  }
  return data as T;
}

function mock<T>(value: unknown, patch: Record<string, unknown> = {}): Promise<T> {
  const copy = structuredClone(value) as Record<string, unknown>;
  return new Promise((resolve) => setTimeout(() => resolve({ ...copy, ...patch } as T), 250));
}

function mockList<T>(value: unknown): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(structuredClone(value) as T), 250));
}

const bo = (key: string) => ({ "X-Backoffice-Key": key });

export const api = {
  meta: (): Promise<Meta> => (MOCK ? mock(fxMeta) : request("GET", "/api/meta")),

  // catalogue + quote (WS1)
  catalogue: (): Promise<Product[]> => (MOCK ? mockList([]) : request("GET", "/api/catalogue")),
  recommend: (req: RecommendRequest): Promise<Quote> =>
    MOCK ? mock(fxQuote, { profile: req.profile }) : request("POST", "/api/recommend", { body: req as unknown as Json }),
  quote: (req: QuoteRequest): Promise<Quote> =>
    MOCK ? mock(fxQuote, { profile: req.profile }) : request("POST", "/api/quote", { body: req as unknown as Json }),

  // advisor (WS2)
  advisorMessage: (req: AdvisorMessageRequest): Promise<AdvisorReply> =>
    MOCK
      ? mock(/recommend/i.test(req.text) ? fxAdvisorReplyRecommended : fxAdvisorReply, { session_id: req.session_id ?? "S-FIXTURE1" })
      : request("POST", "/api/advisor/message", { body: req as unknown as Json }),
  handoff: (req: HandoffRequest): Promise<HandoffResponse> =>
    MOCK ? mock(fxHandoff) : request("POST", "/api/advisor/handoff", { body: req as unknown as Json }),
  llmStatus: (): Promise<LlmStatus> => (MOCK ? mock(fxLlmStatus) : request("GET", "/api/llm-status")),

  // registry (Phase 0)
  gstin: (gstin: string): Promise<GstinLookup> =>
    MOCK ? mock({ gstin, format_valid: true, checksum_valid: true, found: false }) : request("GET", `/api/registry/gstin/${encodeURIComponent(gstin)}`),
  udyam: (udyam: string): Promise<UdyamLookup> =>
    MOCK ? mock({ udyam_number: udyam, format_valid: true, found: false }) : request("GET", `/api/registry/udyam/${encodeURIComponent(udyam)}`),

  // KYC (WS3)
  kycNotice: (): Promise<ConsentNotice> => (MOCK ? mock(fxConsentNotice) : request("GET", "/api/kyc/notice")),
  giveConsent: (orderId: string, req: ConsentRequest): Promise<ConsentRecord> =>
    MOCK ? mock(fxConsentRecord, { order_id: orderId, purposes_accepted: req.purposes_accepted })
      : request("POST", `/api/kyc/${orderId}/consent`, { body: req as unknown as Json }),
  withdrawConsent: (orderId: string): Promise<void> =>
    MOCK ? Promise.resolve() : request("DELETE", `/api/kyc/${orderId}/consent`),
  uploadDocument: (orderId: string, docType: DocType, file: File): Promise<DocumentResult> => {
    if (MOCK) return mock(fxDocumentResult, { doc_type: docType });
    const form = new FormData();
    form.append("doc_type", docType);
    form.append("file", file);
    return request("POST", `/api/kyc/${orderId}/documents`, { body: form });
  },
  submitKyc: (orderId: string): Promise<KycResult> =>
    MOCK ? mock(fxKycResult, { order_id: orderId }) : request("POST", `/api/kyc/${orderId}/submit`),
  kycSample: (orderId: string, applicantId: string): Promise<KycResult> =>
    MOCK ? mock(fxKycResult, { order_id: orderId }) : request("POST", `/api/kyc/${orderId}/sample/${applicantId}`),

  // orders + tracker (WS4)
  createOrder: (req: CreateOrderRequest): Promise<CreateOrderResponse> =>
    MOCK ? mock(fxCreateOrder) : request("POST", "/api/orders", { body: req as unknown as Json }),
  getOrder: (orderId: string, pin: string): Promise<Order> =>
    MOCK ? mock(fxOrder, { order_id: orderId }) : request("GET", `/api/orders/${orderId}`, { query: { pin } }),
  getSlots: (orderId: string, pin: string): Promise<SlotsResponse> =>
    MOCK ? mock(fxSlots) : request("GET", `/api/orders/${orderId}/slots`, { query: { pin } }),
  bookSlot: (orderId: string, req: BookSlotRequest): Promise<Order> =>
    MOCK ? mock(fxOrder, { order_id: orderId, status: "INSTALL_SCHEDULED", install_slot: { date: req.date, window: req.window } })
      : request("POST", `/api/orders/${orderId}/slots`, { body: req as unknown as Json }),
  advanceOrder: (orderId: string, auth: { pin?: string; backofficeKey?: string }): Promise<Order> =>
    MOCK ? mock(fxOrder, { order_id: orderId })
      : request("POST", `/api/orders/${orderId}/advance`, { query: { pin: auth.pin }, headers: auth.backofficeKey ? bo(auth.backofficeKey) : {} }),

  // back office (WS5)
  backoffice: {
    leads: (key: string, q: LeadsQuery = {}): Promise<LeadsPage> =>
      MOCK ? mock(fxLeads) : request("GET", "/api/backoffice/leads", { headers: bo(key), query: { ...q } }),
    handoffs: (key: string): Promise<HandoffRow[]> => (MOCK ? mockList(fxHandoffRows) : request("GET", "/api/backoffice/handoffs", { headers: bo(key) })),
    kycReviews: (key: string): Promise<KycReviewRow[]> => (MOCK ? mockList(fxKycReviews) : request("GET", "/api/backoffice/kyc-reviews", { headers: bo(key) })),
    orders: (key: string): Promise<OrderRow[]> => (MOCK ? mockList(fxOrderRows) : request("GET", "/api/backoffice/orders", { headers: bo(key) })),
    model: (key: string): Promise<ModelReport> => (MOCK ? mock(fxModel) : request("GET", "/api/backoffice/model", { headers: bo(key) })),
    funnel: (key: string): Promise<FunnelReport> => (MOCK ? mock(fxFunnel) : request("GET", "/api/backoffice/funnel", { headers: bo(key) })),
  },
};

export function emptyProfile(language: BusinessProfile["language"] = "en"): BusinessProfile {
  return { needs: [], language };
}
