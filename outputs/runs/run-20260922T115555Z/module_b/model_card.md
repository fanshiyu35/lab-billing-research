# Model card — module B (v1.0.0)

- run_id: run-20260922T115555Z-B
- target: FIRST_OBSERVED_POSITIVE_ALLOCATION_OR_NO_PAYMENT_CLOSURE
- landmark: 7 days after first observable submission
- horizon H: 30 days; interval: 1 day
- data: de-identified participating-site records (site tokens CPL/TRI/NDX).

## Snapshots and labels
{
  "payment": 577,
  "still_open": 376,
  "close_no_payment": 8
}

## Models
{
  "B0_age_stage_baseline": {
    "status": "FITTED",
    "log_loss": 0.3987372917429596,
    "brier_three_class": 0.2296268893620147,
    "n": 850,
    "snap_brier": 0.49154897182576973,
    "snap_log_loss": 0.7116755492983594,
    "n_snapshots": 193,
    "n_abstain": 0
  },
  "B1_discrete_multinomial": {
    "status": "FITTED",
    "log_loss": 0.3968170477596823,
    "brier_three_class": 0.22941166356118275,
    "n": 850,
    "snap_brier": 0.4882041929015912,
    "snap_log_loss": 0.7095474261306225,
    "n_snapshots": 193,
    "n_abstain": 0
  },
  "C1_quality_augmented": {
    "status": "FITTED",
    "log_loss": 0.3965364386794061,
    "brier_three_class": 0.22928583069884292,
    "n": 850,
    "snap_brier": 0.48867644005549926,
    "snap_log_loss": 0.7089357277319144,
    "n_snapshots": 193,
    "n_abstain": 0
  }
}

## Interpretation
- Probabilities are model outputs conditioned on interval features; they
  are not guarantees and not a claim of final collection.
- ABSTAIN means the model declined to predict (insufficient data or no
  fitted model); no fabricated probabilities.
- Censored observations never contribute negative labels.
