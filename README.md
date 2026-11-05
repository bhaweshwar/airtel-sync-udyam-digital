# Udyam Digital

A digital-first acquisition and onboarding journey for small businesses, built for the YTL Hackathon 2026, Enterprise Track A (Airtel SYNC): Project Udyam Digital. The case uses a fictional operator, Accel Telecom, and its B2B arm, Accel Business. All data is synthetic.

A business owner, on a phone and in English or Hindi:
1. **Advisor:** talks to an advisor that recommends a bundle from the catalogue and explains why.
2. **Quote:** sees one monthly price and switches add-ons on or off.
3. **Smart KYC:** completes KYC with document photos, mock GSTIN/Udyam lookups and a clear consent screen.
4. **Tracker:** follows installation without calling support.

Accel staff get a back office that ranks the leads the journey didn't close.

## Status

**Phase 0: shared scaffold.** It contains contracts, data loaders, the SQLite store, GSTIN validation, registry lookups, stub endpoints and the frontend shell. The modules are built in six parallel workstreams; see [docs/WORKSTREAMS.md](docs/WORKSTREAMS.md).

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
