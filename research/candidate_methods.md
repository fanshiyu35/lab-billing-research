# Candidate methods (P01, protocol v1.0)

## Research questions

- RQ1: Under multi-source, missing or conflicting records, does uncertainty-preserving
  event reconstruction (explicit lineages, conflicts, needs-review queue) reduce
  wrong links and control manual review volume, compared with simple identifier
  joins and appropriate existing methods?
- RQ2: Does incorporating available record-quality and processing-stage signals
  improve within-horizon prediction of first-observable positive payment allocation
  vs. no-payment closure vs. still-open, relative to aging-rule and basic baselines?

Both are hypotheses to be tested, not established improvements.

## Module A candidates (reconstruction)

### A0 - exact_id baseline
- Inputs: native previous_record_id plus confirmed mappings only.
- Decision: link when explicit reference exists and passes org/currency/time sanity checks.
- Failure condition: broken or circular references surface as conflicts.
- Cost: trivial. Source: standard deterministic join.

### A1 - constrained_linkage candidate
- Candidate generation from business references, date windows and amount patterns
  within org + source system; never across orgs; never on payer/service token alone.
- Rules carry ID, input dependencies, action, conflict priority and provenance.
- Multi-candidate ambiguity is preserved as needs_review instead of forced picks.
- Confidence scores labeled UNVALIDATED unless calibrated.
- Difference vs A0: higher coverage with an explicit uncertainty tier and
  downstream conflict/amount consistency checks.

## Module B candidates (prediction)

### B0 - empirical-risk rule baseline
- Transparent rules or training-set empirical risk by payer category and aging bucket.
- Rules are not probabilities; empirical risk states its sample support.

### B1 - discrete multinomial baseline
- Discrete-time competing-event model: per-day interval conditional probabilities
  (payment / close-no-payment / none) from t-time features only as specified at protocol freeze; the implemented version-structure boundary is disclosed in the method report limitations.
- S(0)=1; F_payment(h)=sum_{k<=h} S(k-1) p_payment(k); F_close analogously;
  S(h)=S(h-1) p_none(h); class probabilities sum to 1 at every step.

### C1 - quality-augmented candidate
- Same modeling frame as B1 plus reconstruction-quality / missingness / conflict
  features, specified at protocol freeze as computed strictly from data
  available at t; the implemented version-structure boundary (reconstruction-
  state attributes) is disclosed in the method report limitations.
- Explicitly a candidate to be tested; not claimed original in advance.

### C2 (optional)
- Only if an independent reason appears (e.g. demonstrated non-linearity B1 cannot
  capture). Not added for appearance.

## Evaluation
- Module A: precision/recall on adjudicable samples, wrong-merge/split counts,
  refusal ratio, coverage; unlabeled and unknown reported separately.
- Module B: log-loss, three-class Brier score, grouped calibration, class counts,
  refusal/censoring proportions; H-horizon metrics restricted to known-outcome
  or fully-covered cases with the selection disclosed.
- Ablations: drop quality features (C1 vs B1); use baseline reconstruction feeding B1.
