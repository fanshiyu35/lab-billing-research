# Protocol Change PC01 — Interval granularity 1 -> 5 days

- Date: 2024-08-06
- Status: applied (protocol v1.1)
- Contributor: Applicant

## Background
The first module B run (2024-08-05) at 1-day granularity produced
unusable models: payment events concentrate around 10-30 days after
submission, so 1-day intervals have >95% none-rows and the conditional
probabilities are numerically unstable (B1 snapshot log-loss 11.3 vs
B0 0.74).

## Options considered
1. Keep 1-day intervals and add heavy class reweighting.
2. Change interval granularity to 5 days (H=30 becomes 6 intervals).
3. Move to a continuous-time model.

## Decision
Option 2, recorded as a protocol change (not a silent edit).

## Rationale
5-day intervals raise per-interval event rates into a learnable range
while preserving within-horizon discrimination. Reweighting alone
(option 1) distorts absolute probabilities — this was later confirmed in
the balanced-class-weighting defect fixed in 2024-12. The change is
versioned in research/protocol_changes.csv so the frozen protocol and
the implementation stay in sync.

## Corresponding implementation
- configs/reference.json prediction.interval_days = 5.
- src/lab_billing/forecast/snapshot.py and models.py interval handling.
- research/protocol_v1.json v1.1 with change_history.

## Verification
- Post-change locked-test metrics (run-20260922T104226Z): B1 snapshot log-loss 0.7095 (B0 0.7117); C1 shows no incremental value (reported as-is).
