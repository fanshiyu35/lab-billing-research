# Power BI verification checklist

- [ ] All five tables load with correct row counts (match module_a/module_b CSVs).
- [ ] Relationships configured; no ambiguous (many-to-many) joins except the
      LineageMember bridge (one-directional filtering).
- [ ] Measures return the same numbers as forecast_metrics.json and
      lineages.csv aggregates.
- [ ] Currency filter: single currency; cross-currency rows excluded.
- [ ] as_of/run slicer present; mixing runs prevented.
- [ ] Refresh completes without query errors.
- [ ] Native .pbix saved; PBI_NATIVE_STATUS updated to DONE with date and
      comparison notes.

No screenshot or archive-renaming substitutes for the native file.
