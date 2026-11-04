# API design (proposed contract)

Base path: `/api/v1`. JSON request and response bodies use camelCase. Money values use integer paise or integer INR as explicitly named fields; never binary floating point. The health route is implemented; all other routes below are design only.

| Method and route | Purpose | Request / response outline |
|---|---|---|
| `GET /health` | Liveness | `{status, service}` |
| `POST /advisor/sessions` | Start needs discovery | Locale and optional channel; returns session ID and first prompt |
| `POST /advisor/sessions/{id}/messages` | Continue guided conversation | User message; returns assistant response and structured profile fields |
| `POST /recommendations` | Deterministic recommendation | Business profile + needs; returns candidate bundles, eligibility and reason codes |
| `POST /quotes` | Price a selected bundle | Product IDs, explicit quantities, profile; returns line prices, setup, term, caveats and quote token |
| `POST /consents` | Record scoped consent | Purpose, notice version, affirmative action; returns receipt ID |
| `POST /kyc/lookups/gstin` | Mock GST lookup | GSTIN + consent receipt; returns masked identity, status and synthetic-source marker |
| `POST /kyc/lookups/udyam` | Mock Udyam lookup | Udyam number + consent receipt; returns masked enterprise details and synthetic-source marker |
| `POST /kyc/documents` | Upload a document | Multipart document + type + consent receipt; returns document ID and processing state |
| `GET /kyc/cases/{id}` | KYC review state | Per-field status: PASS/FAIL/MANUAL_REVIEW/MISSING/NOT_APPLICABLE |
| `POST /orders` | Create checkout order | Quote token, confirmation and idempotency key; returns order ID/state |
| `GET /orders/{id}/tracking` | Progress tracker | Current state, milestones and indicative dates |

## API conventions

- Validate user-controlled values at the boundary and revalidate all business invariants in application services.
- Return a stable error envelope such as `{code, message, requestId, fieldErrors}`; never echo full identifiers or documents.
- Use `400` for malformed requests, `401/403` for access control, `404` for absent resources, `409` for state conflicts, `422` for business-rule rejection, `429` for rate limits, and `503` for unavailable external adapters.
- Require scoped consent for KYC processing/lookup; response includes consent receipt association, not full document data.
- Require idempotency on order creation and maintain quote snapshot/version to prevent stale pricing.
- Rate-limit lookups and uploads. Enforce payload/file limits and allowlisted MIME types.

## Recommendation/LLM boundary

Recommendation response is built from deterministic catalogue-engine results. Advisor messages may reference only product IDs/prices/reasons returned by that engine. The LLM adapter receives minimized business needs and an allowlisted recommendation context; it returns candidate explanatory text, which is sanitized and checked for unsupported offers before display. Failure falls back to deterministic templates.
