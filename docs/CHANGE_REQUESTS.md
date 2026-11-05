# Change requests

Append-only. A workstream that needs a change to a shared (Phase 0) file adds an entry here instead of editing the file, then works around it locally. Changes are applied on `main` during integration.

| Date | From | File | Change needed | Why | Status |
|---|---|---|---|---|---|
| 2026-11-06 | WS3 | backend/tests/test_phase0.py | Replace the KYC part of `test_stub_endpoints_answer_in_contract_shape` (lines 86–92): consent with `version = notice["version"]` (currently `"v1"`, which now gets 409 NOTICE_VERSION), and expect 403 CONSENT_REQUIRED for documents/submit/sample when no consent is active. Don't run `sample/K03` there (it runs real OCR); `tests/test_ws3_kyc.py` and `scripts/kyc_eval.py` cover it. | The real KYC endpoints enforce the versioned consent and the 403 consent gate from the WS3 brief, so the stub smoke test now fails by design. | open |
