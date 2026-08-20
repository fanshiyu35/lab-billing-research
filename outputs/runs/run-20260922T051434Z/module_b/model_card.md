# Model card — module B (v1.0.0)

- run_id: run-20260922T051434Z-B
- target: FIRST_OBSERVED_POSITIVE_ALLOCATION_OR_NO_PAYMENT_CLOSURE
- landmark: 7 days after first observable submission
- horizon H: 30 days; interval: 1 day
- data: de-identified participating-site records (site tokens CPL/TRI/NDX).

## Snapshots and labels
{
  "payment": 539,
  "still_open": 488,
  "censored": 2,
  "close_no_payment": 8
}

## Models
{
  "B0_age_stage_baseline": {
    "status": "FITTED",
    "log_loss": 0.35612083962205865,
    "brier_three_class": 0.1970088849864472,
    "n": 934,
    "snap_brier": 0.5144259569702185,
    "snap_log_loss": 0.7357284660871263,
    "n_snapshots": 206,
    "n_abstain": 0
  },
  "B1_discrete_multinomial": {
    "status": "FITTED",
    "log_loss": 0.34103700124049185,
    "brier_three_class": 0.19350587267239963,
    "n": 934,
    "snap_brier": 0.4618050188966311,
    "snap_log_loss": 0.6692132603100102,
    "n_snapshots": 206,
    "n_abstain": 0
  },
  "C1_quality_augmented": {
    "status": "FITTED",
    "log_loss": 0.34073750226710264,
    "brier_three_class": 0.19339754635456916,
    "n": 934,
    "snap_brier": 0.4615831802291266,
    "snap_log_loss": 0.6682848894134452,
    "n_snapshots": 206,
    "n_abstain": 0
  }
}

## Interpretation
- Probabilities are model outputs conditioned on interval features; they
  are not guarantees and not a claim of final collection.
- ABSTAIN means the model declined to predict (insufficient data or no
  fitted model); no fabricated probabilities.
- Censored observations never contribute negative labels.
