# Workstreams

Six parallel Claude Code sessions, one per git worktree, all started from the Phase 0 commit on `main`. Each session edits only the files it owns (see [CONTRACTS.md](CONTRACTS.md#file-ownership)), so the branches merge without conflicts.

## 1. Create the worktrees (once, from the main checkout)

```bash
cd /Users/kamal/Projects/airtel-sync
for w in ws1-quote ws2-advisor ws3-kyc ws4-tracker ws5-backoffice ws6-docs; do git worktree add ../ud-$w -b $w; done
for w in ws1-quote ws2-advisor ws3-kyc ws4-tracker ws5-backoffice; do (cd ../ud-$w && scripts/setup_worktree.sh /Users/kamal/Projects/airtel-sync); done
```

The setup script links the main checkout's `backend/.venv` and `frontend/node_modules` into each worktree. No workstream adds dependencies, so they can share them.

## 2. Ports and time boxes

| WS | Worktree | API_PORT | WEB_PORT | Time box |
|---|---|---|---|---|
| WS1 Engine + Quote | `../ud-ws1-quote` | 8001 | 5181 | 2.5 h |
| WS2 Advisor + voice | `../ud-ws2-advisor` | 8002 | 5182 | 3 h |
| WS3 Smart KYC | `../ud-ws3-kyc` | 8003 | 5183 | 3.5 h |
| WS4 Orders + Tracker | `../ud-ws4-tracker` | 8004 | 5184 | 2 h |
| WS5 Back office + lead score | `../ud-ws5-backoffice` | 8005 | 5185 | 2 h |
| WS6 Submission pack | `../ud-ws6-docs` | — | — | 2.5 h |

**Merge order** (Phase 2, on `main`): WS1 → WS4 → WS2 → WS3 → WS5 → WS6.

## 3. Prompts

Open a Claude Code session in each worktree. Paste the **shared preamble**, then that workstream's block.

### Shared preamble

```
You are one of six parallel Claude Code sessions building "Project Udyam Digital" (YTL Hackathon 2026, Enterprise Track A; fictional operator Accel Business; all data synthetic). You are in a git worktree on your own branch. Stack: FastAPI + SQLite backend (backend/, Python 3.12, venv at backend/.venv) serving a Vite + React 19 + TypeScript + Tailwind 4 mobile-first SPA (frontend/).

Before anything else: if backend/.venv or frontend/node_modules is missing, run scripts/setup_worktree.sh /Users/kamal/Projects/airtel-sync. Then read docs/CONTRACTS.md, backend/app/contracts.py and frontend/src/api/types.ts and honour them exactly.

Rules:
- Edit ONLY the files your workstream owns (listed below). If you need a change to a shared Phase 0 file, do not make it: append a row to docs/CHANGE_REQUESTS.md and work around it locally.
- Reuse the shared helpers: backend/app/config.py (settings), data.py, store.py, common/ (gstin, registry, mask, i18n_server, auth); frontend api client (src/api/client.ts), useT()/lt(), useJourney(), useMeta() and the src/ui primitives.
- Every user-facing string from the server is a LocalText {en, hi}. Every UI string goes through t() with keys prefixed by your feature name in your own i18n file. Write plain English and natural Hindi.
- "Today" is settings.today (2026-07-15); never call date.today(). Demo-only controls check settings.demo_mode on the server and useMeta().demo_mode in the UI. Mask identifiers with app.common.mask.
- Run your servers on your own ports: API_PORT=<api> WEB_PORT=<web> scripts/dev.sh. Use `WEB_PORT=<web> npm --prefix frontend run mock` to build UI against the fixtures before the backend works.
- Tests: cd backend && .venv/bin/python -m pytest tests/test_phase0.py tests/<your test file>. Keep your file fast (< 30 s), a handful of tests, no real LLM calls; use the client / fresh_db / bo_headers fixtures from conftest.py.
- Before you finish: your tests and tests/test_phase0.py pass, and npm --prefix frontend run build passes.
- Don't add dependencies. Don't use Airtel branding.
- Time box: stop at the time box with a working slice, commit to your branch (do not merge), and end with a short list of what is done and what is left.
```

### WS1: Engine + Quote (API_PORT 8001, WEB_PORT 5181)

```
WORKSTREAM WS1 — Eligibility, pricing, recommendation + Quote page. Time box 2.5 h.
You own: backend/app/engine/*, backend/app/routers/catalogue.py, backend/app/routers/quote.py, backend/tests/test_ws1_engine.py, frontend/src/features/quote/*, frontend/src/i18n/quote.ts.

Build:
1. Eligibility per product (data.catalogue()): city_tiers, min_employees, min_sites, requires_gstin (needs has_gstin true AND gstin_status not Cancelled/Suspended), requires_one_of (bundle must contain one of the listed products). Each failure gives an Ineligible with reason_code and a LocalText sentence ("Biz Fibre 1G is only sold in tier 1 cities. Kochi is tier 2."). If gstin_status is Cancelled or Suspended, set quote.gst_products_blocked = true and say so in a notice; still sell everything that doesn't need a GSTIN.
2. Pricing: unit price = midpoint of price_min/price_max rounded to the rupee (activated leads pay ~0.48 of the range), monthly = unit price × quantity, setup = setup_inr × quantity, contract_months = longest min_contract_months in the bundle, GST 18% shown separately (monthly_total_with_gst_inr). Never trust client prices.
3. Default quantities from `unit`: per site → sites; per user → employees; per line → ceil(employees/2) capped at 6; per camera → 2 × sites; per counter → sites; per device → employees for P20, 5 for P24; per channel → max(2, ceil(employees/5)); per IP / number / pack / account / vehicle → 1.
4. Recommendation: at startup compute each segment's most common activated bundle from data.leads() bundle_products (format "P01x1;P07x2"); keep only eligible products; add need-based add-ons from profile.needs (cctv→P23, payments_pos→P19, whatsapp→P15, email→P16, backup→P09, security→P20, wifi→P22, website→P18, cloud_backup→P17, telephony→P12, tollfree→P13, sms→P14, static_ip→P11, iot→P24, fleet→P25, sdwan→P10). Connectivity: P01 if fibre is fine for a small site; P04 AirFiber for a single-site micro business on mobile hotspot/none; P02 for prof/multi; P05 leased line for mfg or ≥10 staff with an active GSTIN. Fill addons_available with other eligible, relevant products the owner can switch on. Every item gets a one-line LocalText reason that cites the profile ("12 staff, so 12 email accounts").
5. price(profile, selected): price exactly the selection; if a product's requires_one_of is unmet, auto-add the cheapest eligible prerequisite with a notice; when a prerequisite is removed, remove its dependants with a notice ("Static IP removed because Biz Fibre 300 was removed").
6. Replace the stub bodies of engine.recommend / engine.price (keep the signatures in app/engine/__init__.py; put logic in new files inside app/engine/), and keep /api/recommend and /api/quote saving every quote with store.save_quote.
7. Quote page (frontend/src/features/quote): read the quote from useJourney().journey.quote (if missing, link back to /advisor). Show one big monthly total with the "+18% GST" line and one-time setup; items with their reasons and quantity steppers; Toggle switches for addons_available; ineligible products in a collapsed "Not available for you" list with reasons; contract length; notices as Banners. Every change calls api.quote() and replaces the quote. "Confirm order" asks for contact name and phone, calls api.createOrder (WS4 owns it; it's a stub until merge), saves orderId + pin with useJourney().update, shows the PIN once, then navigates to /kyc/:orderId. Must work at 360 px width.
Tests (backend/tests/test_ws1_engine.py): sweep every profile in data.leads() → recommend() never returns an ineligible product or an unmet dependency; 6 golden profiles: kirana in Ludhiana (tier 2), 3 staff, no GST; dental clinic in Kochi, 12 staff, active GSTIN; restaurant chain, 5 sites, tier 1; auto-parts unit, 40 staff, wants a leased line; CA firm, 8 staff, wants email + backup; tier-1 pharmacy selecting CCTV with no link → a link is auto-added.
```

### WS2: Advisor + voice (API_PORT 8002, WEB_PORT 5182)

```
WORKSTREAM WS2 — Advisor (LLM + rules fallback) + voice input. Time box 3 h.
You own: backend/app/advisor/*, backend/app/routers/advisor.py, backend/tests/test_ws2_advisor.py, scripts/advisor_scenarios.py, frontend/src/features/advisor/*, frontend/src/i18n/advisor.ts.

Design rule: the LLM understands the owner and writes friendly text; it never chooses products or writes numbers. Products and prices come only from app.engine.recommend() / price() (stubs returning a fixture now; WS1 fills them in — code against the signature).

Build:
1. advisor/llm.py: provider wrapper over httpx (no SDKs), tried in settings.llm_order. Groq: OpenAI-compatible POST https://api.groq.com/openai/v1/chat/completions with response_format {"type":"json_object"}, model settings.groq_model. Gemini: REST generateContent with generationConfig.responseMimeType "application/json", model settings.gemini_model. Timeout settings.llm_timeout_s, one retry on 429/5xx, then move on; if all fail return None. GET /api/llm-status reports configured/ok per provider and which one answered.
2. advisor/extract.py: one LLM call per turn returning a partial BusinessProfile plus intent ∈ {answer, accept, change, ask_why, handoff, other} and the language the owner wrote in. Validate with Pydantic; drop unknown values. Map business_type → segment with data.business_type_segments() and city → tier/state with data.city_tiers(). For a city that isn't listed, ask "Is it a metro, a big city or a small town?" (metro → 1, big city → 2, small town → 3 = not served → hand-off).
3. advisor/rules_parser.py: deterministic fallback for English, Hindi and Hinglish (numbers like "teen" / "3 log" / "तीन", "GST hai / nahi", city names from data.city_tiers(), business words → segment, need keywords incl. Hindi such as "CCTV", "बिलिंग", "व्हाट्सऐप"). Used whenever there's no key, a timeout, invalid JSON or a 429. The reply's mode is "rules" when the parser was used.
4. advisor/flow.py: required slots business_type, city/tier, employees, sites, has_gstin, current_internet, needs (≥ 1). Ask one question per turn with 3–5 quick_replies. If the owner types a GSTIN, call common.registry.lookup_gstin, prefill state and gstin_status; a Cancelled or Suspended GSTIN is explained in plain words (GST-only products can't be sold yet). When all slots are filled → engine.recommend(profile) → stage "recommended" with the quote. Tier 3, an explicit request for a person, or two turns in a row where nothing was understood → stage "handoff" and store.save_handoff. Persist with store.create_session / get_session / update_session (keep the message history there).
5. Reply text: EN and HI templates for every question and the recommendation intro. You may ask the LLM to rephrase the intro in the owner's language, but reject its text if it contains any digit, "₹", "Rs" or a product code /P\d\d/, and use the template instead. Prices appear only in the quote card the UI renders.
6. Advisor page (frontend/src/features/advisor): chat bubbles, quick-reply Chips, typing indicator, an "offline mode" Pill when mode = rules, a compact quote preview card with "See full quote" → /quote (save quote, profile and session id with useJourney().update), and a "Talk to a person" button (api.handoff). Voice: a mic button using window.SpeechRecognition || window.webkitSpeechRecognition with lang hi-IN or en-IN from the UI language, interim text in the input, auto-send on the final result; a speaker toggle that reads replies with speechSynthesis. Hide the mic when unsupported.
7. scripts/advisor_scenarios.py: 12 scripted conversations through the API (TestClient, rules mode by default; --llm uses the keys in .env), each asserting the final stage and key product presence/absence: English kirana with no GST; Hindi dental clinic that types a GSTIN; Hinglish restaurant chain with 4 sites; manufacturer with 40 staff wanting a leased line; tier-2 city asking for Fibre 1G (refused with a reason); shop with no GST asking for WhatsApp API (GST-only, explained); cancelled GSTIN typed; budget ₹800; owner changes their mind (remove CCTV); unknown small town → hand-off; "mujhe kisi insaan se baat karni hai" → hand-off; one-shot full description in a single message. Product assertions only become meaningful after WS1 merges; until then assert stages.
Tests (backend/tests/test_ws2_advisor.py): rules_parser extraction on ~10 phrases (EN/HI/Hinglish); the number guard rejects text with digits, ₹ or P-codes; with no keys the endpoint answers in rules mode.
```

### WS3: Smart KYC (API_PORT 8003, WEB_PORT 5183)

```
WORKSTREAM WS3 — Smart KYC: consent, OCR, checks. Time box 3.5 h.
You own: backend/app/kyc/*, backend/app/routers/kyc.py, backend/tests/test_ws3_kyc.py, scripts/kyc_eval.py, frontend/src/features/kyc/*, frontend/src/i18n/kyc.ts.

Build:
1. Consent (DPDP Act 2023): GET /api/kyc/notice returns a versioned ConsentNotice in EN and HI. Purposes: "check my business documents for this order" (required) and "use my anonymised details to improve the service" (optional, never pre-ticked). The body says what is collected, why, who sees it, the retention period, and how to withdraw. Retention: photos are read in memory and never stored; extracted details are kept 180 days after activation, or 30 days if rejected. POST consent stores it (store.save_consent). DELETE withdraws it (store.withdraw_consent) and deletes the KYC result (store.delete_kyc_result). Uploads and submit return 403 {code: "CONSENT_REQUIRED"} without an active consent.
2. kyc/ocr.py: RapidOCR (from rapidocr_onnxruntime import RapidOCR), created once lazily, run on in-memory bytes (cv2.imdecode). Preprocess: use the red channel as greyscale (removes the pink "SYNTHETIC SPECIMEN" watermark); Laplacian-variance blur score (calibrate the threshold on data/kyc_documents so only K04's GST certificate counts as blurred); deskew by trying small rotations (±10°) and keeping the angle with the best mean OCR confidence. Never write uploads to disk.
3. kyc/parse.py: label-anchored parsers for the four specimen templates. GST certificate: GSTIN, Legal name, Trade name, Constitution, Address of principal place of business, Date of liability. Udyam certificate: registration number UDYAM-XX-00-NNNNNNN, enterprise name, type, activity, address, date. Authorised signatory ID: Name, Designation, For business, ID no., Valid till. Utility bill: holder name, supply address, bill date. Detect the document type from its title so a wrong upload in a slot is caught.
4. GSTIN repair: if the read GSTIN fails common.gstin.checksum_valid, try OCR look-alike swaps only (O↔0, I↔1, Z↔2, S↔5, B↔8; at most 2 positions; respect the pattern: positions 1–2 digits, 3–7 letters, 8–11 digits, 12 letter, 13 alphanumeric, 14 "Z", 15 alphanumeric). Accept only if exactly one candidate passes the checksum. Never borrow characters from the registry. K06 must stay invalid.
5. kyc/checks.py, each a Check with LocalText message and fix hint:
   - documents present; image readable (blur);
   - GSTIN format, checksum, found;
   - GSTIN status Active (Cancelled/Suspended → REJECTED with gst_products_blocked true);
   - legal and trade name vs registry (rapidfuzz token_set_ratio: ≥ 90 pass, 75–90 WARN, < 75 FAIL → MANUAL_REVIEW);
   - business name consistent across documents;
   - Udyam number present and found in the registry (name match only; do NOT compare Udyam date or activity, they are noisy for every applicant);
   - signatory equals the proprietor for proprietorships (WARN only for LLP / Pvt Ltd: authority can't be proven from these documents);
   - ID valid till ≥ today;
   - address proof dated ≤ 90 days before today and not in the future;
   - supply address PIN/city matches the GST address.
   Verdict: any rejection-class failure → REJECTED; else any name-mismatch failure → MANUAL_REVIEW; else any owner-fixable failure (blur, missing document, stale bill, expired ID) → ACTION_REQUIRED; else VERIFIED.
6. Endpoints: notice, consent (POST/DELETE), documents (multipart; DocumentResult with masked fields; keep extracted fields in memory keyed by order for at most 30 minutes, never on disk), submit (run checks, store.save_kyc_result with masked fields, then call app.orders.hooks.on_kyc_result(order_id, result)), and demo POST /api/kyc/{order_id}/sample/{K01..K12} (demo_mode only) which runs the same pipeline on data.kyc_document_path(...) files.
7. KYC page (frontend/src/features/kyc): consent screen first (plain language, required vs optional purposes, expandable full notice); then four upload slots using <input type="file" accept="image/*" capture="environment">, each with a status Pill; a "Use a sample applicant" picker (K01–K12) shown only when useMeta().demo_mode; a results screen listing checks in green/amber/red with fix hints and "Retake" for owner-fixable items; a "Withdraw consent" link. Show masked identifiers only. After VERIFIED, link to /track/:orderId.
8. scripts/kyc_eval.py: run all 12 sample applicants through the pipeline, print a table of verdict vs expected, exit non-zero on any mismatch. Expected: K01 REJECTED (Cancelled GSTIN 37IHKXV5167L1ZS; blank Udyam number); K02 VERIFIED (tilted scan, GSTIN contains the letter O); K03 VERIFIED; K04 ACTION_REQUIRED (blurred GST certificate); K05 ACTION_REQUIRED (no Udyam certificate); K06 REJECTED (certificate GSTIN 08YKZXS8189L1ZO fails the checksum; registry has ...5189...); K07 MANUAL_REVIEW (legal name "Prop. Shri Physio Clinic" vs "Neelgiri" everywhere else); K08 VERIFIED (GSTIN letter O); K09 VERIFIED; K10 VERIFIED (27QHJXK0658U1ZL valid and Active; LLP signatory is only a WARN); K11 ACTION_REQUIRED (bill dated 2025-10-31, 257 days old); K12 VERIFIED.
Tests (backend/tests/test_ws3_kyc.py; fast, no OCR): look-alike repair fixes a letter-O misread but not K06; verdict mapping; 90-day boundary; 403 without consent.
```

### WS4: Orders + Tracker (API_PORT 8004, WEB_PORT 5184)

```
WORKSTREAM WS4 — Orders + Tracker. Time box 2 h.
You own: backend/app/orders/*, backend/app/routers/orders.py, backend/tests/test_ws4_orders.py, frontend/src/features/track/*, frontend/src/i18n/track.ts.

Build:
1. POST /api/orders {quote_id, contact_name, phone}: load the quote (store.get_quote; 404 if missing), re-price it with app.engine.price(quote.profile, [its items]) so client numbers are never trusted, then create the order with store.create_order: id like "UD-260715-0007" (date from settings.today + store.count_orders()+1), a random 4-digit PIN (store only a salted hash), the phone Fernet-encrypted with settings.fernet_key plus common.mask.mask_phone. Status goes QUOTE_ACCEPTED → KYC_PENDING with store.add_event rows. Return {order_id, pin}.
2. orders/state.py: allowed transitions only. KYC_PENDING → KYC_ACTION_REQUIRED | KYC_REVIEW | KYC_VERIFIED | REJECTED; KYC_ACTION_REQUIRED → KYC_PENDING | KYC_VERIFIED | KYC_REVIEW | REJECTED (a retake re-runs KYC); KYC_REVIEW → KYC_VERIFIED | REJECTED; KYC_VERIFIED → INSTALL_SCHEDULED → INSTALLING → ACTIVE. Fill app/orders/hooks.py on_kyc_result(order_id, result) to map the verdict to a transition and write an event with a LocalText.
3. Timeline + ETA: steps ordered / documents checked / installation booked / engineer on site / services live, each done/current/upcoming/blocked. Per-product ETA = install start (the booked slot date, else the day after KYC_VERIFIED, else today + 2) + install_days from the catalogue; eta_activation_date = latest product ETA; label them "Estimated" in the UI. Slots: the next 5 working days × windows "10-13" and "14-18", starting the day after KYC_VERIFIED (relative to settings.today); booking moves the order to INSTALL_SCHEDULED. next_action tells the owner what to do next ("Retake your GST certificate photo", "Pick an installation slot").
4. GET /api/orders/{id}?pin= returns Order; wrong or missing PIN → 404 (never reveal whether the order exists); at most 10 attempts per order per minute (in memory). POST /api/orders/{id}/advance moves to the next status only when settings.demo_mode, authorised by the PIN or common.auth.is_backoffice_key(X-Backoffice-Key), with a plausible event ("Engineer Ravi assigned", "Fibre line activated").
5. Track pages (frontend/src/features/track): /track is a lookup form (order ID + PIN, prefilled from useJourney()). /track/:orderId shows the vertical Timeline, per-product ETA chips, a next-action card, the slot picker, event history, a "Share status on WhatsApp" link (https://wa.me/?text= with the order status only, no personal data), polling every 10 s, and a clearly labelled "Demo: move to next step" button only when useMeta().demo_mode.
Tests (backend/tests/test_ws4_orders.py): illegal transitions are rejected; KYC verdict mapping; ETA for a 3-product bundle; wrong PIN → 404.
```

### WS5: Back office + lead score (API_PORT 8005, WEB_PORT 5185)

```
WORKSTREAM WS5 — Back office + lead score. Time box 2 h.
You own: backend/app/leads/*, backend/app/routers/backoffice.py, backend/tests/test_ws5_leads.py, frontend/src/features/backoffice/*, frontend/src/i18n/backoffice.ts.

Build:
1. leads/model.py: scikit-learn LogisticRegression (class_weight="balanced", max_iter=1000) on one-hot intake-time fields ONLY: lead_source, segment, city_tier, has_gstin, has_udyam, employee band (1–5 / 6–20 / 21–50 / 50+), num_sites band (1 / 2–3 / 4+), current_internet, current_provider, monthly spend band, preferred_language. Never use stage dates, stage_reached, drop_reason, bundle, value, churn, NPS or outcome columns (they leak the answer). Target: outcome == "Activated". Train once, lazily on first use (well under a second). Report a time split (train created_date < 2026-06-01, test June): ROC-AUC, top-decile lift, top-20% capture. Then refit on all rows for scoring. Per lead, top 2 factors = largest positive coefficient × feature contributions, as plain phrases ("came through a referral", "has a GSTIN").
2. Bands: HOT = top 20% of scores, WARM = next 30%, COLD = the rest. Suggested channel, checked in this order (this is our answer to "what role for the field force and partners"):
   - drop_reason "Unreachable after 3 attempts", "Wrong or invalid number" or "Owner had no time for a visit" → SELF_SERVE_LINK (send the advisor link by SMS/WhatsApp instead of calling);
   - segment multi or mfg, or an expected bundle ≥ ₹10,000 → FIELD;
   - tier 2, or preferred_language other than English/Hindi, or segment micro → PARTNER (local, same language);
   - otherwise → INSIDE_SALES.
3. Endpoints (router already depends on common.auth.require_backoffice_key):
   - /leads: dropped leads whose drop_reason is fixable by the digital journey or by contact (no time for a visit, visit not scheduled, quote too complex, quote took too long, missing documents, paperwork too long, document details did not match, unreachable, wrong number), ranked by score; supports limit/offset/channel/segment.
   - /handoffs: store.list_handoffs().
   - /kyc-reviews: store.list_kyc_results(["MANUAL_REVIEW", "ACTION_REQUIRED"]) with only the failing checks.
   - /orders: store.list_orders(), masked.
   - /model: metrics plus the top 10 coefficients.
   - /funnel: baseline from data.leads() (5,000 → 3,406 → 1,974 → 861 → 588 → 368) plus live order counts by status.
4. Back-office page (frontend/src/features/backoffice): a passcode gate (keep the key in sessionStorage, try/catch) and tabs Leads to call / Advisor hand-offs / KYC reviews / Orders / Model.
   - Lead rows show a band Pill, score, top factors, a channel badge and the drop reason, with channel and segment filters.
   - Orders rows have an "Advance" button using api.advanceOrder with the back-office key (demo mode).
   - The Model tab states AUC and lift in plain words, plus the caveat "ranks who is likely to activate, not who activates because we call".
   - Desktop-first (the layout is wide on /backoffice) but usable on a phone.
Tests (backend/tests/test_ws5_leads.py): no leakage columns in the feature list; time-split AUC ≥ 0.65; the channel rule on 4 example leads; 401 without the key.
```

### WS6: Submission pack (no ports)

```
WORKSTREAM WS6 — Submission pack: deck, architecture diagram, privacy note, demo script, metrics. Time box 2.5 h.
You own: docs/deck/*, docs/architecture/*, docs/privacy/*, docs/demo-script.md, docs/metrics.md. Do not touch code. The case brief and the official template are in docs/case/ (Airtel_SYNC_Case.pdf, "Submission Template_Sync.pptx": two image-only slides, a title background and a content background).

Build:
1. docs/architecture/architecture.mmd (Mermaid) plus an exported architecture.svg or .png: phone SPA (EN/HI, voice) → one FastAPI app (rules engine; advisor with Groq → Gemini → rules fallback; Smart KYC with RapidOCR and the mock GSTIN/Udyam registries; orders + tracker; back office with a lead score) → SQLite + the case CSVs. Label the data flows: what personal data moves where; documents are processed in memory only; the LLM sees only the business description.
2. docs/privacy/privacy-note.md and a one-page privacy-note.pdf covering:
   - consent per purpose (versioned, EN/HI, withdraw = delete);
   - data minimisation (only what each step needs; Aadhaar never collected);
   - photos read in memory and never stored;
   - retention (180 days after activation, 30 days if rejected);
   - masking of GSTIN/Udyam/ID/phone in the UI and logs; phone encrypted at rest;
   - the LLM receives only the business description, never IDs or images;
   - back office behind a passcode; synthetic data only;
   - what production would add: DigiLocker pull, Aadhaar e-sign, audit log, role-based access.
3. docs/metrics.md and the deck: a business case in ≤ 10 slides on the template backgrounds (title, then content). Slides:
   - the problem, in the data;
   - target segments and their bundles;
   - the journey (screenshot placeholders);
   - how the advisor stays safe (rules decide, the LLM talks);
   - Smart KYC + DPDP;
   - field force and partners (FIELD for multi-site, manufacturers and bundles ≥ ₹10k; PARTNER for tier-2, regional-language and micro, with an assisted-sale commission; SELF_SERVE_LINK for unreachable leads);
   - metrics and targets;
   - rollout (pilot in 2 tier-1 + 2 tier-2 cities over 8 weeks);
   - risks and mitigations;
   - economics.
   Use only the numbers below (from smb_leads.csv) and label every projection as an assumption.
Facts:
- Funnel 5,000 → 3,406 → 1,974 → 861 → 588 → 368 (7.4%).
- 17.6 days lead → activation. 3.0 status calls per activated customer. Blended acquisition cost ₹15,053 per activation.
- GSTIN leads activate at 9.6% vs 2.0% without.
- Segments (share of leads / activation / median monthly bundle / 6-month churn):
  - Micro retail 54% / 4.1% / ₹2,470 / 23%
  - Professional offices 25% / 11.1% / ₹6,575 / 14%
  - Multi-site 15% / 11.0% / ₹28,080 / 11%
  - Manufacturers 6% / 12.8% / ₹15,910 / 8%
- Sources (activation, cost per lead):
  - Field sales 7.3% ₹1,769; Channel partner 8.0% ₹1,672; Website form 4.3% ₹274
  - Inbound call 9.5% ₹487; Referral 14.8% ₹605; WhatsApp campaign 2.8% ₹112
- Top drop reasons:
  - Unreachable after 3 attempts 805; Owner had no time for a visit 531; Not interested on first call 470; Price too high 414
  - Locked in with current provider 325; Wrong or invalid number 319; Visit not scheduled by sales 296; Only wanted a mobile plan 280
  - Competitor cheaper 207; Quote too complex 206; Quote took too long 179; Installation delayed beyond 21 days 98
  - Missing GST or Udyam document 94; Paperwork too long 79; Signatory not available 53; Document details did not match 47
- Journey-fixable drops (visit / no time / quote / paperwork / documents / install delay) ≈ 1,583, plus 1,124 unreachable or wrong-number leads that a self-serve link can reach.
Proposed targets (label as targets): lead → activation 7.4% → 12%; time to activate 17.6 → ≤ 7 days; acquisition cost ₹15,053 → ≤ ₹8,000; status calls 3.0 → ≤ 0.5; 6-month churn ~15% → ≤ 10%.
Priority: lead with Professional offices (highest value per effort, medium price sensitivity, ready for digital), with Micro retail as the volume play through self-serve and partners; multi-site and manufacturers stay field-assisted.
4. docs/demo-script.md, a 2:50 narrated path with what to type or click and timings:
   - Hindi voice question for a dental clinic → recommendation with reasons;
   - switch on CCTV and see the dependency notice → confirm the order;
   - consent → sample K11 (stale bill → retake), then K03 (verified);
   - tracker: book a slot, demo-advance to live;
   - back office: ranked leads with scores and channels.
Build the deck as a .pptx from the template, either by hand or with python-pptx in a throwaway venv outside the app's requirements, and export a PDF. Leave clearly marked screenshot placeholders for integration.
```

## 4. Phase 2: integration (back on `main`, after the workstreams)

1. **Merge** in order WS1 → WS4 → WS2 → WS3 → WS5 → WS6. Before merging each one:
   - Rebase the branch on `main`.
   - Apply any rows in `CHANGE_REQUESTS.md`.
2. **Run the checks once each:**
   - `cd backend && .venv/bin/python -m pytest`
   - `backend/.venv/bin/python scripts/kyc_eval.py`
   - `backend/.venv/bin/python scripts/advisor_scenarios.py`
   - `npm --prefix frontend run build`
3. **Walk the demo script** at phone width, and fix only what breaks the demo path.
4. **Deploy:**
   - Multi-stage Dockerfile: node builds `frontend/dist`; then `python:3.12-slim` with `libgl1 libglib2.0-0` (RapidOCR pulls in `opencv-python`) serves `/api` and `dist` through uvicorn.
   - Render web service with the env vars from `.env.example`.
   - Wake it before judging.
5. **Finish the submission:** record the ≤ 3 min video, drop screenshots into the deck, and update the README.
