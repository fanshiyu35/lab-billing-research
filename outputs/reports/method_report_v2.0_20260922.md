# Method Report — Billing Event Reconstruction and Payment-Delay Early-Warning for Clinical Laboratory Settings

- Version: 2.0
- Date: 2026-09-22

---

## 1. Research Questions

- RQ1: Under multi-source, missing or conflicting records, does uncertainty-preserving
  event reconstruction (explicit lineages, conflicts, needs-review queue) reduce wrong
  links and control manual review volume, compared with simple identifier joins and
  appropriate existing methods?
- RQ2: Does incorporating available record-quality and processing-stage signals improve
  within-horizon prediction of first-observable positive payment allocation vs. no-payment
  closure vs. still-open, relative to aging-rule and basic baselines?

## 2. Related Work and Position

- Fellegi & Sunter (1969): decision-theoretic record linkage with a possible-link
  disposition; the needs-review tier operationalizes this disposition.
- Christen (2012) and van der Aalst (2016): general matching and event-log analysis;
  this work adds billing-domain event semantics and as-of point-in-time discipline.
- Deep Claim (arXiv:2007.06229): predicts payer responses pre-submission from claims;
  this work differs in scope: post-submission billing-event reconstruction plus an
  observation-window-aware competing-event forecast.
- Fine & Gray (1999) / Kaplan & Meier (1958): competing-risk and censoring foundations;
  a discrete-time interval formulation is adopted for irregular observation.
- Zeng et al. (2007), Schoonbee (2022): invoice-lateness prediction; the aging baseline
  is informed by these, with explicit censoring treatment added.

Full scan: research/prior_work.csv (nine references, verified).

## 3. Data and Permissions

- The study uses de-identified billing event records from three participating clinical
  laboratory organizations, referred to by site tokens CPL, TRI and NDX under the
  data-use arrangement. Site tokens are used throughout; organizational identities
  are recorded in the study documentation.
- Data window: 2022-07-01 to 2023-11-15. Records carry per-site local timezones
  (including daylight-saving transitions); submission and payment activity follows
  weekday-dominant rhythms with a mix of same-day and lagged record entry.
- Data quality issues observed and handled: duplicate imports, cross-organization
  duplicate bill numbers, missing correction references, timezone-less timestamps,
  invalid amounts and non-USD currencies. These are isolated by the schema validator,
  never silently repaired, and reported in the run documentation.
- Manually adjudicated reference labels (record pair lineage membership and observed
  outcome times) are held out from all model inputs and used only for evaluation.
- Real-mode processing of identified data remains disabled; see governance/data_permissions.json.

## 4. Event Dictionary and Prediction Target

- Event types: SUBMITTED, CORRECTED, PAYMENT_POSTED, PAYMENT_REVERSED, VOID_VERSION,
  CLOSED_NO_PAYMENT, REOPENED, ADJUSTMENT, STATUS_UPDATED, UNKNOWN (with review).
- Target: within H=30 days after landmark t (first observable submission + 7 days),
  predict the first observable positive payment allocation, first no-payment closure,
  or still-open. Not final bank cash, not full settlement.
- Protocol v1.1 (PC01, 2024-08-06): interval granularity 1 -> 5 days after sparsity
  findings at 1-day resolution.

## 5. Candidate Methods

- Module A: A0 exact-id baseline (native previous_record_id with org/cycle/time checks);
  A1 constrained linkage (R2 same-bill-id version chains; R3 amount/date-window weak
  evidence with uniqueness gating). Accepted / rejected / needs-review tiers; no
  unconstrained transitive chaining; manual decisions applied as a separate layer.
- Module B: B0 age/stage empirical-risk baseline (abstains on unsupported cells);
  B1 discrete-time multinomial logistic regression; C1 B1 plus reconstruction-quality
  features. Class probabilities per interval with the product-rule cumulative curves;
  sum-to-one enforced (T16).

## 6. Splits and Leakage Control

- Temporal split grouped by lineage, 60/20/20; test portion locked.
- Features computed strictly from records observable at t (T10); reference labels and
  outcome fields excluded from features (T13); lineages never span splits (T14);
  preprocessing fitted on train only (T15).

## 7. Results (locked test set)

Module A (held-out adjudicated adjacency evaluation):
- reference pairs 95; predicted 123
- true positives 94; false positives 29;
  false negatives 1
- precision 0.7642; recall 0.9895; refusal ratio 0.0956
- The weak-evidence rule R3 is the dominant false-positive source; multi-candidate
  ambiguity is routed to review instead of being forced.

Module B (snapshot-level, n=206 test snapshots; outcome mix
{"payment": 539, "still_open": 488, "censored": 2, "close_no_payment": 8}):
- B0: snap log-loss 0.736, Brier 0.514
- B1: snap log-loss 0.669, Brier 0.462
  (relative improvement 9.0%)
- C1: snap log-loss 0.668, Brier 0.462
  (delta vs B1 -0.0009 — no incremental value)

## 8. Negative / Neutral Findings (reported as-is)

- C1 quality features add no measurable value on the locked test set.
- An early implementation with balanced class weighting distorted conditional
  probabilities approximately 4x; corrected after diagnostics (2024-12).
- Close-no-payment events are rare in the observation window (n=8);
  the model abstains rather than fabricating probabilities where support is insufficient.

## 9. Applicability and Limitations

- Applicable condition: multi-source billing exports with availability-time semantics,
  USD-denominated amounts, explicit or inferable version chains.
- Not applicable: final collection forecasting, cross-currency aggregation,
  identified patient-level analytics without authorization.
- Limitations: the participating sites span three ownership models in one national
  context; generalization to other settings requires further validation. Landmark
  and horizon are fixed study defaults pending operational confirmation. No external
  independent validation has been completed to date.

## 10. Contributions

- The research design, decision records (research/decisions/, D01-D06 and PC01) and
  the analysis were carried out by the applicant; engineering execution used
  computational tooling under her direction. Individual decisions trace to code and
  tests as documented in the decision records.

## 11. Reproducibility

- Environment: environment.json (Python 3.12.13; historical snapshot 3.11.5).
- Commands: the standard pipeline entry (full pipeline); pytest (22 acceptance
  tests); the validation entry (held-out evaluation). Full command references in README.
- Code and data access: https://github.com/fanshiyu35/lab-billing-research
- Run referenced: the v1.4 reference run (artifacts archived with the code release).

## References

See research/prior_work.csv for the verified reference list.
