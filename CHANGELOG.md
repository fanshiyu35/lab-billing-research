# Changelog

All notable changes to this project are documented in this file.

## [1.3.0] - 2026-06-10

### Changed
- Reports regenerated against the v1.3 pipeline outputs; test suite
  re-run after dependency refresh (Python 3.12.13, scikit-learn 1.9.1).
- Review packet rebuilt with current screenshots.

## [1.2.0] - 2026-02-14
- Validation script hardened: adjacency truth derivation now tolerates
  non-numeric version ids; refusal ratio includes review queue.

## [1.1.0] - 2025-11-10
- Personal research records organized (contribution index, decision
  register); external handoff notes added.
- Method report v1.1 issued with the 2025-08 validation numbers.

## [1.0.0] - 2025-05-20

### Added
- Validation suite v1.0 against hidden ground truth (module A
  precision/recall; module B ablations).
- Full-pipeline entry, Streamlit interface, Power BI adapter
  materials, acceptance tests T01-T25.

### Research findings (reference data, locked test set)
- Module A: recall 0.99, precision 0.76; weak-evidence rule R3 accounts
  for most false positives; multi-candidate refusals 9.6%.
- Module B: B1 improves snapshot log-loss 9% over B0; C1 quality
  features add no incremental value.

## [0.9.0] - 2025-03-10
- Streamlit interface v1.0; Power BI adapter (native .pbix NOT_BUILT).

## [0.7.0] - 2024-12-15
- Module B v1.0: B0/B1/C1 discrete-time competing-event models;
  snapshot-level evaluation.

## [0.5.0] - 2024-06-10
- Module A v1.0: amounts, as-of truncation, manual decisions.

## [0.4.0] - 2024-03-15
- Constrained linkage rules R2/R3; transitive conflict detection.

## [0.2.0] - 2024-01-25
- Module A v0.2: exact-id baseline.

## [0.1.0] - 2023-11-20
- Data contract, schema validators, data preparation pipeline v0.1.

## [0.0.1] - 2023-09-28

### Added
- Repository and workspace skeleton initialized.
- Initial environment (Python 3.11.5, scikit-learn 1.3.0) captured in environment.json.
- Data governance templates and project state files created.
- configuration separation established (study / identified-data modes) (configs/).
