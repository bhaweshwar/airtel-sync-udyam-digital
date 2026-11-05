# Change requests

Append-only. A workstream that needs a change to a shared (Phase 0) file adds an entry here instead of editing the file, then works around it locally. Changes are applied on `main` during integration.

| Date | From | File | Change needed | Why | Status |
|---|---|---|---|---|---|
| 2026-11-05 | WS4 | `backend/tests/test_phase0.py` | In `test_stub_endpoints_answer_in_contract_shape`, replace the 4 `/api/orders` lines (nonexistent quote `Q-1`, order `UD-1`, pin `1234`) with: `store.save_quote(fixtures.quote())`, create the order from `Q-FIXTURE1`, then use the returned `order_id` + `pin` for get / slots / advance. | Real WS4 returns 404 for a missing quote and for a wrong PIN or unknown order (required by the brief), so the stub-shape assertions can no longer pass after WS4 merges. | open |
