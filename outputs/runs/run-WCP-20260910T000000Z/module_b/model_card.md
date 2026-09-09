# Model card — module B (v1.0.0)

- run_id: run-WCP-20260910T000000Z-B
- target: FIRST_OBSERVED_POSITIVE_ALLOCATION_OR_NO_PAYMENT_CLOSURE
- landmark: 7 days after first observable submission
- horizon H: 30 days; interval: 1 day
- data: de-identified participating-site records (site tokens CPL/TRI/NDX).

## Snapshots and labels
{
  "payment": 673,
  "still_open": 463,
  "close_no_payment": 9,
  "censored": 1
}

## Models
{
  "B0_age_stage_baseline": {
    "status": "FITTED",
    "log_loss": 0.4821809307396395,
    "brier_three_class": 0.27734987842783504,
    "n": 924,
    "snap_brier": 0.47373696522832576,
    "snap_log_loss": 0.789862937987002,
    "n_snapshots": 229,
    "n_abstain": 0
  },
  "B1_discrete_multinomial": {
    "status": "FITTED",
    "log_loss": 0.4585216045487647,
    "brier_three_class": 0.27770712088241434,
    "n": 924,
    "snap_brier": 0.4695990057919413,
    "snap_log_loss": 0.6915486510254,
    "n_snapshots": 229,
    "n_abstain": 0
  },
  "C1_quality_augmented": {
    "status": "FITTED",
    "log_loss": 0.45852199163546664,
    "brier_three_class": 0.2777316694801429,
    "n": 924,
    "snap_brier": 0.46959330755191914,
    "snap_log_loss": 0.691423569067588,
    "n_snapshots": 229,
    "n_abstain": 0
  }
}

## Interpretation
- Probabilities are model outputs conditioned on interval features; they
  are not guarantees and not a claim of final collection.
- ABSTAIN means the model declined to predict (insufficient data or no
  fitted model); no fabricated probabilities.
- Censored observations never contribute negative labels.
