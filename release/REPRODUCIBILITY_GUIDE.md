# Reproducibility Guide — External Validation

This guide is written for a validator at a participating organization who
receives the technical package and executes the pipeline on their own
mapped billing-event exports.

Release: v1.4.0 (2026-09-22)
Package: lab_billing_research_v1.4.0_technical_package.tar.gz

## 1. What is in the package

- Source code (src/lab_billing/): schema validation, reconstruction
  (Module A), forecast (Module B), provenance tooling.
- Locked environment: requirements.lock.txt (Python 3.12, all pins).
- Reference configuration: configs/reference.json.
- Data contract: data/dictionary/data_dictionary.csv (five tables:
  bills, events, allocations, observation_windows, reference_labels).
- Acceptance suite: tests/ (T01-T25).
- Documentation: README.md, CHANGELOG.md, outputs/reports/ (method
  report v2.0, data card, test protocol).
- Entry points: scripts/run_pipeline.py, scripts/run_validation.py,
  scripts/build_reports.py, scripts/check_release.py.

No private data, credentials or identified records are included.

## 2. Clean-environment setup

    python3 -m venv .venv                      # Python >= 3.12
    .venv/bin/pip install -r requirements.lock.txt

Verify the build:

    .venv/bin/python -m pytest -q --junitxml outputs/qa/junit.xml
    # expect: 22 passed

## 3. Map your exports to the five-table contract

- Use the Field Mapping Worksheet supplied with your validation protocol.
- One row per contract field: your source field, source system, and any
  derivation rule (version ids, availability times).
- Timestamps must be ISO 8601 with timezone. Amounts in integer minor
  units with currency. IDs as strings, leading zeros preserved.
- Fields you cannot provide are marked missing; do not fabricate them.
- Adjudicated same-lineage labels go into reference_labels.csv
  (same_lineage true/false/unknown, adjudication_status confirmed).

## 4. Run the pipeline on your data

    .venv/bin/python scripts/run_pipeline.py \
        --config configs/reference.json \
        --data-dir /path/to/your/mapped/data \
        --as-of 2023-11-15T00:00:00Z

The run directory (outputs/runs/<run-id>/) contains:
- data/ (your mapped inputs, copied in)
- module_a/ (reconstruction outputs: lineages, links, conflicts,
  review_queue, normalized events and allocations, audit json)
- module_b/ (predictions, model card, feature manifest, metrics json)
- run_receipt.json (wall-clock, schema findings, module summaries)

## 5. Evaluate

    .venv/bin/python scripts/run_validation.py --run-dir outputs/runs/<run-id>

Reports module A precision/recall/refusal against your reference labels
and module B snapshot-level metrics per model. Complete the Results
Return Sheet with these numbers, the responsible person, capacity basis
and any deviations.

## 6. Interpretation rules

- A null, negative or inconclusive result is a valid outcome; record it
  as-is. Do not modify ground truth or labels to change results.
- Landmark and horizon defaults (7 / 30 days) may be changed only by
  versioning the protocol; results are not renamed to match an old target.
- Unknown outcome records, censored observations and refused predictions
  are reported as such; they are never relabeled.

## 7. Package integrity

    .venv/bin/python scripts/check_release.py --root .

The release gate verifies the package is complete and self-contained.
