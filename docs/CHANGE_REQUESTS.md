# Change requests

Append-only. A workstream that needs a change to a shared (Phase 0) file adds an entry here instead of editing the file, then works around it locally. Changes are applied on `main` during integration.

| Date | From | File | Change needed | Why | Status |
|---|---|---|---|---|---|
| 2026-11-05 | WS1 | docs/CONTRACTS.md | In "Python interfaces", document `app.engine.price(profile, selected, previous=None)`: the optional `previous` Quote (the one being edited) makes removing a prerequisite also remove its dependants; without it, unmet dependencies get the cheapest eligible prerequisite added. Signature stays backward compatible. | `/api/quote` passes the stored quote for `quote_id`; WS4 re-pricing needs no change. | Open |
| 2026-11-05 | WS1 | .claude/launch.json | Optional: per-worktree launch configs (or env-driven ports). Today it pins 8000/5173, which workstreams must not use, so the browser preview can't start a worktree's own servers by name. | WS1 ran `API_PORT=8001 WEB_PORT=5181 scripts/dev.sh` by hand instead. | Open |
| 2026-11-05 | WS4 | `backend/tests/test_phase0.py` | In `test_stub_endpoints_answer_in_contract_shape`, replace the 4 `/api/orders` lines (nonexistent quote `Q-1`, order `UD-1`, pin `1234`) with: `store.save_quote(fixtures.quote())`, create the order from `Q-FIXTURE1`, then use the returned `order_id` + `pin` for get / slots / advance. | Real WS4 returns 404 for a missing quote and for a wrong PIN or unknown order (required by the brief), so the stub-shape assertions can no longer pass after WS4 merges. | open |
| 2026-11-06 | WS2 | backend/app/store.py, backend/app/db.py | Add an encrypted `phone_enc` + `phone_masked` column to `handoffs` and a `phone` argument to `store.save_handoff`. | `HandoffRequest.phone` has nowhere to go, so the back office can't call the owner back from a hand-off row. WS2 currently ignores the phone. | open |
| 2026-11-06 | WS2 | .claude/launch.json | Add per-workstream entries (e.g. `ws2-api` on 8002 serving the built frontend) or read the port from `API_PORT`. | Every entry is hard-wired to 8000/5173, which workstreams must not use. | open |
