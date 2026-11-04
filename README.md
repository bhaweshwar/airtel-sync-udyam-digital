# Project Udyam Digital

Mobile-first digital onboarding prototype for MSMEs, built for Airtel SYNC 2026 Track A. This project uses a modular monolith: a React/TypeScript client calls a Spring Boot REST API. Deterministic catalogue and KYC services will own eligibility and validation decisions; any future LLM integration will be isolated behind a provider interface and limited to conversation and explanations.

## Technology

- React 19.3, TypeScript 6.0, Vite 8
- Java 21 application baseline, Spring Boot 3.5.16, Maven Wrapper 3.9.11
- SQLite planned for local prototype persistence
- Tesseract planned for OCR integration
- Git

Java 25 is installed in the current environment. Spring Boot 3.5 supports Java 17 through 25, so it can run on the installed JDK. The project compiles to Java 21 bytecode for a broadly supported LTS runtime; Java 25 will be used for the current build unless a Java 21 JDK is selected. See [technology decisions](docs/architecture/technology-decisions.md).

## Repository structure

```text
frontend/                  React + TypeScript + Vite client
backend/                   Spring Boot modular monolith
docs/architecture/         Architecture and API contracts
docs/requirements/          Audited case requirements and data rules
data/source/                Local source archives (ignored by Git)
scripts/                    Local helper scripts
```

The source ZIP and extracted synthetic datasets are intentionally excluded from Git pending redistribution permission confirmation.

## Prerequisites

- Node.js 22.12+ (the current workspace has Node 24.18) and npm
- JDK 21+; JDK 25 is supported by the chosen Spring Boot line
- Network access on first run so Maven Wrapper and npm can fetch dependencies
- Tesseract is required only when OCR integration is implemented

## Local development

Frontend:

```powershell
cd frontend
npm ci
npm test
npm run dev
```

Frontend unit tests use Node's built-in test runner. A Windows Edge visual smoke
flow is available at `frontend/tests/capture-flow.mjs`; it exercises the live
advisor-to-recommendation path and writes screenshots to `docs/screenshots/`.

Backend (Windows):

```powershell
cd backend
.\mvnw.cmd test
.\mvnw.cmd spring-boot:run
```

Health check: `GET http://localhost:8080/api/v1/health`.

The backend loads the audited product catalogue at startup. By default it reads
`data/source/dataset/product_catalogue.csv` relative to the repository root. Set
`CATALOGUE_PATH` to use a different CSV file. A missing or invalid catalogue
fails startup with a row-specific load error. The local source archive and
synthetic case data remain excluded from Git.

## Current status

Implemented: premium responsive customer landing page, progressive business
advisor, and backend-priced recommendations with eligibility details and
reasons. The interface calls the Spring Boot REST API; the backend owns
catalogue eligibility, dependency validation, pricing, and recommendation
decisions. See [catalogue engine](docs/architecture/catalogue-engine.md) and
[API design](docs/architecture/api-design.md). Actual desktop/mobile captures
are in [docs/screenshots](docs/screenshots/).

Not implemented yet: conversational LLM, OCR and KYC workflows, checkout,
persistence, and order activation tracking. The advisor is guided and
deterministic; it does not claim to be AI powered. Source data is local and
ignored.
