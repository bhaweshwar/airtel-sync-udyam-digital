# Change requests

Append-only. A workstream that needs a change to a shared (Phase 0) file adds an entry here instead of editing the file, then works around it locally. Changes are applied on `main` during integration.

| Date | From | File | Change needed | Why | Status |
|---|---|---|---|---|---|
| 2026-11-06 | WS2 | backend/app/store.py, backend/app/db.py | Add an encrypted `phone_enc` + `phone_masked` column to `handoffs` and a `phone` argument to `store.save_handoff`. | `HandoffRequest.phone` has nowhere to go, so the back office can't call the owner back from a hand-off row. WS2 currently ignores the phone. | open |
| 2026-11-06 | WS2 | .claude/launch.json | Add per-workstream entries (e.g. `ws2-api` on 8002 serving the built frontend) or read the port from `API_PORT`. | Every entry is hard-wired to 8000/5173, which workstreams must not use. | open |
