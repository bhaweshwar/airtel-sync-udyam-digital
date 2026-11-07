# Udyam Digital

A digital-first acquisition and onboarding journey for small businesses, built for the YTL Hackathon 2026, Enterprise Track A (Airtel SYNC): Project Udyam Digital. The case uses a fictional operator, Accel Telecom, and its B2B arm, Accel Business. All data is synthetic.

A business owner, on a phone and in English or Hindi:
1. **Advisor:** talks to an advisor that recommends a bundle from the catalogue and explains why.
2. **Quote:** sees one monthly price and switches add-ons on or off.
3. **Smart KYC:** completes KYC with document photos, mock GSTIN/Udyam lookups and a clear consent screen.
4. **Tracker:** follows installation without calling support.

Accel staff get a back office that ranks the leads the journey didn't close.

## Status

All four required modules work end to end, plus the back office with a lead score and browser voice input in the advisor.
- **Live prototype:** https://udyam-digital-779328647112.asia-south1.run.app (Google Cloud Run; the back office needs the staff passcode).
- **Checks:** 82 backend tests; `scripts/kyc_eval.py` matches all 12 sample applicants; `scripts/advisor_scenarios.py` passes all 12 scenarios in rules mode.
- **Submission pack:** in `docs/deck/`, `docs/architecture/`, `docs/privacy/` and `docs/demo-script.md`.
- **How it was built:** in six parallel workstreams; see [docs/WORKSTREAMS.md](docs/WORKSTREAMS.md).

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

## Layout

```
data/         case CSVs + 47 specimen KYC images (synthetic)
backend/      FastAPI app: contracts, data, store, common helpers, one router + package per module
frontend/     Vite + React + TypeScript + Tailwind, mobile-first, EN/HI
docs/         CONTRACTS.md (shared API), WORKSTREAMS.md (plan + prompts), case brief and template
scripts/      dev.sh, setup_worktree.sh, export_fixtures.py
```

## Design rules

- **Rules decide, the LLM talks.** Products, eligibility and prices come from a deterministic engine. The LLM only understands the owner's words and phrases replies, and never writes numbers.
- **The advisor never dead-ends.** With no LLM key, or when the LLM fails, a rules parser keeps the conversation going in English, Hindi and Hinglish.
- **Privacy by default:**
  - Consent is asked per purpose before KYC.
  - Document photos are read in memory and never stored.
  - Identifiers are masked in responses and logs.
  - Phone numbers are encrypted at rest.
