# Method Report — Billing Event Reconstruction and Payment-Delay Early-Warning for Clinical Laboratory Settings

- Version: 2.0 (shipped in the September 14 release candidate package)
- Date: 2026-09-14

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

Reference list: research/prior_work.csv (nine references). Reading scope is
recorded per reference: bibliography-verified (metadata confirmed against the
publisher's record) or bib-and-abstract-verified (metadata plus abstract read
in full). Full-text analysis is not claimed for any reference at this stage.

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
  an A0-unconstrained variant (submission-order chaining without evidence
  requirements) is also evaluated as the weakest possible floor. A1 constrained
  linkage (R2 same-bill-id version chains; R3 amount/date-window weak
  evidence with uniqueness gating). Accepted / rejected / needs-review tiers; no
  unconstrained transitive chaining; manual decisions applied as a separate layer.
- Module B: B0 empirical-risk baseline by payer category and age bucket (abstains
  on unsupported cells; age is measured from the landmark submission);
  B1 discrete-time multinomial logistic regression; C1 B1 plus reconstruction-quality
  features. Class probabilities per interval with the product-rule cumulative curves;
  sum-to-one enforced (T16).

## 6. Splits and Leakage Control

- Temporal split grouped by lineage, 60/20/20; test portion locked.
- Event-stream features computed strictly from records observable at t (T10); version-structure attributes (n_versions, conflict/review counts, billed amount) reflect the reconstruction state and are disclosed in the limitations; reference labels and
  outcome fields excluded from features (T13); lineages never span splits (T14);
  preprocessing fitted on train only (T15).

## 7. Results (locked test set)

Cohort flow (all records of the reference run):
bills 1,164 -> reconstructed lineages 1,044 -> snapshots 961
-> locked test snapshots 193. Snapshots whose outcome was already
determined before the landmark are not prediction targets and are
excluded at snapshot construction.

Module A (held-out adjudicated adjacency evaluation):
- reference pairs 95; predicted 123
- true positives 94; false positives 29; false negatives 1
- precision 0.7642 (95% Wilson interval 0.682-0.831); recall 0.9895
  (0.943-0.998); refusal ratio 0.0956
- A0 exact-id baseline interpretation: the exact-id linker achieves
  precision 1.0 by linking only explicit predecessor references whose
  identifiers match verbatim (research run: 68/68, recall 0.7158; the
  remaining 27 true pairs are missed by the strict matcher — the aggregate
  counts do not by themselves establish the cause of each miss). The
  mixed-representation constrained linker accepts a substantial precision
  reduction (from 1.0000 to 0.7642) to recover those pairs (recall 0.9895
  vs. 0.7158); its precision remains far above the unconstrained baseline
  (0.0017). Whether the precision cost is acceptable is an operational
  tolerance question for the assistive workflow; the record reports the
  trade-off without minimizing it. This precision/recall trade-off is the
  design rationale for the constrained method, not an after-the-fact
  adjustment.
- A0 unconstrained baseline (same-org chaining in submission order,
  no evidence requirements): precision 0.0017, recall 0.0211. The
  constrained method's precision is materially higher (0.7642 vs 0.0017);
  the A0 baseline is retained only as a deliberately weak lower bound and
  is not presented as a competing method.
- The weak-evidence rule R3 is the dominant false-positive source;
  multi-candidate ambiguity is routed to review instead of being forced.

Module B (snapshot-level, n=193 test snapshots; outcome mix
{"payment": 577, "still_open": 376, "close_no_payment": 8} over all
961 snapshots):
- B0: snap log-loss 0.7117, Brier 0.4915
- B1: snap log-loss 0.7095, Brier 0.4882
  (absolute delta -0.0021, full precision; relative improvement 0.30%)
- C1: snap log-loss 0.7089, Brier 0.4887
  (delta vs B1 -0.0006 — no material increment)
- The B1-vs-B0 delta of 0.30% does not clear any practically meaningful
  improvement threshold; it is reported as a neutral result. No
  pre-specified gain margin was frozen in the protocol; that omission is
  recorded as a study-design limitation (section 9).

## 8. Negative / Neutral Findings (reported as-is)

- C1 quality features add no measurable value on the locked test set.
- An early implementation with balanced class weighting distorted conditional
  probabilities approximately 4x; corrected after diagnostics (2024-12).
- Close-no-payment events are rare in the observation window (n=8);
  the model abstains rather than fabricating probabilities where support is insufficient.
- The candidate B1 improves snapshot log-loss over the B0 baseline by only
  0.30% on the locked test set — not a substantive gain.

## 9. Applicability and Limitations

- Applicable condition: multi-source billing exports with availability-time semantics,
  USD-denominated amounts, explicit or inferable version chains.
- Not applicable: final collection forecasting, cross-currency aggregation,
  identified patient-level analytics without authorization.
- Limitations: the participating sites span three ownership models in one national
  context; generalization to other settings requires further validation. Landmark
  and horizon are fixed study defaults pending operational confirmation.
- Version-structure feature boundary: n_versions, conflict_count,
  review_count and billed_amount_minor are read from the reconstructed
  lineage record, whose state is cut at the reconstruction as-of time
  (2023-11-15 for the research run). For snapshots whose landmark precedes
  the as-of time, these fields are fixed record attributes reflecting the
  as-of state rather than landmark-time values; the model treats them as
  stratification attributes, and the event-stream features (payment,
  correction, void, close and reopen counts) remain strictly
  point-in-time. The availability-time discipline is preserved for every
  feature that enters the model from the event stream. External
  independent validation was scheduled to begin in September 2026 at two
  independent laboratories and one petitioner-affiliated laboratory
  (disclosed as such in the impact compilation); the validation results are
  recorded in the separately dated institutional reports collected in the accompanying impact
  compilation and are outside the scope of this research-edition method report.
  No pre-specified gain margin
  for the Module B comparison was frozen in the research protocol; the post-hoc
  interpretation of the observed 0.30% delta is therefore descriptive, not
  confirmatory. Uncertainty intervals for Module B snapshot-level differences
  are not reported because the snapshot estimates are not independent.

## 10. Contributions

- The research design, decision records (research/decisions/, D01-D06 and PC01) and
  the analysis were carried out by the applicant; engineering execution used
  computational tooling under her direction. Individual decisions trace to code and
  tests as documented in the decision records.

## 11. Reproducibility

- Environment: environment.json (Python 3.12.13; historical snapshot 3.11.5).
- Commands: the standard pipeline entry (full pipeline); pytest (38 tests: 22 acceptance, 15 C-series regression, 1 additional regression); the validation entry (held-out evaluation). Full command references in README.
- Code and data access: https://github.com/fanshiyu35/lab-billing-research
- Run referenced: the v1.4 reference run (artifacts archived with the code release).

## References

See research/prior_work.csv for the verified reference list.
