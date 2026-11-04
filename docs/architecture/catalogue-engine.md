# Deterministic catalogue engine

## Source and startup

`CsvCatalogueLoader` reads the official 25-row catalogue CSV into an immutable
in-memory `ProductCatalogue` at Spring startup. The default path is
`data/source/dataset/product_catalogue.csv`, configurable with the
`CATALOGUE_PATH` environment variable or `app.catalogue.path` property. The
loader checks required headers, row shape, unique product IDs, enum/value
formats, numeric ranges, dependency references, and dependency cycles. Invalid
input fails startup with a row-specific `CatalogueLoadException`. No source
CSV is copied into the repository.

The source fields map to product identity/category/name/description, catalogue
unit, monthly price minimum and maximum, one-time setup amount, minimum term,
available city tiers, employee/site minimums, GSTIN requirement, pipe-separated
OR dependency alternatives, typical installation days, and optional target
segments. Semicolon-separated set values are parsed as such; blank dependency
and target-segment cells mean no restriction/dependency.

## Eligibility

Each product is evaluated against the submitted profile for city tier,
employee count, site count, target segment when the source specifies one, and
GSTIN where required. The result is `ELIGIBLE`, `INELIGIBLE`, or
`MANUAL_REVIEW`, with machine-readable reason codes and user-readable reasons.
Cancelled or missing required GSTIN is ineligible. Suspended, not-found, or
failed registry status requires manual review unless another hard failure
makes the product ineligible. The engine does not perform registry lookups.

Dependencies are OR alternatives: a bundle containing at least one eligible
selected alternative satisfies the dependent product. Ineligible or
manual-review dependencies do not satisfy it. Product selection IDs must be
unique, and unknown IDs are reported as ineligible. Pricing rejects a bundle
unless all selected products are eligible.

## Bundle price

Prices use `BigDecimal` and two decimal places with HALF_UP rounding. Per-line
monthly minimum and maximum are catalogue rates multiplied by quantity. The
display estimate is their arithmetic midpoint. The one-time setup fee is
charged once per selected product line because the source does not define a
per-unit setup basis. Bundle totals sum the line values. Minimum contract
duration and typical installation duration use the maximum among selected
products; installation durations are not added because the CSV gives no
sequencing/dependency schedule. These are estimates, not persisted quotes.

## Recommendation behavior

The recommendation service first evaluates every product, then selects the
first eligible connectivity choice in a fixed segment-specific preference
order. It adds a segment default and products mapped from requested business
needs, only where the product is eligible and any dependency is already
satisfied in the assembled selection. Per-site catalogue items use the
profile's site count; other items default to quantity one. It then validates
and prices the resulting bundle. If there is no valid purchasable bundle, the
response contains an empty recommendation list and exclusions. Exclusions
include both ineligible and manual-review products with reasons.

This is a deterministic starter policy, not learned ranking. It does not
invent products or prices and does not use an LLM. Segment preference IDs and
need mappings live in `RecommendationService` and should be revised only
against approved product/business requirements.

## HTTP routes

- `GET /api/v1/catalogue/products`
- `GET /api/v1/catalogue/products/{productId}`
- `POST /api/v1/catalogue/eligibility/evaluate`
- `POST /api/v1/catalogue/bundles/validate`
- `POST /api/v1/catalogue/pricing/calculate`
- `POST /api/v1/recommendations`

Profile fields reflect the source rules: `segment`, `businessType`,
`employeeCount`, `siteCount`, `city`, numeric `cityTier`, `state`,
`gstinStatus`, `currentRequirements`, and optional `industryActivity`.
Selections are `{ "productId": "P01", "quantity": 1 }`. The detailed API
records are the source of truth for enum names and response fields. The
recommendation endpoint accepts a profile directly; other bundle routes accept
`businessProfile` and `selections`.

## Known boundaries

The registry is in memory and is reloaded at startup. There is no catalogue
versioning, quote persistence, user/session state, stock/coverage lookup,
external GST verification, authentication, or LLM integration in this phase.
Keep the case CSV local and ignored by Git; treat any modified source data as a
separate, reviewed input rather than editing it in place.
