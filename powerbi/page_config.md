# Page configuration steps (Power BI Desktop)

1. **Status page**
   - Cards: Bill Count, Lineage Count, Payment Event Count.
   - Slicer: run_id (from Lineages), org_token.
   - Note box: DEMO / synthetic-only statement.

2. **Reconstruction page**
   - Table: Lineages with gross/reversed/net/unallocated.
   - Bar: lineages by org_token and payer_category.
   - Drill-through: lineage -> member bills (via LineageMember bridge).

3. **Early-warning page**
   - Cards: Avg P_payment_by_H, Avg P_close_no_payment_by_H, Avg P_still_open_by_H.
   - Table: Predictions with outcome vs predicted probabilities.
   - Slicer: outcome.

4. **Test comparison page**
   - Table from module_b/forecast_metrics.json (paste as manual table) with
     snap_log_loss and snap_brier per model (B0/B1/C1).

## Field-to-visual mapping

| Visual | Fields |
|---|---|
| Status cards | measures above |
| Lineage table | Lineages[lineage_id], [org_token], [status], [gross_posted], [net_observed_posted] |
| Prediction table | Predictions[snapshot_id], [outcome], [P_payment_by_H], [P_close_no_payment_by_H], [P_still_open_by_H] |
