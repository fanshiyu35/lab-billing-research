# Decision D06 — Evaluation split

- Date: 2023-10-20
- Status: applied
- Contributor: Applicant

## Background
Random splits leak: version chains and later events of the same lineage
can land in both train and test. Temporal grouping by lineage prevents
this.

## Options considered
1. Random train/test split at record level.
2. Temporal split grouped by lineage (60/20/20).
3. Group k-fold by org.

## Decision
Temporal 60/20/20 grouped by lineage (option 2), test portion locked.

## Rationale
The same lineage and its corrected versions must never span splits
(T14). Temporal ordering reflects deployment reality (models only see
the past). Org-level k-fold was deferred; the multi-site structure is
instead exercised by the multi-site data contract (D03).

## Corresponding implementation
- src/lab_billing/forecast/pipeline.py temporal_grouped_split.
- Leakage guards T10/T13/T14/T15.

## Verification
- T14 (no lineage across splits), T15 (preprocessing fitted on train
  only), tests/test_module_b.py.
- Split sizes on the reference run: 2,419 train / 846 test interval rows (192 test snapshots).
