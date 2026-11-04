# Conversational advisor workflow

## Trust and authority

`AdvisorSessionService` owns session continuity and profile merge rules. It
calls `AdvisorModelProvider`; the Gemini REST implementation can propose facts
and wording but cannot invoke tools or mutate catalogue data. Fact candidates
are accepted only when their evidence appears in the current redacted customer
message and their field/value passes deterministic validation. Conflicting
values remain unchanged until the customer explicitly corrects them. GSTIN
status remains self-reported; this flow performs no registry lookup.

The session service requires an explicitly collected segment/business type,
employee count, site count, city, city tier, state and at least one need before
calling `RecommendationService`. City tier is not inferred from a city name.
The existing engine response is returned unchanged. Gemini can add a short
explanation tied to the engine response; candidate product explanations are
accepted only for selected product IDs and commercial-looking text is rejected.
If a provider call fails, the session does not commit that turn and the API
returns a safe retryable error.

## Conversation lifecycle

`POST /api/v1/advisor/conversations` creates an in-memory session, optionally
recording a selected need from the landing page. A message is redacted for
common Indian identity-number, phone and email patterns before it is sent to
the provider or stored. The provider sees the latest 10 redacted turns and the
collected profile. The response includes up to two follow-up questions drawn
from missing or conflicting fields.

Sessions are process-local, limited to 5,000 concurrent records, retain at most
24 redacted messages, and expire after two hours of inactivity. Restarting the
backend clears them. This is prototype-only state management; production needs
authenticated ownership, distributed persistence, explicit retention policy,
rate limiting and operational controls.

## Gemini adapter

`GeminiRestAdvisorProvider` calls Google's documented `generateContent` REST
endpoint over HTTPS. Structured JSON response schemas constrain extraction and
explanation shapes. API key, model name and timeout come from environment
variables. The key is sent in the `x-goog-api-key` header and is not returned,
logged or included in prompts. Timeouts, rate limits, provider errors, invalid
configuration and malformed JSON map to safe API errors. Automated tests use
mocked HTTP and provider responses; they do not use a live key.
