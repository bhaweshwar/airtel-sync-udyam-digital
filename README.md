# Udyam Digital

**A digital-first acquisition and onboarding journey for small businesses.**

Built for YTL Hackathon 2026, Enterprise Track A (Airtel SYNC). The case uses the fictional operator Accel Telecom and its B2B arm, Accel Business. All case and prototype data is synthetic.

## The idea

Small businesses often piece together connectivity and digital services from multiple providers, while sales, quoting, KYC and installation can involve slow, manual steps. Udyam Digital brings discovery, a tailored bundle, transparent pricing, document checks and order tracking into one mobile-first journey.

The synthetic case data shows the opportunity: 368 of 5,000 leads activated (7.4%), with an average 17.6 days to activation and about three status calls per customer.

## The customer journey

1. **Discover:** An English- or Hindi-speaking owner describes their business to an advisor by chat or voice.
2. **Get a bundle:** A deterministic rules engine recommends eligible products and calculates a clear monthly price. Add-ons can be toggled.
3. **Complete KYC:** The owner reviews purpose-specific consent, uploads documents, and receives checks using OCR and mock GSTIN/Udyam registries.
4. **Track the order:** The owner uses an order ID and PIN to view status, installation slots and ETAs.

Accel staff can use a passcode-protected back office to review handoffs, KYC cases and ranked leads.

## What makes the design useful

- **Rules set eligibility and prices.** The LLM helps interpret the owner’s message and phrase replies; it does not choose prices.
- **The advisor has a fallback.** If LLM services are unavailable or not configured, a rules-based parser continues the conversation.
- **The journey supports assisted sales.** Leads that do not close digitally can be routed to staff or partners.
- **The prototype is multilingual and mobile-first.** The owner journey supports English and Hindi, with browser voice input in the advisor.

## Prototype and project files

- **Live prototype:** [Open Udyam Digital](https://udyam-digital-779328647112.asia-south1.run.app). The back office requires the configured staff passcode.
- **Architecture:** [View the solution architecture diagram](Architecture%20Diagram.png).
- **Privacy and security:** [Read the one-page design note](Privacy%20and%20Security%20Note.pdf).
- **Checks:** 82 backend tests; the KYC evaluation matches all 12 sample applicants; the advisor scenarios pass all 12 cases in rules mode.

## Privacy and security choices

KYC actions require recorded consent. The application processes document uploads in memory and does not persist customer document photos. Phone numbers are encrypted at rest, and order PINs are stored as salted hashes. The advisor masks recognized GSTIN, Udyam and Indian mobile-number patterns before sending messages to configured LLM providers.

This is a synthetic-data prototype, not a production security certification. Retention deletion jobs are not implemented; back-office access uses a shared passcode; and the demo SQLite database is not durable across service restarts or scale-to-zero. See the [privacy and security note](Privacy%20and%20Security%20Note.pdf) for details.

## Run it

You need Python 3.12 (via [uv](https://docs.astral.sh/uv/)) and Node 22+.

```bash
uv venv backend/.venv --python 3.12
uv pip install --python backend/.venv/bin/python -r backend/requirements.txt
npm --prefix frontend install
cp .env.example .env        # optional: LLM keys, back-office passcode
scripts/dev.sh              # API on :8000, web on :5173
```

- **Single server:** run `npm --prefix frontend run build`. FastAPI then serves the built app at http://127.0.0.1:8000.
- **Mock mode:** `npm --prefix frontend run mock` uses sample data and makes no server calls.
- **Tests:** `cd backend && .venv/bin/python -m pytest`

## Deploy (Google Cloud Run)

The `Dockerfile` builds the React app and serves it from FastAPI in one container. The live prototype runs on Cloud Run in `asia-south1` with 2 vCPU and 2 GB of memory (document reading needs about 1.2 GB at its peak), one instance at most.

1. Store `GROQ_API_KEY`, `GEMINI_API_KEY`, `BACKOFFICE_KEY` and `FERNET_KEY` in Secret Manager. Without LLM keys the advisor runs in offline rules mode. The staff passcode is the `BACKOFFICE_KEY` value.
2. From a clean export of the repository (no `.env`), deploy with
   `gcloud run deploy udyam-digital --source . --region asia-south1 --cpu 2 --memory 2Gi --max-instances 1 --set-secrets GROQ_API_KEY=GROQ_API_KEY:latest,...`
   and set `OCR_THREADS=1` so the tracker stays responsive while a document is read.
3. Before a demo, open the URL once. An idle service scales to zero, and the first request takes a few seconds.

`render.yaml` is kept for reference, but Render's free 512 MB plan runs out of memory while reading documents.

Limits of this setup:
- **Demo data resets.** The SQLite database lives on the container's disk, so orders disappear on every restart, redeploy or scale to zero.
- **Demo mode is on.** Sample applicants and the "move to next step" button are visible; set `DEMO_MODE=0` to hide them.

## Repository layout

- `backend/` — FastAPI app, API routers, rules engine, advisor, KYC pipeline, orders and lead scoring.
- `frontend/` — Vite, React, TypeScript and Tailwind app; mobile-first, English and Hindi.
- `data/` — synthetic case CSVs and specimen KYC images.
- `scripts/` — development, evaluation and fixture tools.
- `Architecture Diagram.png` — solution architecture.
- `Privacy and Security Note.pdf` — one-page privacy and security design note.
