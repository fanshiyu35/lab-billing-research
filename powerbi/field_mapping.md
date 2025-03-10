# Field mapping (backend -> Power BI)

| Backend field | PBI column | Notes |
|---|---|---|
| lineage_id | Lineages[lineage_id] | text |
| org_token | Lineages[org_token] | CPL/TRI/NDX |
| status | Lineages[status] | OPEN / CLOSED_NO_PAYMENT / PAYMENT_OBSERVED / REOPENED_OR_POST_CLOSE_PAYMENT |
| gross_posted | Lineages[gross_posted] | integer minor units (USD) |
| record_ids | LineageMember[record_ids] | expanded bridge |
| P_payment_by_H | Predictions[P_payment_by_H] | numeric string in CSV; cast to decimal |
| outcome | Predictions[outcome] | payment / close_no_payment / still_open / ABSTAIN |

Currency: USD only. as_of: per-run; do not mix runs without an explicit
run_id slicer.
