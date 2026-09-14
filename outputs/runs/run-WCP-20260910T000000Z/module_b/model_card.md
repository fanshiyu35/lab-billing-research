# Model card — module B (v1.0.0)

- run_id: run-WCP-20260910T000000Z-B
- target: FIRST_OBSERVED_POSITIVE_ALLOCATION_OR_NO_PAYMENT_CLOSURE
- landmark: 7 days after first observable submission
- horizon H: 30 days; interval: 1 day
- data: de-identified participating-site records (site tokens CPL/TRI/NDX).

## Snapshots and labels
{
  "payment": 709,
  "still_open": 459,
  "close_no_payment": 9
}

## Models
{
  "B0_age_stage_baseline": {
    "status": "FITTED",
    "log_loss": 0.45031664753088463,
    "brier_three_class": 0.2747212555589652,
    "n": 964,
    "snap_brier": 0.45256949618066755,
    "snap_log_loss": 0.6557858409756108,
    "n_snapshots": 236,
    "n_abstain": 0
  },
  "B1_discrete_multinomial": {
    "status": "FITTED",
    "log_loss": 0.4509101893303061,
    "brier_three_class": 0.2756438925047948,
    "n": 964,
    "snap_brier": 0.45743452314827326,
    "snap_log_loss": 0.6603241491297168,
    "n_snapshots": 236,
    "n_abstain": 0
  },
  "C1_quality_augmented": {
    "status": "FITTED",
    "log_loss": 0.45085153122731664,
    "brier_three_class": 0.2756216746608152,
    "n": 964,
    "snap_brier": 0.4573326745734148,
    "snap_log_loss": 0.6601006320809859,
    "n_snapshots": 236,
    "n_abstain": 0
  }
}

## Interpretation
- Probabilities are model outputs conditioned on interval features; they
  are not guarantees and not a claim of final collection.
- ABSTAIN means the model declined to predict (insufficient data or no
  fitted model); no fabricated probabilities.
- Censored observations never contribute negative labels.
