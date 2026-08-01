# Data Card — Participating-Site Billing Event Records

- Version: 2.0 (2026-09-22)

## Sample formation
- 1000 billing lineages from three participating clinical
  laboratory organizations (site tokens CPL / TRI / NDX) with distinct
  ownership profiles.
- Data window 2022-07-01T00:00:00+00:00 to 2023-11-15T00:00:00+00:00; per-site local
  timezones with DST transitions; weekday-dominant submission and payment
  rhythms; a mix of same-day and lagged record entry.
- Outcome mix (adjudicated): payment ~84%, still-open ~10%, no-payment close ~6%.
- Payer mix: commercial ~55%, government ~32%, self-pay ~8%, other ~5%.

## Tables
| Table | Rows |
|---|---|
| bills | 1167 |
| events | 2145 |
| allocations | 883 |
| observation_windows | 6 |

## Data quality issues observed and handled
- duplicate event imports, cross-organization duplicate bill numbers, missing
  correction references, timezone-less timestamps, invalid amounts, non-USD
  currencies — isolated by the schema validator and reported; originals retained.

## Curation
- Invalid rows isolated, never deleted; original records retained.
- Adjudicated reference labels (lineage membership, outcome times) are held out
  from all model inputs and used only for evaluation.

## Limitations
- The three participating sites span three ownership models in one national
  context; distributions here are descriptive of these sites, not claims about
  the broader industry.
- Identified patient data is outside the scope of this dataset.
