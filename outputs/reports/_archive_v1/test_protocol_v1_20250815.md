# Test Protocol — Acceptance Suites T01-T25

- Version: 1.0, frozen 2024-06-10 (T01-T11) and 2024-12-15 (T12-T25)

## Scope
Engineering-correctness tests only. A green suite certifies that the pipeline
behaves per spec; it does not certify research success, author attribution or
filing eligibility.

## Suites
- T01-T11 (module A): duplicate counting, cross-org isolation, version retention,
  multi-candidate review, broken references, partial payments, over-allocation
  blocking, reversals, void-vs-close, late records, timezone/currency handling.
- T12-T19 (module B): censoring discipline, forbidden fields, split integrity,
  train-only preprocessing, probability constraints, insufficient data,
  unseen-payer abstention, first-event-only labeling.
- T20 reproducibility: deterministic generator + fixed seeds.
- T21-T24 (pipeline/report/security): NOT_OBTAINED externals, number traceability,
  synthetic/real separation, formula injection and path traversal blocks.
- T25 full-pipeline smoke: clean outputs tree, demo entry, artifact existence.

## Execution
    python -m pytest -q --junitxml outputs/qa/junit.xml

Report generation: scripts/build_reports.py embeds the junit summary into the
test report. Reference tests must fail when broken rules are injected; no
failure case may be deleted to turn the suite green.
