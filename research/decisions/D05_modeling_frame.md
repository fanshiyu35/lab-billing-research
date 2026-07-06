# Decision D05 — Modeling frame for module B

- Date: 2023-10-12
- Status: applied
- Contributor: Applicant

## Background
Observation in billing exports is irregular (late arrivals, gaps, DST),
so continuous-time survival modeling would need assumptions the data
cannot support. An interval formulation matches the daily operational
cadence.

## Options considered
1. Continuous-time proportional-hazards / Fine-Gray regression.
2. Discrete-time competing-event model: per-interval conditional
   probabilities (payment / close / none) with product-rule cumulative
   curves.
3. Static binary classifier at t (payment vs not).

## Decision
Discrete-time competing-event model (option 2).

## Rationale
The product rule S(0)=1; F_payment(h)=Σ S(k-1) p_payment(k); S(h)=
S(h-1) p_none(h) yields three probabilities that sum to one at every
step — a testable invariant (T16). Static classifiers (option 3) cannot
express the time structure of when the first event arrives, which is the
operational question.

## Corresponding implementation
- src/lab_billing/forecast/models.py: B0/B1/C1, cumulative_curves,
  sum-to-one enforcement.
- protocol v1.0 section Module B.

## Verification
- T16 (probabilities non-negative, sum to one, cumulative curves
  correct), tests/test_module_b.py.
- Locked-test snapshot metrics: B1 log-loss 0.669 vs B0 0.736.
