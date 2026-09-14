# Model card — module B (v1.0.0)

- run_id: run-20260922T115514Z-B
- target: FIRST_OBSERVED_POSITIVE_ALLOCATION_OR_NO_PAYMENT_CLOSURE
- landmark: 7 days after first observable submission
- horizon H: 30 days; interval: 1 day
- data: de-identified participating-site records (site tokens CPL/TRI/NDX).

## Snapshots and labels
{
  "payment": 576,
  "still_open": 375,
  "close_no_payment": 8
}

## Models
{
  "B0_age_stage_baseline": {
    "status": "FITTED",
    "log_loss": 0.3986246761194671,
    "brier_three_class": 0.22934425857239368,
    "n": 846,
    "snap_brier": 0.4943193812002867,
    "snap_log_loss": 0.7148682447611714,
    "n_snapshots": 192,
    "n_abstain": 0
  },
  "B1_discrete_multinomial": {
    "status": "FITTED",
    "log_loss": 0.39675153486654724,
    "brier_three_class": 0.22912457318098037,
    "n": 846,
    "snap_brier": 0.4908483777418546,
    "snap_log_loss": 0.7123097346939679,
    "n_snapshots": 192,
    "n_abstain": 0
  },
  "C1_quality_augmented": {
    "status": "FITTED",
    "log_loss": 0.39662935474669936,
    "brier_three_class": 0.229064186674721,
    "n": 846,
    "snap_brier": 0.4914677676105672,
    "snap_log_loss": 0.7124455697623446,
    "n_snapshots": 192,
    "n_abstain": 0
  }
}

## Interpretation
- Probabilities are model outputs conditioned on interval features; they
  are not guarantees and not a claim of final collection.
- ABSTAIN means the model declined to predict (insufficient data or no
  fitted model); no fabricated probabilities.
- Censored observations never contribute negative labels.
