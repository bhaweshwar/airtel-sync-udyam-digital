# Project Udyam Digital

Mobile-first digital onboarding prototype for MSMEs, built for Airtel SYNC 2026 Track A. A React/TypeScript client calls a Spring Boot modular monolith. The Java catalogue engine owns eligibility and pricing. The conversational advisor uses Gemini to extract customer-stated needs and explain deterministic engine results.

## Technology

- React 19, TypeScript 6, Vite 8
- Java 21 bytecode, Spring Boot 3.5.16, Maven Wrapper 3.9.11
- Gemini documented `generateContent` REST API (`gemini-3.8-flash` by default)
- SQLite and Tesseract are planned for later persistence and OCR work
- Java 25 is installed locally; Spring Boot 3.5 supports it. See [technology decisions](docs/architecture/technology-decisions.md).

## Repository structure

```text
frontend/                   React + TypeScript + Vite client
backend/                    Spring Boot modular monolith
docs/architecture/          Architecture and API contracts
docs/requirements/           Audited case requirements and data rules
data/source/                 Local source archives and datasets (ignored)
```

The source ZIP and synthetic case datasets are excluded from Git pending redistribution permission confirmation.

## Prerequisites

- Node.js 22.12+ and npm
- JDK 21+ (JDK 25 supported by this Spring Boot line)
- Network access for Maven and npm dependencies
- A Gemini API key for conversational turns; Tesseract is not yet used

## Local development

Frontend:

```powershell
cd frontend
npm ci
npm test
npm run dev
```

Backend (Windows):

```powershell
cd backend
.\mvnw.cmd test
.\mvnw.cmd spring-boot:run
```

Health check: `GET http://localhost:8080/api/v1/health`.

The catalogue loads from `data/source/dataset/product_catalogue.csv` relative to the repository root. Set `CATALOGUE_PATH` to select a different local file. A missing or invalid catalogue prevents startup. Synthetic case data is ignored by Git.

## Gemini advisor configuration

The Gemini key is used only by the backend. Use `.env.example` as a local reference; Spring Boot reads environment variables and does not load `.env` files itself. Set the key in the backend process environment or IDE run configuration. In PowerShell:

```powershell
$env:GEMINI_API_KEY = 'your-key'
$env:GEMINI_MODEL = 'gemini-3.8-flash'
$env:GEMINI_TIMEOUT = '30s'
cd backend
.\mvnw.cmd spring-boot:run
```

Never put a real key in source, tests, screenshots or committed documentation. If the key is absent, starting and reading a conversation still works, but sending a message returns a clear recoverable `503`; no pretend AI answer is shown.

`AdvisorModelProvider` is the provider boundary. `GeminiRestAdvisorProvider` uses Google's documented [Gemini `generateContent` REST API](https://ai.google.dev/api/generate-content) and [structured output](https://ai.google.dev/gemini-api/docs/structured-output), with the backend-only API-key header and request timeouts. The default [`gemini-3.8-flash` model](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash) supports this request style. Another provider can implement the port without changing session orchestration. Candidate facts require matching evidence in the latest customer message. The model does not decide product eligibility, product selection or pricing; those come from `RecommendationService`.

Conversation endpoints:

- `POST /api/v1/advisor/conversations` starts a temporary session (optional `initialNeed`).
- `POST /api/v1/advisor/conversations/{id}/messages` continues it.
- `GET /api/v1/advisor/conversations/{id}` returns recent redacted history and state.
- `GET /api/v1/advisor/conversations/{id}/profile` returns collected fields.
- `GET /api/v1/advisor/conversations/{id}/recommendation` returns the deterministic result once ready, otherwise `409`.

Sessions are held in process memory and expire after two hours. Common PAN, GSTIN, Aadhaar, phone and email patterns are redacted before session storage or Gemini processing. GSTIN status is customer-reported and is never verified by this advisor.

## Testing and build

Run `cd backend; .\mvnw.cmd test`, `cd frontend; npm test`, and `cd frontend; npm run build`. Automated tests use mocked provider behavior and do not require a Gemini key or consume API quota. An optional Windows Edge UI smoke check is available as `npm run test:advisor-browser` while both services are running; without a Gemini key it checks the recoverable error/retry, no-fake-response and mobile-layout states.

## Current status

Implemented: premium responsive landing page, conversational Gemini advisor, temporary session management, profile summary, follow-up prompts, retry states, and deterministic catalogue-priced recommendations with eligibility details. OCR/KYC, checkout, persistent conversation storage and order activation tracking remain out of scope for this phase.

A live Gemini request has not been verified unless a key is configured and an actual request succeeds.
