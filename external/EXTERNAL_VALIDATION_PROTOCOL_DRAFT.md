# External Validation Protocol — Draft (for future independent execution)

Status: DRAFT / NOT CONFIRMED. This document defines the scope a future
independent party would execute. It is not a signed agreement and no such
execution has taken place.

## Scope
- Software version: v1.1 (see CHANGELOG and environment.json).
- Research questions: RQ1 (reconstruction quality), RQ2 (within-horizon
  prediction) as defined in the method report v1.1.
- Baselines: A0/B0; candidates: A1/B1 (C1 optional ablation).

## Data permitted
- The independent party uses its own billing-event exports or a new
  synthetic set generated with a different seed (not seed 42), mapped to
  the five-table contract in data/dictionary/data_dictionary.csv.
- Processing location, access people and disclosure scope must be
  documented before execution.

## Independent execution
1. Reproduce the pipeline from a clean environment (README, locked
   requirements).
2. Run reconstruction and prediction on their mapped data.
3. Report metrics exactly as defined in scripts/run_validation.py.

## Pre-specified evaluation
- Module A: precision/recall on adjudicated or hidden-truth adjacency,
  refusal ratio.
- Module B: snapshot-level log loss and Brier vs B0/B1 on a locked split.

## Failure and conflict reporting
- Any deviation, failed run, or disagreement is reported verbatim; negative
  or null results are acceptable and expected to be reported as-is.

## Conflict of interest
- The parties' relationship and any payment must be disclosed in the final
  fact sheet.

## Out of scope
- This protocol does not cover clinical claims, real patient data without
  authorization, or any regulatory submission.
