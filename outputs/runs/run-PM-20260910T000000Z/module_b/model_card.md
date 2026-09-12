# Model card — module B (v1.0.0)

- run_id: run-PM-20260910T000000Z-B
- target: FIRST_OBSERVED_POSITIVE_ALLOCATION_OR_NO_PAYMENT_CLOSURE
- landmark: 7 days after first observable submission
- horizon H: 30 days; interval: 1 day
- data: de-identified participating-site records (site tokens CPL/TRI/NDX).

## Snapshots and labels
{
  "payment": 522,
  "still_open": 352,
  "close_no_payment": 9
}

## Models
{
  "B0_age_stage_baseline": {
    "status": "FITTED",
    "log_loss": 0.41727420629201,
    "brier_three_class": 0.2482045900811998,
    "n": 742,
    "snap_brier": 0.4735642963770813,
    "snap_log_loss": 0.6795940948251171,
    "n_snapshots": 177,
    "n_abstain": 0
  },
  "B1_discrete_multinomial": {
    "status": "FITTED",
    "log_loss": 0.41765156351465005,
    "brier_three_class": 0.24897427860321328,
    "n": 742,
    "snap_brier": 0.4743888504944438,
    "snap_log_loss": 0.6799228452001366,
    "n_snapshots": 177,
    "n_abstain": 0
  },
  "C1_quality_augmented": {
    "status": "FITTED",
    "log_loss": 0.41777211908836176,
    "brier_three_class": 0.2489891305137189,
    "n": 742,
    "snap_brier": 0.4744658775697467,
    "snap_log_loss": 0.680180660907574,
    "n_snapshots": 177,
    "n_abstain": 0
  }
}

## Interpretation
- Probabilities are model outputs conditioned on interval features; they
  are not guarantees and not a claim of final collection.
- ABSTAIN means the model declined to predict (insufficient data or no
  fitted model); no fabricated probabilities.
- Censored observations never contribute negative labels.
