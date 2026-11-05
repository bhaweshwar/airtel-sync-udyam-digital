# Metrics and targets

The baseline comes from `data/smb_leads.csv`: 5,000 synthetic small-business leads for Accel Business, April to June 2026, from tier-1 and tier-2 cities. Each target and projection is an **assumption** that the pilot has to prove. None of them is a measured result.

## Baseline: the funnel today

| Stage | Leads | % of previous stage |
|---|---|---|
| Lead | 5,000 | – |
| Contacted | 3,406 | 68% |
| Needs assessed | 1,974 | 58% |
| Quote accepted | 861 | 44% |
| KYC complete | 588 | 68% |
| Activated | 368 | 63% |

Overall lead → activation is **7.4%**. The steepest drop comes between needs assessed and quote accepted.

| Baseline fact | Value |
|---|---|
| Lead → activation, average | 17.6 days |
| Status calls per activated customer | 3.0 |
| Blended acquisition cost per activation | ₹15,053 |
| Activation with a GSTIN / without | 9.6% / 2.0% |

## The five metrics we would run the business on

| # | Metric | Definition | Baseline | Target (assumption) |
|---|---|---|---|---|
| 1 | Lead → activation | Activated leads ÷ all leads in the cohort | 7.4% | **12%** |
| 2 | Time to activate | Days from lead created to service live, average | 17.6 days | **≤ 7 days** |
| 3 | Acquisition cost | Sales, partner and marketing cost ÷ activations | ₹15,053 | **≤ ₹8,000** |
| 4 | Status calls | Customer calls chasing status ÷ activated customers | 3.0 | **≤ 0.5** |
| 5 | 6-month churn | Activated customers who leave within 6 months | ~15% | **≤ 10%** |

Why these five:

- **Conversion and cost** show whether the digital journey replaces expensive visits.
- **Time to activate and status calls** show whether the owner trusts the journey. The tracker exists to drive status calls down.
- **Churn** stops us from buying conversion with bundles that don't fit. The rules engine only offers products a business is eligible for.

## Segments

| Segment | Share of leads | Activation | Median monthly bundle | 6-month churn | Role in the plan |
|---|---|---|---|---|---|
| Micro retail | 54% | 4.1% | ₹2,470 | 23% | Volume play: self-serve and partners |
| Professional offices | 25% | 11.1% | ₹6,575 | 14% | **Lead segment**: digital-ready, medium price sensitivity |
| Multi-site | 15% | 11.0% | ₹28,080 | 11% | Field-assisted |
| Manufacturers | 6% | 12.8% | ₹15,910 | 8% | Field-assisted |

## Lead sources

| Source | Activation | Cost per lead | Cost per activation (derived*) |
|---|---|---|---|
| Field sales | 7.3% | ₹1,769 | ≈ ₹24,200 |
| Channel partner | 8.0% | ₹1,672 | ≈ ₹20,900 |
| Website form | 4.3% | ₹274 | ≈ ₹6,400 |
| Inbound call | 9.5% | ₹487 | ≈ ₹5,100 |
| Referral | 14.8% | ₹605 | ≈ ₹4,100 |
| WhatsApp campaign | 2.8% | ₹112 | ≈ ₹4,000 |

\* Derived as cost per lead ÷ activation rate, so it covers lead cost only. It is a relative comparison between sources, not a full acquisition cost.

## Why people drop out

| Drop reason | Leads |
|---|---|
| Unreachable after 3 attempts | 805 |
| Owner had no time for a visit | 531 |
| Not interested on first call | 470 |
| Price too high | 414 |
| Locked in with current provider | 325 |
| Wrong or invalid number | 319 |
| Visit not scheduled by sales | 296 |
| Only wanted a mobile plan | 280 |
| Competitor cheaper | 207 |
| Quote too complex | 206 |
| Quote took too long | 179 |
| Installation delayed beyond 21 days | 98 |
| Missing GST or Udyam document | 94 |
| Paperwork too long | 79 |
| Signatory not available | 53 |
| Document details did not match | 47 |

- **Journey-fixable: ≈ 1,583 leads.** These are drops for visits, no time, the quote, paperwork, documents and install delay. The advisor, instant quote, Smart KYC and tracker go after these directly.
- **Reachable by a self-serve link: 1,124 leads.** These are the unreachable and wrong-number leads. A link sent by SMS or WhatsApp lets the owner start alone, at any hour.

## How each part of the prototype moves a metric

| Prototype feature | Drop reasons it targets | Metric |
|---|---|---|
| Advisor (EN/HI, voice) + rules engine | No time for a visit, visit not scheduled, only wanted a mobile plan | 1, 3 |
| Instant quote with toggles and plain-language reasons | Quote too complex, quote took too long, price too high | 1, 2 |
| Smart KYC (GSTIN/Udyam lookup, OCR checks, retake hints) | Missing document, paperwork too long, details did not match | 1, 2 |
| Order tracker with self-booked install slot | Install delay, status chasing | 2, 4 |
| Back-office lead score and suggested channel | Unreachable, wrong number, field time spent on cold leads | 1, 3 |
| Eligibility rules (tier, size, GSTIN, dependencies) | Bundles that don't fit and churn later | 5 |

## Illustrative projections (assumptions, not results)

- **Same 5,000 leads a quarter at 12%** would give about 600 activations instead of 368.
- **Acquisition cost at ≤ ₹8,000** would save about ₹7,000 per activation compared with ₹15,053.
- **Status calls at ≤ 0.5** would cut about 1,100 calls a quarter (368 × 3.0) to about 300, even at 600 activations.
- **Months of bundle revenue to recover acquisition cost** (revenue, not margin):

  | Segment | At ₹15,053 | At ₹8,000 |
  |---|---|---|
  | Professional offices | ~2.3 | ~1.2 |
  | Micro retail | ~6.1 | ~3.2 |

  Micro retail only pays back through low-cost channels.

## How the pilot measures them

- Every lead carries a cohort tag (pilot city, channel, segment) and the timestamps the order timeline already records: quote, consent, KYC verdict, slot booked, live.
- Status calls are counted from support tickets tagged with an order ID.
- Pilot cities are compared with matched non-pilot cities over the same 8 weeks.
- Churn is read at 6 months, so the pilot reports an early proxy at 8 weeks: installs live within the promised slot, and the first bill paid.
