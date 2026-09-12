# Model card — module B (v1.0.0)

- run_id: run-PG-20260910T000000Z-B
- target: FIRST_OBSERVED_POSITIVE_ALLOCATION_OR_NO_PAYMENT_CLOSURE
- landmark: 7 days after first observable submission
- horizon H: 30 days; interval: 1 day
- data: de-identified participating-site records (site tokens CPL/TRI/NDX).

## Snapshots and labels
{
  "payment": 561,
  "still_open": 407,
  "close_no_payment": 7
}

## Models
{
  "B0_age_stage_baseline": {
    "status": "FITTED",
    "log_loss": 0.37866721199938275,
    "brier_three_class": 0.2189282981271632,
    "n": 868,
    "snap_brier": 0.48661693773760745,
    "snap_log_loss": 0.6889301619738549,
    "n_snapshots": 195,
    "n_abstain": 0
  },
  "B1_discrete_multinomial": {
    "status": "FITTED",
    "log_loss": 0.3822374436048067,
    "brier_three_class": 0.22136867104718172,
    "n": 868,
    "snap_brier": 0.501853971320956,
    "snap_log_loss": 0.7054464076400216,
    "n_snapshots": 195,
    "n_abstain": 0
  },
  "C1_quality_augmented": {
    "status": "FITTED",
    "log_loss": 0.38216445689015194,
    "brier_three_class": 0.22131008259883853,
    "n": 868,
    "snap_brier": 0.50180799087198,
    "snap_log_loss": 0.7048925225148981,
    "n_snapshots": 195,
    "n_abstain": 0
  }
}

## Interpretation
- Probabilities are model outputs conditioned on interval features; they
  are not guarantees and not a claim of final collection.
- ABSTAIN means the model declined to predict (insufficient data or no
  fitted model); no fabricated probabilities.
- Censored observations never contribute negative labels.
