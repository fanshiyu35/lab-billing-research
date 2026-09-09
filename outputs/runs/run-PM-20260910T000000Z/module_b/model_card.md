# Model card — module B (v1.0.0)

- run_id: run-PM-20260910T000000Z-B
- target: FIRST_OBSERVED_POSITIVE_ALLOCATION_OR_NO_PAYMENT_CLOSURE
- landmark: 7 days after first observable submission
- horizon H: 30 days; interval: 1 day
- data: de-identified participating-site records (site tokens CPL/TRI/NDX).

## Snapshots and labels
{
  "still_open": 359,
  "payment": 491,
  "close_no_payment": 2
}

## Models
{
  "B0_age_stage_baseline": {
    "status": "FITTED",
    "log_loss": 0.41487451756845806,
    "brier_three_class": 0.2225022679340313,
    "n": 760,
    "snap_brier": 0.4932675548048901,
    "snap_log_loss": 0.8390089519103634,
    "n_snapshots": 171,
    "n_abstain": 0
  },
  "B1_discrete_multinomial": {
    "status": "INSUFFICIENT_DATA"
  },
  "C1_quality_augmented": {
    "status": "INSUFFICIENT_DATA"
  }
}

## Interpretation
- Probabilities are model outputs conditioned on interval features; they
  are not guarantees and not a claim of final collection.
- ABSTAIN means the model declined to predict (insufficient data or no
  fitted model); no fabricated probabilities.
- Censored observations never contribute negative labels.
