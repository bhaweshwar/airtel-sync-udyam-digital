# KYC validation rules (proposed implementation contract)

## Evidence classes
- **Confirmed failure:** deterministic rule fails on reliable extracted value or registry response (e.g. missing required document, inactive GSTIN, mismatch beyond approved normalization).
- **Manual review:** OCR uncertain, authenticity cannot be established, name/address fuzzy match, registry unavailable, image altered/illegible, or signatory authority unclear.
- **Validated field:** extracted value agrees with a successful mock registry lookup and approved rule. This is prototype validation, not real-world identity verification.

## Sequence
1. Present purpose-specific consent; record version, timestamp, actions and scope before upload/lookup. Minimise collected fields.
2. Validate file type/size and malware policy; retain originals only for approved duration. Mask IDs in UI/logs.
3. OCR returns field, page/region, confidence, engine/version; user can correct OCR. Never treat OCR as validity proof.
4. GSTIN: normalize uppercase; format/checksum validation following README exception for embedded entity character X; exact mock registry lookup; status must map to approved active state; compare legal/trade name and state/address. Registry status state mapping requires agreement.
5. Udyam: normalize identifier; exact registry lookup; district code 00 is synthetic and should not trigger real-world validation rejection; compare enterprise name/activity/state/city.
6. Name comparisons use legal entity/proprietor relationship-aware normalization; do not require proprietor?s personal legal name to equal business trade name. Set fuzzy thresholds only after adjudicating specimens.
7. Address proof: identify issue/billing date and compare against 2026-07-15; age ?90 days is README constraint. Define future-date and missing-date handling. Compare locality/state/pincode with declared/registry address; define tolerances.
8. Signatory ID: check readable name, relationship/authority, issue/expiry if present; reference date 2026-07-15. Decide allowed ID document types and expiry behavior.
9. Return per-field statuses with reasons and request resubmission/manual review. Preserve audit trail without full IDs.

The supplied specimens are explicitly synthetic and marked as not valid documents. They are OCR/validation test fixtures, not proof of real KYC completion. Legal/compliance interpretation requires review before production.


## Proposed routing policy (owner approval required)
**Hard fail:** missing required document; specimen/test watermark; GST status Cancelled or Suspended; GST-gated product with no active verified mock record; confirmed invalid checksum after corrected OCR; address proof older than 90 days; confirmed material name/address mismatch; expired ID when expiry is a policy requirement.

**Manual review:** registry not found or unavailable; duplicate/conflicting records; low/uncalibrated OCR confidence; partial ID extraction; fuzzy name/address result; owner/trade/legal-name relationship unclear; ambiguous date or wrapped address; authority not demonstrated. Do not automatically fail a customer solely because a mocked registry does not contain a synthetic ID.

No numeric OCR confidence threshold is supportable yet because this sample has not been labeled/calibrated. First manually label a representative validation set, measure field-level precision/recall, then set thresholds per field; low-confidence values always require correction/review. Consent is required before document processing and separately before each registry lookup. Recommended demo handling: use synthetic-only fixtures, mask all but minimal ID characters, prohibit full identifiers in logs, and delete uploaded originals/OCR derivatives after the approved demo purpose. Exact retention days require privacy/legal owner decision; do not silently retain indefinitely.
