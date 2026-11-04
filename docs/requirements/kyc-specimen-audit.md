# KYC specimen audit ? Phase 1.1

## Method and scope
Inspected all 47 source PNGs for K01?K12 with Tesseract 5.5.3 (PSM 6), then compared OCR candidates with mock registries where extraction was exact. Visually inspected K04 GST because OCR was unusable. OCR confidence was not calibrated; extraction is evidence only, never authenticity. Every image is synthetic specimen material and contains test/specimen markings; therefore document authenticity is **FAIL** for real KYC use, irrespective of field-level extraction. This is a prototype test set, not a valid applicant dossier.

Reference date for address proof: 2026-07-15; allowed age ?90 days. OCR-read dates and computed ages: K01 2026-06-26 (19 days, PASS date rule); K02 2026-05-22 (54, PASS); K03 2026-05-30 (46, PASS); K04 2026-05-28 (48, PASS); K05 2026-06-11 (34, PASS); K06 2026-06-11 (34, PASS); K07 2026-07-05 (10, PASS); K08 2026-05-26 (50, PASS); K09 2026-07-10 (5, PASS); K10 2026-06-18 (27, PASS); K11 2025-10-31 (257 days, FAIL); K12 2026-07-06 (9, PASS). Date outcomes apply only to readable OCR date candidates; manual visual confirmation remains appropriate before real decisions.

## Applicant findings
| Applicant | Confirmed finding | Other field disposition |
|---|---|---|
| K01 | All specimen-only; address date 19 days | GST OCR not exact; registry/status, names and address MANUAL_REVIEW; Udyam OCR MANUAL_REVIEW; signatory synthetic |
| K02 | All specimen-only; address date 54 days; Udyam OCR candidate exact registry match | GST OCR unreadable; GST status/name/address MANUAL_REVIEW; Udyam field match still cannot validate specimen; signatory synthetic |
| K03 | All specimen-only; address date 46 days; Udyam candidate exact match; GST candidate matched Active record | Field values can be registry-consistent, but authenticity FAIL; address/name comparison MANUAL_REVIEW |
| K04 | GST image visually blurred and marked invalid; address date 48 days | GST and Udyam MANUAL_REVIEW/unreadable; name/address checks unresolved; signatory synthetic |
| K05 | Udyam certificate MISSING; address date 34 days; GST candidate matched Active record | Missing Udyam is confirmed FAIL; GST authenticity FAIL; signatory synthetic |
| K06 | All specimen-only; address date 34 days; Udyam candidate exact match | GST OCR not exact; status/name/address MANUAL_REVIEW; signatory synthetic |
| K07 | All specimen-only; address date 10 days; Udyam candidate exact match | GST OCR not exact; status/name/address MANUAL_REVIEW; signatory synthetic |
| K08 | All specimen-only; address date 50 days; Udyam candidate exact match | GST OCR ambiguous; registry candidates include varied statuses, so status MANUAL_REVIEW; signatory synthetic |
| K09 | All specimen-only; address date 5 days; Udyam candidate exact match | GST OCR ambiguous; candidate registry statuses vary, MANUAL_REVIEW; signatory synthetic |
| K10 | All specimen-only; address date 27 days; Udyam candidate exact match | GST OCR ambiguous; candidates include Active/Cancelled/Suspended; MANUAL_REVIEW; signatory synthetic |
| K11 | All specimen-only; address proof is 257 days old, FAIL | Udyam candidate exact match; GST OCR ambiguous; address comparison and GST status MANUAL_REVIEW; signatory synthetic |
| K12 | All specimen-only; address date 9 days; Udyam candidate exact match; GST candidate matched Active record | Registry consistency does not authenticate specimen; address/name comparison MANUAL_REVIEW |

?Exact Udyam candidate match? and ?GST candidate matched Active record? refer to OCR-derived values compared with synthetic registry rows. This supports a field-level mock lookup only, not document validity. Full identifiers are masked in the machine-readable matrix. Name/address values are present as OCR evidence where read; conclusions are MANUAL_REVIEW unless registry and image fields unambiguously agree.

## Planted/observable issues and detection mechanism
- **Specimen authenticity limitation (all applicants):** watermark/text says synthetic/specimen/test-only. Detector: explicit specimen watermark/text flag plus production rejection; do not pass as KYC.
- **Missing Udyam image (K05):** document inventory required by workflow; outcome MISSING/FAIL.
- **Stale address proof (K11):** parse issue/bill date; compare with 2026-07-15; >90 days ? FAIL. OCR date should be manually checked if confidence low.
- **GST registry status cases:** exact lookup after corrected OCR; Active can pass status rule, Cancelled/Suspended fail eligibility, unknown/multiple candidate ? MANUAL_REVIEW. OCR ambiguities prevent safe assignment for K01/K02/K04/K06?K11.
- **Name/address discrepancies and signatory issues:** field-level comparison with registry and other docs, entity-aware name normalization, authority and expiry review. Do not infer planted-case outcomes where OCR or visual evidence is insufficient.
- **OCR/format checks:** use format/checksum and Udyam pattern validation after user correction; README specifically permits GST PAN character X and Udyam district code 00. Checksum passing does not establish authenticity.

The JSON matrix assigns per-field outcomes and evidence. The expected answer key expresses deterministic expected handling, not hidden judges? labels.
