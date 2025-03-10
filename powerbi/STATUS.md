# Power BI native status

PBI_NATIVE_STATUS=NOT_BUILT/NOT_TESTED

This project's development environment is macOS, where Power BI Desktop is
not available (Power BI Desktop requires Windows). The deliverables in this
directory are complete adapter materials: import queries, DAX measures,
relationship documentation, page configuration steps and a verification
checklist.

To produce the native .pbix:
1. On a Windows machine with Power BI Desktop installed, open a new report.
2. Apply powerbi/import_queries.pq in Power Query (Home > Transform data >
   Advanced Editor), one query per table.
3. Paste powerbi/measures.dax measures into the model.
4. Build relationships per powerbi/schema_relationships.md.
5. Configure pages per powerbi/page_config.md.
6. Refresh, compare against backend outputs, then save the .pbix.

No screenshot or renamed archive may substitute for the native file. When a
native .pbix is produced and verified, update this file to NOT_BUILT/DONE
with the verification date and the comparison notes.
