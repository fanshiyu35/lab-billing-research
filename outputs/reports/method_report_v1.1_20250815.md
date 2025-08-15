# Method Report — Billing Event Reconstruction and Payment-Delay Early-Warning for Clinical Laboratory Settings

- Version: 1.1
- Date: 2025-08-15
- Status: DEMO engineering report. All results are from synthetic data.
- Author-contribution status: DOCUMENTED_PENDING_REVIEW (not yet reviewed by the applicant)

---

# 中文导读

本报告描述一套面向临床检验机构账单数据的研究工具及其演示验证结果。工具包含两个模块：模块A对多源、缺失或冲突的账单记录进行不确定保留的事件重建；模块B在重建结果之上，预测未来30天内业务链首次可观察付款、无款关闭或仍未结案的三类互斥概率。全部结果来自种子42的合成数据，不支持向真实运营外推，也不构成对最终银行回款的预测。演示验证显示：模块A对真实链邻接的召回率0.99、精确率0.76；模块B的离散时间多项模型相较账龄基线在锁定测试集上快照级对数损失改善9%，而加入重建质量特征的候选模型未带来增量。上述为工程验证结论，真实研究与外部验证尚未开展。

---

## 1. Research Questions

- RQ1: Under multi-source, missing or conflicting records, does uncertainty-preserving
  event reconstruction (explicit lineages, conflicts, needs-review queue) reduce wrong
  links and control manual review volume, compared with simple identifier joins and
  appropriate existing methods?
- RQ2: Does incorporating available record-quality and processing-stage signals improve
  within-horizon prediction of first-observable positive payment allocation vs. no-payment
  closure vs. still-open, relative to aging-rule and basic baselines?

Both are hypotheses tested here on synthetic data; neither is an established improvement.

## 2. Related Work and Position

- Fellegi & Sunter (1969): decision-theoretic record linkage with a possible-link
  disposition; our needs-review tier operationalizes this disposition.
- Christen (2012) and van der Aalst (2016): general matching and event-log analysis;
  we add billing-domain event semantics and as-of point-in-time discipline.
- Deep Claim (arXiv:2007.06229): predicts payer responses pre-submission from claims;
  our scope differs: post-submission billing-event reconstruction plus an
  observation-window-aware competing-event forecast.
- Fine & Gray (1999) / Kaplan & Meier (1958): competing-risk and censoring foundations;
  we adopt a discrete-time interval formulation suitable for irregular observation.
- Zeng et al. (2007), Schoonbee (2022): invoice-lateness prediction; our aging baseline
  is informed by these, with explicit censoring treatment added.

Full scan: research/prior_work.csv (nine references, verified).

## 3. Data and Permissions

- DEMO mode only. Synthetic generator v0.1, seed 42, 1000 lineages across three
  fictional site contracts (org tokens CPL/TRI/NDX). No real patient or billing data.
- Business window 2022-07-01 to 2023-11-15; per-site local timezones with DST;
  weekday-dominant submission and payment rhythms; same-day and lagged record entry.
- Injected dirt: duplicate imports, cross-org duplicate numbers, missing references,
  timezone-less timestamps, illegal amounts, non-USD currencies — intercepted by the
  schema validator (run receipt: expected-dirty 40).
- REAL-LOCAL mode remains disabled (governance/data_permissions.json: NOT_OBTAINED).
- Hidden ground truth (true lineage membership and future payment times) is stored
  separately under data/_ground_truth/ and excluded from all model inputs.

## 4. Event Dictionary and Prediction Target

- Event types: SUBMITTED, CORRECTED, PAYMENT_POSTED, PAYMENT_REVERSED, VOID_VERSION,
  CLOSED_NO_PAYMENT, REOPENED, ADJUSTMENT, STATUS_UPDATED, UNKNOWN (with review).
- Target v1 (operational): within H=30 days after landmark t (first observable
  submission + 7 days), predict the first observable positive payment allocation,
  first no-payment closure, or still-open. Not final bank cash, not full settlement.
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
- Features computed strictly from available_at <= t (T10); hidden truth, final payment
  amounts and labels excluded from features (T13); lineages never span splits (T14);
  preprocessing fitted on train only (T15).

## 7. Results (synthetic demo, locked test)

Module A (hidden-truth adjacency evaluation):
- truth pairs 95; predicted 123
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

## 8. Negative / Neutral / Failure Results (reported as-is)

- C1 quality features add no measurable value on the locked test set.
- B1's early implementation with balanced class weighting distorted conditional
  probabilities ~4x; corrected after diagnostics (2024-12).
- Close-no-payment events are rare in the observation window (n=8);
  the model abstains rather than fabricating probabilities where support is insufficient.

## 9. Applicability and Limitations

- Applicable condition: multi-source billing exports with available_at semantics,
  USD-denominated amounts, explicit or inferable version chains.
- Not applicable: final collection forecasting, cross-currency aggregation, real
  patient-level analytics without authorization.
- Limitations: synthetic data only; fixed landmark/H demo defaults; close-class rarity;
  continuous-time extensions not implemented; no external validation obtained.

## 10. Author Contributions and AI Assistance

- Engineering and analysis on this repository were produced with AI assistance; the
  applicant's substantive design decisions, verification and personal contribution are
  tracked in research/research_decisions.csv and evidence/contribution_index.md.
  Attribution status: DOCUMENTED_PENDING_REVIEW.

## 11. Reproducibility

- Environment: environment.json (Python 3.12.13; historical snapshot 3.11.5).
- Commands: scripts/run_demo.py (full pipeline); pytest (22 acceptance tests);
  scripts/run_validation.py (ground-truth evaluation).
- Run referenced here: run-20260922T040752Z-demo

## References

See research/prior_work.csv for the verified reference list.
