# Synthetic dataset business intelligence

Source data: synthetic, Apr?Jun 2026. Denominator for conversion is all 5,000 leads; stage counts use non-empty stage date.

## Funnel

| Stage | Leads | Conversion from prior stage |
|---|---:|---:|
| Lead | 5,000 | ? |
| Contacted | 3,406 | 68.1% |
| Needs assessed | 1,974 | 58.0% |
| Quote accepted | 861 | 43.6% |
| KYC complete | 588 | 68.3% |
| Activated | 368 | 62.6% |

Lead-to-activation is 7.36%. Largest loss proportionally is Needs assessed ? Quote accepted (43.6%).

## Conversion by segment

| Segment | Leads | Activated | Activation rate |
|---|---:|---:|---:|
| Micro retail & services | 2,709 | 110 | 4.06% |
| Professional offices | 1,247 | 138 | 11.07% |
| Small manufacturers | 289 | 37 | 12.80% |
| Small multi-site businesses | 755 | 83 | 10.99% |

## Lead source

| Source | Leads | Activated | Rate |
|---|---:|---:|---:|
| Channel partner | 1,010 | 81 | 8.02% |
| Field sales | 1,720 | 125 | 7.27% |
| Inbound call | 504 | 48 | 9.52% |
| Referral | 413 | 61 | 14.77% |
| Website form | 995 | 43 | 4.32% |
| WhatsApp campaign | 358 | 10 | 2.79% |

## Preferred language

| Language | Leads | Activated | Rate |
|---|---:|---:|---:|
| Bengali | 111 | 10 | 9.01% |
| English | 1,168 | 94 | 8.05% |
| Gujarati | 233 | 14 | 6.01% |
| Hindi | 2,137 | 169 | 7.91% |
| Kannada | 253 | 13 | 5.14% |
| Malayalam | 83 | 7 | 8.43% |
| Marathi | 505 | 32 | 6.34% |
| Punjabi | 96 | 4 | 4.17% |
| Tamil | 207 | 9 | 4.35% |
| Telugu | 207 | 16 | 7.73% |

## GSTIN

| Has GSTIN | Leads | Activated | Rate |
|---|---:|---:|---:|
| N | 1,466 | 30 | 2.05% |
| Y | 3,534 | 338 | 9.56% |

## Drop reasons
Among 4,632 dropped leads, most frequent: unreachable after 3 attempts (805), owner no time for visit (531), not interested first call (470), price too high (414), locked with provider (325), wrong/invalid number (319), visit not scheduled (296), wanted mobile-only (280). Other reasons in source include quote complexity/delay, documentation, installation, mismatch and payment issues.

## Activated outcomes
368 activated. Median monthly bundle ?6,900; mean ?12,351. Six-month churn: 56/368 = 15.2%. NPS mean 6.86; promoters (9?10) 67, passives (7?8) 141, detractors (0?6) 160; NPS = -25.3. Acquisition cost: total all leads ?5,539,640; mean per lead ?1,108; among activated lead rows mean ?5,385. This differs from README?s about ?15,000 per activated customer; resolve whether cost definition/denominator is blended allocated spend vs raw row cost.

## Initial segment recommendation (inference, not case mandate)
1. Professional offices: 11.1% conversion, 1,247 leads, 138 activations; meaningful volume and moderate bundle value (median ?6,575), with manageable observed churn (13.8%).
2. Small multi-site: 11.0%, 755 leads, 83 activations; higher median bundle (?28,080), addressing multi-site coordination need; higher cost per activated row (?9,099).
3. Small manufacturers: 12.8%, 289 leads, 37 activations; highest conversion and ?15,910 median bundle, but smallest lead pool and higher observed acquisition cost. Pilot alongside professional offices; validate addressable scale.
Micro retail is largest pool (2,709) but 4.1% conversion and 22.7% churn in activated subset; treat as a redesign/low-price test rather than primary first wave. Language differences are observational and sample sizes vary; do not interpret as causal preference effects.

## Important definition caveats
Funnel conversion is count at each date divided by previous stage count. Segment/source/language/GSTIN rates are lead-to-activation. Costs are dataset row values and may be inconsistent with README?s blended CAC. NPS segmentation uses standard 0?6 detractors, 7?8 passives, 9?10 promoters. Small cohorts are volatile. Synthetic records do not establish real market demand or causal drivers.


## Acquisition-cost reconciliation (corrected)
The `acquisition_cost_inr` column has **0 missing values**. Its sum across all 5,000 lead rows is ?5,539,640. The dataset does not define whether each row is observed cash spend or allocated lead-level spend; call it recorded acquisition spend, not audited actual cash cost.

| Denominator cohort | Count | Cohort spend | Spend / cohort member |
|---|---:|---:|---:|
| All leads | 5,000 | ?5,539,640 | ?1,107.93 per lead |
| Contacted | 3,406 | ?5,205,910 | ?1,528.45 per contacted lead |
| Needs assessed | 1,974 | ?4,534,090 | ?2,296.90 per assessed lead |
| Quote accepted | 861 | ?2,931,980 | ?3,405.32 per accepted quote |
| KYC complete | 588 | ?2,455,080 | ?4,175.31 per completed KYC |
| Activated | 368 | ?1,981,750 | ?5,385.19 within activated rows |

Campaign CAC for a business case should be total cohort spend / activated customers = **?5,539,640 / 368 = ?15,053.37 per activation**, aligning with README?s approximate ?15,000. The ?5,385 figure is a selected-cohort spend average, not acquisition CAC: it excludes costs allocated to leads that did not activate. Stage ratios above use spend only among leads that reached that stage and should not be interpreted as fully-loaded stage CAC.

Segment CAC (all segment spend divided by activated in segment): micro retail ?20,007 (?2,200,780 / 110); professional offices ?10,695 (?1,475,870 / 138); small manufacturers ?15,324 (?567,000 / 37); small multi-site ?15,614 (?1,295,990 / 83). Source CAC: channel partner ?20,851 (?1,688,930 / 81); field sales ?24,335 (?3,041,870 / 125); inbound call ?5,113 (?245,440 / 48); referral ?4,099 (?250,020 / 61); website ?6,352 (?273,120 / 43); WhatsApp ?4,026 (?40,260 / 10). Cohort-level ratios are preferable for comparison; small activations counts create volatility.

### NPS and churn verification
Both columns are populated for all 368 activated leads (no missing values among activated records). Churn = 56 `Y` / 368 = **15.22%**; 312 `N`. NPS uses promoters 9?10 (67), detractors 0?6 (160), passives 7?8 (141); `(67?160)/368 ? 100 = ?25.27`, conventionally **?25**. Mean score is 6.86, which is not NPS. These calculations exclude all 4,632 nonactivated leads whose outcomes are blank.
