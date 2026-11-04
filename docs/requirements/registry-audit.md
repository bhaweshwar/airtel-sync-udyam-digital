# Mock registry audit

All records are synthetic. Complete identifiers are excluded from this report. CSV-loaded types are strings; date fields require parsing/validation.

## GST registry

Rows: 3534. Columns: gstin, legal_name, trade_name, constitution, principal_place_of_business, state, registration_date, status. Unique GSTIN: 3534, duplicate IDs: 0, missing cells: 0.
Status distribution: {"Active": 3266, "Cancelled": 167, "Suspended": 101}
Exact identifier matches against nonblank lead GSTINs: 3534 / 3534.

## Udyam registry

Rows: 2723. Columns: udyam_number, enterprise_name, enterprise_type, major_activity, nic_description, state, city, date_of_registration. Unique Udyam numbers: 2723, duplicate IDs: 0, missing cells: 0.
Exact identifier matches against nonblank lead Udyam numbers: 2723 / 2723.

## Lookup API recommendation
Normalize case/whitespace; validate format separately; do exact synthetic registry lookup; return found/not-found, status, registry fields needed for review, source timestamp/version and masked identifier. Do not disclose whether arbitrary identifiers exist to unauthenticated callers. Distinguish inactive/suspended/cancelled status; define status enum and error semantics. Rate-limit, consent-gate, audit access and avoid logging full IDs. Mock results must be visibly labeled synthetic.
