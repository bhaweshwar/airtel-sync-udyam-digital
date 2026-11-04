# Module responsibilities

The backend is organized by business capability inside one deployable Spring Boot application. Modules expose application services and DTOs; they do not depend on controller classes in other modules.

| Module | Owns | May depend on | Must not own |
|---|---|---|---|
| `common` | API error model, IDs, clock, shared validation primitives | Framework/config | Business policy for another module |
| `config` | Spring wiring, serialization, security and persistence configuration | Infrastructure | Domain decisions |
| `advisor` | Conversation session, question flow, provider abstraction and explanation assembly | Catalogue application API; LLM adapter | Eligibility, price or KYC decision authority |
| `catalogue` | Product catalogue, hard eligibility, dependency evaluation, reason codes | Catalogue repository | UI presentation or LLM output |
| `quotation` | Quantity validation, quote snapshots, price calculation and expiry | Catalogue API; quote repository | Reinterpreting catalogue eligibility |
| `kyc` | Consent evidence, document inventory, OCR orchestration, field validations and manual-review cases | Registry/OCR ports; KYC repositories | Government verification claims or unconsented processing |
| `order` | Checkout validation and order lifecycle | Quotation API; order repository | Payment credentials in prototype |
| `tracking` | Read-only projection of order events and indicative milestones | Order API/events | Recomputing commercial rules |

Keep domain objects independent from HTTP and SQLite. Controllers translate request/response DTOs and call application services. Adapters implement ports for SQLite, Tesseract, mock registries, and future providers. Create a module package when its first actual behavior is implemented; avoid placeholder classes solely to populate packages.

## Initial package map

`com.udhyam.digital` currently includes `common.health`, `common.api`, and
`catalogue` with `api`, `application`, `domain`, `infrastructure`, and `config`
packages. The catalogue infrastructure loads the CSV into an immutable
in-memory registry at startup. The application layer evaluates eligibility,
dependencies, pricing, and recommendations; the API layer translates JSON.
Advisor, quotation persistence, KYC, order, and tracking modules remain future
work.
