# Power BI schema and relationships

## Tables imported (from a run's module_a / module_b outputs)

| Table | Key | Import file |
|---|---|---|
| Bills | record_id | outputs/runs/<run>/data/bills.csv |
| Events | event_id | outputs/runs/<run>/module_a/events_normalized.csv |
| Allocations | allocation_id | outputs/runs/<run>/module_a/allocations_normalized.csv |
| Lineages | lineage_id | outputs/runs/<run>/module_a/lineages.csv |
| Predictions | snapshot_id | outputs/runs/<run>/module_b/predictions.csv |

## Relationships

- Lineages[lineage_id] --1:N-- Bills (via record_ids membership; for Power BI,
  expand lineage record_ids into a bridge table LineageMember[lineage_id,
  record_id] and join Bills[record_id] to LineageMember[record_id]).
- Events[bill_record_id] --N:1-- Bills[record_id] (nullable; payments attach
  via Allocations instead).
- Allocations[payment_event_id] --N:1-- Events[event_id].
- Allocations[bill_record_id] --N:1-- Bills[record_id].

Currency and as_of must not be mixed across tables; measures filter a single
currency and a single as_of/run.

## Cardinality rules

- bill counts, lineage counts and payment-event counts are different
  measures; never add rows from repeated event rows directly.
- Cross-currency rows are excluded, not converted.
