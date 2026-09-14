# Model card — module B (v1.0.0)

- run_id: run-PM-20260910T000000Z-B
- target: FIRST_OBSERVED_POSITIVE_ALLOCATION_OR_NO_PAYMENT_CLOSURE
- landmark: 7 days after first observable submission
- horizon H: 30 days; interval: 1 day
- data: de-identified participating-site records (site tokens CPL/TRI/NDX).

## Snapshots and labels
{
  "payment": 521,
  "still_open": 354,
  "close_no_payment": 9
}

## Models
{
  "B0_age_stage_baseline": {
    "status": "FITTED",
    "log_loss": 0.41547621407833163,
    "brier_three_class": 0.24679700477863165,
    "n": 747,
    "snap_brier": 0.4736807591577589,
    "snap_log_loss": 0.6797012551140638,
    "n_snapshots": 177,
    "n_abstain": 0
  },
  "B1_discrete_multinomial": {
    "status": "FITTED",
    "log_loss": 0.41544618974610786,
    "brier_three_class": 0.24736011106873174,
    "n": 747,
    "snap_brier": 0.4737079479836324,
    "snap_log_loss": 0.6793584625065465,
    "n_snapshots": 177,
    "n_abstain": 0
  },
  "C1_quality_augmented": {
    "status": "FITTED",
    "log_loss": 0.4155689655302065,
    "brier_three_class": 0.24737341533843893,
    "n": 747,
    "snap_brier": 0.4737921970749083,
    "snap_log_loss": 0.6795792168046096,
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
