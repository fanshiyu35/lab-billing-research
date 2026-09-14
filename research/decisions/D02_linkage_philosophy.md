# Decision D02 — Linkage philosophy

- Date: 2023-10-02
- Status: applied
- Contributor: Applicant

## Background
Multi-source billing records contain genuinely ambiguous cases (same
native number, no explicit predecessor, close amounts and dates). A
linker can either force a single best guess or preserve uncertainty.

## Options considered
1. Forced single-best link for every candidate pair.
2. Uncertainty-preserving tiers: accepted / rejected / needs-review.

## Decision
Uncertainty-preserving tiers (option 2).

## Rationale
Forced picks inject errors silently; downstream amount math and payment
prediction then compound them. The possible-link disposition in Fellegi &
Sunter (1969) is the theoretical basis for an explicit review tier
(research/prior_work.csv: PW01).

## Corresponding implementation
- src/lab_billing/reconstruct/rules.py: R2 version chains and R3
  weak-evidence candidates with uniqueness gating; multi-candidate pairs
  are routed to review_queue instead of being merged.
- Review queue semantics documented in the method report, section 5.

## Verification
- Acceptance tests T04 (multi-candidate needs review) and T05 (broken
  reference flagged) in tests/test_module_a.py.
- Hidden-truth evaluation on the initial implementation sample: recall
  0.99 / precision 0.76 with a 9.6% refusal ratio — high recall with
  controlled review volume was the goal of this choice.
