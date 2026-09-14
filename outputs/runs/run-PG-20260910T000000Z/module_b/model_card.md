# Model card — module B (v1.0.0)

- run_id: run-PG-20260910T000000Z-B
- target: FIRST_OBSERVED_POSITIVE_ALLOCATION_OR_NO_PAYMENT_CLOSURE
- landmark: 7 days after first observable submission
- horizon H: 30 days; interval: 1 day
- data: de-identified participating-site records (site tokens CPL/TRI/NDX).

## Snapshots and labels
{
  "payment": 558,
  "still_open": 410,
  "close_no_payment": 7
}

## Models
{
  "B0_age_stage_baseline": {
    "status": "FITTED",
    "log_loss": 0.37381408128689375,
    "brier_three_class": 0.21513731148485984,
    "n": 870,
    "snap_brier": 0.489501389337307,
    "snap_log_loss": 0.6918389741084606,
    "n_snapshots": 195,
    "n_abstain": 0
  },
  "B1_discrete_multinomial": {
    "status": "FITTED",
    "log_loss": 0.37788321971409716,
    "brier_three_class": 0.21780979259429323,
    "n": 870,
    "snap_brier": 0.5058119226999702,
    "snap_log_loss": 0.7098226449896026,
    "n_snapshots": 195,
    "n_abstain": 0
  },
  "C1_quality_augmented": {
    "status": "FITTED",
    "log_loss": 0.37778209845135086,
    "brier_three_class": 0.2177666227365402,
    "n": 870,
    "snap_brier": 0.505904011902689,
    "snap_log_loss": 0.7091348376799902,
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
