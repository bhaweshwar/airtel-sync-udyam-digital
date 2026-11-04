# Case requirements audit

## Source and certainty
Source: extracted `Airtel_SYNC_Case.pdf`, data-pack `README.md`, and `Submission Template_Sync.pptx`. Case and dataset explicitly describe fictional/synthetic businesses and values. No Judges Only pack was accessed.

## Problem and required journey
Design a digital-first, phone-friendly acquisition/onboarding path for MSMEs, in the owner?s preferred language, that helps discover, buy and activate a suitable bundle with minimal human effort. Case context states current pain points: salesperson-led needs discovery, 3?5 day quote, paper/email KYC, 10?14 day activation and separate billing/support.

Prototype must cover: (1) conversational GenAI advisor asking about business type, size, locations and current tools, recommending catalogue bundles and explaining why in plain language; (2) quote/checkout with one transparent monthly price and toggleable add-ons; (3) upload/extract/validate KYC with mocked GSTIN and Udyam lookups plus clear consent; (4) order status tracker.

## Business questions / expectations
- Prioritise segments and identify suitable products, price and contract for each.
- Advisor should work in Hindi and regional languages (voice/chat is posed as design direction).
- Make KYC near-instant using examples such as registry lookup, OCR, DigiLocker and e-sign, while addressing DPDP Act 2023 consent, purpose limitation and data minimisation. DigiLocker/e-sign are examples, not mandatory integrations.
- Explain how field sales and channel partners augment the digital journey.
- Define 3?5 success metrics and targets (examples in case: lead-to-activation conversion, time, CAC, 6-month churn). Targets are to be proposed, not provided as fixed requirements.

## Submission requirements
Working prototype, demo video ?3 minutes, code repository; solution architecture diagram; business case ?10 slides covering target customer, value, pricing/savings, rollout and risks; one-page privacy/security note. Template contains two slide XML pages and 11 layouts; extracted slide text is empty. Treat it as a visual/template starting point and inspect in PowerPoint before deciding which layouts to retain.

## Non-functional / explicit data constraints
Mobile-first; preferred-language journey; minimal human effort; transparent pricing; clear consent; purpose limitation and data minimisation; KYC documents securely handled; reports/UI/logs should mask identifiers per README privacy expectations. Dataset is synthetic. README says accept GSTIN embedded PAN entity character X in format validation and use 2026-07-15 as reference date; Udyam district code 00 is synthetic/nonexistent. Address proof age rule: no older than 90 days.

## Not specified by case
No fixed production cloud, model, authentication, encryption standard, retention period, API contract, exact product ranking algorithm, numeric KPI targets, payment provider, tax treatment, bundle discount, or formal KYC pass/fail policy is mandated. Do not present these as competition requirements.
