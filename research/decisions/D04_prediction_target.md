# Decision D04 — Prediction target

- Date: 2023-10-09
- Status: applied (real business confirmation still pending; unknowns
  U03/U04)
- Contributor: Applicant

## Background
"Will we get paid" is not directly observable from billing systems:
final cash depends on banking events outside the data. An operationally
actionable target must be labelable from the data itself.

## Options considered
1. Final collection / full settlement prediction.
2. First observable positive payment allocation or no-payment closure
   within a horizon.
3. Total collected amount regression.

## Decision
Option 2: first observable positive allocation or explicit no-payment
closure within H=30 days after landmark t (first observable submission
+ 7 days), with a third still-open class.

## Rationale
Deep Claim's response-date framing (PW06) and competing-risk theory
(Fine & Gray 1999, PW04) support a first-event formulation. Final
collection depends on unobservable events; the first observable event is
both actionable and labelable. The three classes are mutually exclusive
and exhaust the space, which makes the probability constraints testable
(T16).

## Corresponding implementation
- src/lab_billing/forecast/snapshot.py (SnapshotBuilder._label:
  first observable payment / close / still-open; censored when the
  observation window ends before H).
- configs/reference.json prediction block (landmark_days=7, horizon_days=30).

## Verification
- T12 (censored rows never become negatives), T19 (first event only,
  reopen does not rewrite), tests/test_module_b.py.
- Outcome mix on the reference run: 539 payment / 488 still-open / 8 close /
  2 censored snapshots.
