# Model card — module B (v1.0.0)

- run_id: run-WCP-20260910T000000Z-B
- target: FIRST_OBSERVED_POSITIVE_ALLOCATION_OR_NO_PAYMENT_CLOSURE
- landmark: 7 days after first observable submission
- horizon H: 30 days; interval: 1 day
- data: de-identified participating-site records (site tokens CPL/TRI/NDX).

## Snapshots and labels
{
  "payment": 712,
  "still_open": 454,
  "close_no_payment": 9
}

## Models
{
  "B0_age_stage_baseline": {
    "status": "FITTED",
    "log_loss": 0.45025286881948395,
    "brier_three_class": 0.27477465386828415,
    "n": 957,
    "snap_brier": 0.45116110574385276,
    "snap_log_loss": 0.6543020337465313,
    "n_snapshots": 235,
    "n_abstain": 0
  },
  "B1_discrete_multinomial": {
    "status": "FITTED",
    "log_loss": 0.4507387034856437,
    "brier_three_class": 0.27559846245878084,
    "n": 957,
    "snap_brier": 0.4554132470748415,
    "snap_log_loss": 0.657866770318999,
    "n_snapshots": 235,
    "n_abstain": 0
  },
  "C1_quality_augmented": {
    "status": "FITTED",
    "log_loss": 0.4508205964185302,
    "brier_three_class": 0.2756142635752133,
    "n": 957,
    "snap_brier": 0.4554509398833274,
    "snap_log_loss": 0.6582195476837311,
    "n_snapshots": 235,
    "n_abstain": 0
  }
}

## Interpretation
- Probabilities are model outputs conditioned on interval features; they
  are not guarantees and not a claim of final collection.
- ABSTAIN means the model declined to predict (insufficient data or no
  fitted model); no fabricated probabilities.
- Censored observations never contribute negative labels.
