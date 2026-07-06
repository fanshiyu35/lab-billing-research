# Decision D01 — Research domain scope

- Date: 2023-09-30
- Status: applied (superseded by none)
- Contributor: Applicant

## Background
At project inception the method could target any high-volume billing
environment. The choice of domain determines the event dictionary, the
data contract and the realism targets of the generator.

## Options considered
1. General healthcare billing (hospitals, clinics, mixed service lines).
2. Clinical laboratory billing.
3. Commercial B2B invoicing (no payer adjudication).

## Decision
Clinical laboratory billing (option 2).

## Rationale
Laboratory billing combines high claim volume with multi-payer
adjudication, frequent corrections and versioned bills, which exercises
the reconstruction problem; it also matches the applicant's professional
context in billing-department business analysis. Deep Claim
(arXiv:2007.06229) and the invoice-lateness literature (Zeng et al. 2007,
Schoonbee 2022) were reviewed as anchors before this choice
(research/prior_work.csv: PW06-PW08).

## Corresponding implementation
- Service mix and pricing in src/lab_billing/schema/synthetic_generator.py
  (SERVICE_MIX: panels, chemistry, molecular, anatomic pathology,
  toxicology, microbiology).
- Site contracts in data/reference/org_profiles.csv.

## Verification
Domain realism checked in the data-quality review of the first generator
run (amount distributions, payer mix, weekday rhythms).
