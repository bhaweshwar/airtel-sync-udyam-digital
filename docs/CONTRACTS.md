# Contracts

The shared API, models and file ownership for the six parallel workstreams. Phase 0 owns this document, `backend/app/contracts.py` and `frontend/src/api/types.ts`. If any of them disagree, `contracts.py` wins.

Need a change? Append it to [CHANGE_REQUESTS.md](CHANGE_REQUESTS.md). Don't edit shared files from a workstream branch.

## Conventions

- **Money** is whole rupees (`int`).
- **Dates and times:** dates are `YYYY-MM-DD`; timestamps are ISO-8601 UTC.
- **"Today"** is `settings.today`, which defaults to `2026-07-15`, the reference date of the case data. Never call `date.today()`.
- **User-facing server text** is a `LocalText {en, hi}`. The frontend picks one with `useT().lt(text)`.
  - Exception: advisor `reply_text` and `quick_replies` are already in the conversation's language.
- **Errors:** `HTTPException(status, detail={"code": "SOME_CODE", "message": "Plain sentence."})`. The client raises `ApiError(status, code, message)`.
- **Identifiers** (GSTIN, Udyam, ID number, phone) are masked in every response and log line.
  - Use `app.common.mask`.
  - The registry lookups are the only exception: they echo what the owner typed.
  - Uvicorn access logs are masked automatically (`RedactFilter` in `main.py`).
- **Demo-only behaviour** (sample applicants, "advance order") must check `settings.demo_mode`. The frontend reads it from `useMeta().demo_mode`.
- **Nothing calls an LLM in tests.** `conftest.py` blanks the API keys.

## Shared models (`backend/app/contracts.py`)

| Model | Key fields |
|---|---|
| `BusinessProfile` | `business_type`, `segment` (micro/prof/multi/mfg), `city`, `city_tier` (1, 2, or 3 = not served), `state`, `employees`, `sites`, `has_gstin`, `gstin`, `gstin_status` (from a lookup), `current_internet` (none/mobile_hotspot/home_broadband/business_broadband/mixed/leased_line), `needs[]`, `budget_monthly_inr`, `language` (en/hi). All optional except `needs` (default `[]`) and `language` (default `en`) |
| `Product` | One catalogue row, typed: `city_tiers[]`, `requires_one_of[]`, `install_days`, `target_segments[]` |
| `LineItem` | `product_id, name, category, unit, quantity, unit_price_inr, monthly_inr, setup_inr, contract_months, install_days, reason: LocalText, kind: core/addon` |
| `Ineligible` | `product_id, name, reason_code` (TIER/EMPLOYEES/SITES/GSTIN/DEPENDENCY), `reason: LocalText` |
| `Quote` | `quote_id, profile, items[], addons_available[], ineligible[], monthly_total_inr, one_time_total_inr, gst_rate (0.18), monthly_total_with_gst_inr, contract_months, notices: LocalText[], valid_until, gst_products_blocked` |
| `AdvisorReply` | `session_id, reply_text, quick_replies[], profile, missing_fields[], stage` (asking/recommended/handoff), `mode` (llm/rules), `quote?` |
| `GstinLookup` | `gstin, format_valid, checksum_valid, found`, plus registry fields: `legal_name, trade_name, constitution, address, state, registration_date, status` (Active/Cancelled/Suspended) |
| `UdyamLookup` | `udyam_number, format_valid, found, enterprise_name, enterprise_type, major_activity, nic_description, state, city, date_of_registration` |
| `ConsentNotice` | `version, purposes[{id, required, text}], body, retention` |
| `Check` | `code, status` (PASS/WARN/FAIL), `message: LocalText, fix_hint?: LocalText, doc_type?` |
| `DocumentResult` | `doc_type, detected_type, readable, quality{blur_score, blurry, skew_deg}, fields` (masked), `issues: Check[]` |
| `KycResult` | `order_id, verdict` (VERIFIED/ACTION_REQUIRED/MANUAL_REVIEW/REJECTED), `checks[], gst_products_blocked, created_at` |
| `Order` | `order_id, status, contact_name, phone_masked, items[], totals, timeline[{key, label, state, date?, eta?}], item_etas[], eta_activation_date, install_slot?, events[], next_action?, created_at` |
| `LeadRow` | `lead_id, business_name, segment, city, city_tier, source, preferred_language, stage_reached, drop_reason, score (0–1), band` (HOT/WARM/COLD), `top_factors[2], suggested_channel` (FIELD/PARTNER/INSIDE_SALES/SELF_SERVE_LINK) |

**Order status machine (WS4 enforces):**

```
QUOTE_ACCEPTED → KYC_PENDING → KYC_ACTION_REQUIRED → (retake re-runs KYC) KYC_PENDING | KYC_VERIFIED | KYC_REVIEW | REJECTED
                             → KYC_REVIEW → KYC_VERIFIED | REJECTED
                             → KYC_VERIFIED → INSTALL_SCHEDULED → INSTALLING → ACTIVE
                             → REJECTED
```

## Endpoints

| Method + path | Body / query | Returns | Owner |
|---|---|---|---|
| `GET /api/health` | | `{status}` | Phase 0 |
| `GET /api/meta` | | `Meta {demo_mode, today, sample_applicants, version}` | Phase 0 |
| `GET /api/registry/gstin/{gstin}` | | `GstinLookup` (real) | Phase 0 |
| `GET /api/registry/udyam/{udyam}` | | `UdyamLookup` (real) | Phase 0 |
| `GET /api/catalogue` | | `Product[]` (real) | WS1 |
| `POST /api/recommend` | `{profile}` | `Quote` (saved) | WS1 |
| `POST /api/quote` | `{profile, selected:[{product_id, quantity}], quote_id?}` | `Quote` (saved, new id) | WS1 |
| `POST /api/advisor/message` | `{session_id?, text, language?}` | `AdvisorReply` | WS2 |
| `POST /api/advisor/handoff` | `{session_id, reason, phone?}` | `HandoffResponse` | WS2 |
| `GET /api/llm-status` | | `LlmStatus` | WS2 |
| `GET /api/kyc/notice` | | `ConsentNotice` | WS3 |
| `POST /api/kyc/{order_id}/consent` | `{version, purposes_accepted[]}` | `ConsentRecord` | WS3 |
| `DELETE /api/kyc/{order_id}/consent` | | 204, and deletes KYC data | WS3 |
| `POST /api/kyc/{order_id}/documents` | multipart `doc_type`, `file` | `DocumentResult` (403 without consent) | WS3 |
| `POST /api/kyc/{order_id}/submit` | | `KycResult` | WS3 |
| `POST /api/kyc/{order_id}/sample/{K01..K12}` | | `KycResult` (demo) | WS3 |
| `POST /api/orders` | `{quote_id, contact_name, phone}` | `{order_id, pin}` | WS4 |
| `GET /api/orders/{id}` | `?pin=` | `Order` (404 on wrong PIN) | WS4 |
| `GET /api/orders/{id}/slots` | `?pin=` | `SlotsResponse` | WS4 |
| `POST /api/orders/{id}/slots` | `{pin, date, window}` | `Order` | WS4 |
| `POST /api/orders/{id}/advance` | `?pin=` or header `X-Backoffice-Key` | `Order` (demo only) | WS4 |
| `GET /api/backoffice/leads` | `?limit&offset&channel&segment`, header `X-Backoffice-Key` | `LeadsPage` | WS5 |
| `GET /api/backoffice/handoffs` | header | `HandoffRow[]` | WS5 |
| `GET /api/backoffice/kyc-reviews` | header | `KycReviewRow[]` | WS5 |
| `GET /api/backoffice/orders` | header | `OrderRow[]` | WS5 |
| `GET /api/backoffice/model` | header | `ModelReport` | WS5 |
| `GET /api/backoffice/funnel` | header | `FunnelReport` | WS5 |

Every endpoint already exists as a stub that returns a fixture of the right shape (`backend/app/fixtures.py`). A workstream replaces the stub bodies in its own router file. It never touches `main.py`, because every router is already included there.

## Python interfaces between workstreams

| Function | Called by | Owner |
|---|---|---|
| `app.engine.recommend(profile) -> Quote` | WS2 advisor, `/api/recommend` | WS1 |
| `app.engine.price(profile, selected) -> Quote` | WS4 orders (re-price at order time), `/api/quote` | WS1 |
| `app.orders.hooks.on_kyc_result(order_id, KycResult)` | WS3 after every submit | WS4 |

These are stubs on `main` until the owner's branch is merged. Code against the signature.

## Shared helpers (Phase 0, use them, don't copy them)

- **`app.config.settings`**
  - `today`, `demo_mode`, `backoffice_key`, `fernet_key`
  - `groq_api_key`, `groq_model`, `gemini_api_key`, `gemini_model`
  - `llm_order`, `llm_timeout_s`, `kyc_documents_dir`
- **`app.data`** (all cached):
  - `catalogue()`, `products_by_id()`, `leads()` (DataFrame with `segment_code`)
  - `gstin_registry()`, `udyam_registry()`
  - `city_tiers()`: 22 cities, lower-case key → `{city, tier, state}`
  - `business_type_segments()`: 35 business types → segment
  - `kyc_document_path(applicant, doc_type)`, `SEGMENT_CODES`, `CURRENT_INTERNET_CODES`, `SAMPLE_APPLICANTS`
- **`app.common.gstin`**: `normalize`, `check_char`, `format_valid`, `checksum_valid`, `is_valid`, `state_for`, `normalize_udyam`, `udyam_format_valid`, `STATE_CODES`.
  - All 3,534 registry GSTINs pass the checksum.
  - K06's certificate GSTIN `08YKZXS8189L1ZO` fails it.
- **`app.common.registry`**: `lookup_gstin`, `lookup_udyam`.
- **`app.common.mask`**: `mask_gstin`, `mask_udyam`, `mask_phone`, `mask_id`, `redact(text)`.
- **`app.common.i18n_server`**: `lt(en, hi)`, `pick(text, lang)`.
- **`app.common.auth`**: `require_backoffice_key` (FastAPI dependency), `is_backoffice_key(value)`.
- **`app.store`**: CRUD for every table (sessions, handoffs, quotes, orders, events, consents, KYC results) plus `new_id(prefix)` and `now()`. No workstream writes SQL.
- **Frontend:**
  - `api` client (`src/api/client.ts`); `useT()` gives `{t, lt, lang}`; `useLang()`; `useJourney()` (profile, quote, orderId, pin, advisorSessionId); `useMeta()`.
  - UI primitives from `src/ui`: `Button, Card, Chip, Toggle, Stepper, Money, formatInr, Pill, Banner, Spinner, Timeline, PageTitle`.

## Tables (SQLite, `backend/app/db.py`)

| Table | Writer | Readers |
|---|---|---|
| `advisor_sessions` | WS2 | WS5 (via `handoffs`) |
| `handoffs` | WS2 | WS5 |
| `quotes` | WS1 (via `/api/recommend`, `/api/quote`) | WS4 |
| `orders`, `order_events` | WS4 | WS5 |
| `consents`, `kyc_results` | WS3 | WS4, WS5 |

## File ownership

| Owner | Files |
|---|---|
| Phase 0 | `backend/app/{main,config,contracts,data,db,store,fixtures}.py`, `backend/app/common/*`, `backend/tests/{conftest,test_phase0}.py`, `backend/requirements*`, `frontend/src/{App,Layout,Landing,main}.tsx`, `frontend/src/{api,state,ui}/*`, `frontend/src/i18n/{index.tsx,common.ts}`, `frontend/package.json`, `frontend/vite.config.ts`, `scripts/{dev.sh,export_fixtures.py}`, `docs/CONTRACTS.md` |
| WS1 | `backend/app/engine/*`, `backend/app/routers/{catalogue,quote}.py`, `backend/tests/test_ws1_engine.py`, `frontend/src/features/quote/*`, `frontend/src/i18n/quote.ts` |
| WS2 | `backend/app/advisor/*`, `backend/app/routers/advisor.py`, `backend/tests/test_ws2_advisor.py`, `scripts/advisor_scenarios.py`, `frontend/src/features/advisor/*`, `frontend/src/i18n/advisor.ts` |
| WS3 | `backend/app/kyc/*`, `backend/app/routers/kyc.py`, `backend/tests/test_ws3_kyc.py`, `scripts/kyc_eval.py`, `frontend/src/features/kyc/*`, `frontend/src/i18n/kyc.ts` |
| WS4 | `backend/app/orders/*`, `backend/app/routers/orders.py`, `backend/tests/test_ws4_orders.py`, `frontend/src/features/track/*`, `frontend/src/i18n/track.ts` |
| WS5 | `backend/app/leads/*`, `backend/app/routers/backoffice.py`, `backend/tests/test_ws5_leads.py`, `frontend/src/features/backoffice/*`, `frontend/src/i18n/backoffice.ts` |
| WS6 | `docs/deck/*`, `docs/architecture/*`, `docs/privacy/*`, `docs/demo-script.md`, `docs/metrics.md` |
