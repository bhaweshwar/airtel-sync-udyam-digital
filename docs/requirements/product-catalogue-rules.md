# Product catalogue rules and deterministic recommendation requirements

All product fields below are transcribed from the synthetic catalogue. Prices are monthly unit ranges; the file does not state how a point in the range is selected.

| ID | Product | Category | Monthly min?max | Setup | Min contract (months) | Tiers | Min employees / sites | GSTIN | Requires one of | Install days | Segments |
|---|---|---|---:|---:|---:|---|---:|:---:|---|---:|---|
| P01 | Biz Fibre 100 | Connectivity | ?999?1199 | ?0 | 12 | 1;2 | 1 / 1 | N | ? | 5 | micro;prof |
| P02 | Biz Fibre 300 | Connectivity | ?1499?1799 | ?0 | 12 | 1;2 | 1 / 1 | N | ? | 5 | prof;multi |
| P03 | Biz Fibre 1G | Connectivity | ?3999?4499 | ?0 | 12 | 1 | 5 / 1 | Y | ? | 7 | prof;multi;mfg |
| P04 | Biz 5G AirFiber 100 | Connectivity | ?899?1099 | ?0 | 6 | 1;2 | 1 / 1 | N | ? | 2 | micro;prof |
| P05 | Internet Leased Line 20 | Connectivity | ?8000?12000 | ?10000 | 12 | 1;2 | 10 / 1 | Y | ? | 21 | mfg;multi |
| P06 | Internet Leased Line 100 | Connectivity | ?25000?35000 | ?15000 | 24 | 1;2 | 25 / 1 | Y | ? | 30 | mfg |
| P07 | Business Postpaid 299 | Connectivity | ?299?399 | ?0 | 1 | 1;2 | 1 / 1 | N | ? | 1 | micro;prof;multi;mfg |
| P08 | Business Postpaid 599 | Connectivity | ?599?799 | ?0 | 1 | 1;2 | 1 / 1 | N | ? | 1 | prof;multi;mfg |
| P09 | Backup 4G/5G Failover | Connectivity | ?499?599 | ?1500 | 12 | 1;2 | 1 / 1 | N | P01|P02|P03|P05|P06 | 3 | multi;prof |
| P10 | Managed SD-WAN | Connectivity | ?2500?3500 | ?5000 | 24 | 1;2 | 10 / 3 | Y | P01|P02|P03|P05|P06 | 14 | multi |
| P11 | Static IP | Connectivity | ?200?300 | ?0 | 12 | 1;2 | 1 / 1 | N | P01|P02|P03 | 1 | prof;mfg |
| P12 | Cloud Telephony / SIP | Communication | ?1000?1500 | ?2000 | 12 | 1;2 | 3 / 1 | Y | P01|P02|P03|P04|P05|P06 | 5 | prof;multi |
| P13 | Toll-free Number | Communication | ?1500?2000 | ?1000 | 12 | 1;2 | 1 / 1 | Y | ? | 3 | multi;prof |
| P14 | Business SMS 10k | Communication | ?1500?2000 | ?0 | 1 | 1;2 | 1 / 1 | Y | ? | 4 | prof;multi;micro |
| P15 | WhatsApp Business API Starter | Communication | ?999?1499 | ?0 | 3 | 1;2 | 1 / 1 | Y | ? | 3 | micro;prof;multi |
| P16 | Cloud Email & Office Suite | Cloud & Productivity | ?125?150 | ?0 | 12 | 1;2 | 1 / 1 | N | ? | 1 | prof;multi;mfg |
| P17 | Cloud Backup 1 TB | Cloud & Productivity | ?499?699 | ?0 | 12 | 1;2 | 1 / 1 | N | ? | 1 | prof;mfg |
| P18 | Website + Domain Starter | Cloud & Productivity | ?299?499 | ?0 | 12 | 1;2 | 1 / 1 | N | ? | 2 | micro;prof |
| P19 | Cloud POS & Billing | Cloud & Productivity | ?599?899 | ?2500 | 12 | 1;2 | 1 / 1 | N | ? | 3 | micro;multi |
| P20 | Endpoint Security | Security | ?99?149 | ?0 | 12 | 1;2 | 1 / 1 | N | ? | 1 | prof;mfg;multi |
| P21 | Managed Firewall | Security | ?1999?2999 | ?4000 | 24 | 1;2 | 10 / 1 | Y | P01|P02|P03|P05|P06 | 10 | mfg;multi;prof |
| P22 | Secure Wi-Fi with Guest Network | Security | ?399?599 | ?1000 | 12 | 1;2 | 1 / 1 | N | P01|P02|P03|P04 | 3 | micro;multi;prof |
| P23 | Cloud CCTV | IoT & Physical | ?199?299 | ?1800 | 12 | 1;2 | 1 / 1 | N | P01|P02|P03|P04|P05|P06 | 4 | micro;multi;mfg |
| P24 | Machine Monitoring IoT | IoT & Physical | ?149?249 | ?3000 | 24 | 1;2 | 10 / 1 | Y | ? | 10 | mfg |
| P25 | Fleet Tracker | IoT & Physical | ?199?299 | ?1500 | 12 | 1;2 | 1 / 1 | N | ? | 3 | multi;mfg |

## Deterministic eligibility and quote sequence
1. Preserve the catalogue as source of truth. Normalize tier and segment tokens, but reject unknown values rather than guessing.
2. For each requested product, require tier in `available_city_tiers`, employee count ? `min_employees`, sites ? `min_sites`; if `requires_gstin=Y`, require a supplied GSTIN whose mock lookup status is active. A format-valid ID alone is insufficient. The README says accept entity character X.
3. Enforce `requires_one_of` against at least one listed product in the same bundle. Apply dependency evaluation after bundle selection; resolve dependencies transitively and prevent cycles (none apparent in this catalogue). Clarify whether the qualifying product must be eligible/quantity-positive and whether dependency is per site.
4. Apply quantities according to `unit`: per site, line, IP, channel, user, account, counter, device, camera, pack, number or vehicle. The catalogue does not specify default/maximum quantities nor whether employee/site counts cap or imply quantities. Ask user or apply an approved rule.
5. Select monthly unit price within range only under an approved pricing policy; quote line monthly = selected unit price ? quantity. Total monthly = sum of lines. One-time setup should be charged once per product order unless per-unit semantics are clarified; catalogue has setup fees but does not say if they scale by quantity. Do not silently add taxes, discounts, prorations, or install charges.
6. Bundle contract duration must satisfy each included product?s `min_contract_months`; use maximum of included minima as safe common term unless the commercial model permits different terms, which is not specified.
7. Show each item, quantity, unit price, monthly line, one-time setup, overall monthly price, contract term and unmet eligibility reason. Recalculate server-side at checkout.
8. Use `typical_install_days` for indicative tracker estimates only; specify whether multi-product estimate is max, critical path or additive before implementation.

## Ambiguities / possible conflicts to resolve
- Price range does not define selection (micro vs negotiated pricing); no tax or discounts.
- Units mix per-site and per-account with no quantity defaults or setup-fee multiplication rule.
- `requires_one_of` is inclusive OR; does not define same location/site, compatibility or whether dependencies themselves require recursive checking.
- GSTIN rule says valid, active; mock registry status values need exact allowed-state mapping.
- Segment eligibility listed as target segments but README eligibility bullet does not clearly say target segment is hard exclusion. Treat as ranking hint until approved.
- tier values only 1/2 in current data; no behavior for unknown or future tiers.
- Product restriction thresholds (employees/sites) have no upper bounds or aggregation semantics for multi-site quantities.
- Minimum terms vary within bundles; term presentation/proration unspecified.
- Typical installation durations conflict with overall stated 10?14 day current journey but are product-level estimates, not guarantees.


## Proposed configurable pricing and bundle policy (owner approval required)

| Decision | Options | Recommendation | Business rationale / consequence |
|---|---|---|---|
| Monthly price point | minimum, midpoint, maximum, segment/negotiated rule | Default to midpoint; display range and label indicative until confirmed | Transparent neutral quote; no hidden discount. Configure per product and segment. |
| Unit quantities | inferred from sites/employees, user input, fixed defaults | Ask quantities by catalogue unit; only auto-suggest per-site qty from site count with user confirmation | Avoid selling under/over scope. Account/pack items default to 1 only after confirmation. |
| Setup fee | once per product, per unit, per site | Treat setup as per purchased unit for unit-based offerings, once for per-account offerings, pending commercial confirmation | Consistent quote math; may overcharge if source intended one-time order fee, so label and configure. |
| Contract | each product term separately, bundle max, common term | Bundle common term = maximum included product minimum | Avoid representing bundle as cancellable before a required item?s minimum. Show term before checkout. |
| Installation ETA | sum, maximum, critical path | Quote maximum product install days as conservative single-site estimate; multi-site stays manual/route-specific | Parallel work can overlap; sum may overstate. Not a service guarantee. |
| Dependency | hard fail, auto-add, warning | Require at least one eligible listed dependency in same bundle; offer auto-add as a preview then require explicit confirmation | Prevent invalid bundle and surprise purchase. Re-evaluate after all toggles. |
| Add-on becomes ineligible | silently remove, keep, block | Block checkout, explain rule and request remove/replace; never silently remove | User retains control and quote remains valid. |

### Numerical examples
- **Midpoint price:** P01 ?999??1,199 gives ?1,099/month. Two sites at one unit/site ? ?2,198/month. If the price is later set to minimum, the same quote is ?1,998; at maximum it is ?2,398.
- **Per-unit setup:** P09 (?499??599/month, ?1,500 setup, per site), two sites ? midpoint ?1,098 ? 2 = ?2,196/month and proposed setup ?3,000. A once-per-order interpretation would instead be ?1,500 setup, which is why the rule must remain configurable and be approved.
- **Account setup:** P19 (?599??899/month, ?2,500 setup, per counter), three counters ? midpoint ?749 ? 3 = ?2,247/month; proposed per-unit setup ?7,500. If catalogue authors intended setup once per account, it would be ?2,500.
- **Contract:** P01 (12 months) bundled with P10 (24 months) ? proposed common term 24 months, not 12.
- **ETA:** P01 (5 days) with P09 (3 days) ? proposed 5-day estimate, not 8; identify it as indicative.
- **Dependency/ineligibility:** P09 requires P01/P02/P03/P05/P06. If all eligible network products are removed, P09 must become ineligible and checkout is blocked until the customer removes P09 or restores a qualifying product.

All these values should live in configuration/catalogue metadata; the original CSV remains unchanged.
