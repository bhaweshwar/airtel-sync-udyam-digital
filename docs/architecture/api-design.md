# API design

Base path: `/api/v1`. JSON request and response bodies use camelCase. The
health and catalogue/recommendation routes below are implemented. Money is
serialized as decimal INR values backed by `BigDecimal`; callers cannot supply
prices.

| Method and route | Purpose | Request / response outline |
|---|---|---|
| `GET /health` | Liveness | `{status, service}` |
| `GET /catalogue/products` | List imported products | Returns all loaded catalogue products |
| `GET /catalogue/products/{productId}` | Read one product | Returns product or `404` |
| `POST /catalogue/eligibility/evaluate` | Evaluate products for a profile | Returns each product with eligible/manual-review/ineligible status and reasons |
| `POST /catalogue/bundles/validate` | Validate selected products | Profile plus product IDs and quantities; rejects invalid bundles |
| `POST /catalogue/pricing/calculate` | Price an eligible bundle | Same request as validation; returns line and total estimates |
| `POST /recommendations` | Deterministic recommendation | Business profile + needs; returns eligible products, prices and exclusions |
| `POST /advisor/conversations` | Start an ephemeral conversation | Optional selected need; returns session ID and empty state |
| `POST /advisor/conversations/{id}/messages` | Continue Gemini-assisted discovery | Customer message; returns redacted history, profile, follow-ups and recommendation when ready |
| `GET /advisor/conversations/{id}` | Retrieve conversation | Recent redacted history, profile and recommendation state |
| `GET /advisor/conversations/{id}/profile` | Retrieve structured profile | Customer-stated fields; GSTIN status remains unverified |
| `GET /advisor/conversations/{id}/recommendation` | Retrieve deterministic result | Engine response or `409` until discovery is complete |
| `POST /quotes` | Persist a quote | Not implemented; current price calculation is stateless |
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

Recommendation response is built by the deterministic catalogue engine. Gemini receives recent redacted conversation context and customer-stated profile fields to extract candidates; each fact must have matching evidence in the latest customer turn. The explanation call receives the actual engine response, and its text cannot change selections, eligibility or prices. Unsafe commercial text is rejected. Provider failures return a recoverable error; no fallback is presented as an AI answer.

### Implemented request shape

The profile request fields are `segment`, `businessType`, `employeeCount`,
`siteCount`, `cityTier`, `needs`, and `gstinStatus`. Segment and tier are enum
names from the API schema. See the request records under
`backend/src/main/java/com/udhyam/digital/catalogue/api` for the full contract.

```json
{
  "businessProfile": {
    "segment": "MICRO_RETAIL",
    "businessType": "Retail shop",
    "employeeCount": 3,
    "siteCount": 1,
    "cityTier": "TIER_1",
    "needs": ["CONNECTIVITY", "DIGITAL_PRESENCE"],
    "gstinStatus": "ACTIVE"
  },
  "selections": [{"productId": "P01", "quantity": 1}]
}
```

Bundle validate and price use that shape. Recommendations accept the profile
object directly. Requests are bean-validated; errors use a JSON envelope with
`code`, `message`, and `details`. Bundle business-rule failures return `422`.
Eligibility evaluation is advisory and reports manual review distinctly.

Advisor routes listed above are implemented. Quote persistence, consent, KYC,
order, and tracking routes remain future contracts and are not served yet.

### Advisor request and response examples

Start a session with an optional need selected on the landing page:

```json
{ "initialNeed": "RELIABLE_INTERNET" }
```

Continue with natural language:

```json
{ "message": "I run a small bakery in Jaipur with four employees and need reliable internet." }
```

The response contains `conversationId`, redacted `messages`, a nullable-field
`profile`, `missingFields`, up to two `followUpQuestions`, a `status`, and the
deterministic `recommendation` when discovery is complete. The `profile` route
wraps the profile with `gstinStatusSource` and `gstinStatusVerified: false`.
Common provider errors use `503` for missing configuration/rate limits,
`504` for timeout, and `502` for malformed/unavailable provider responses; all
carry a safe `{code,message,details}` error envelope and can be retried.

See [advisor workflow](advisor-workflow.md) for state, redaction, provider, and
recommendation boundaries.
