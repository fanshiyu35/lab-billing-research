# Model card — module B (v1.0.0)

- run_id: run-PG-20260910T000000Z-B
- target: FIRST_OBSERVED_POSITIVE_ALLOCATION_OR_NO_PAYMENT_CLOSURE
- landmark: 7 days after first observable submission
- horizon H: 30 days; interval: 1 day
- data: de-identified participating-site records (site tokens CPL/TRI/NDX).

## Snapshots and labels
{
  "payment": 536,
  "still_open": 394,
  "close_no_payment": 8,
  "censored": 2
}

## Models
{
  "B0_age_stage_baseline": {
    "status": "FITTED",
    "log_loss": 0.38324429514861297,
    "brier_three_class": 0.21872372856104408,
    "n": 825,
    "snap_brier": 0.5017352960204527,
    "snap_log_loss": 0.7194320262621744,
    "n_snapshots": 186,
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
