# Research decision records (narrative index)

These records expand research/research_decisions.csv into a
question-and-answer form: what was decided, what the alternatives were,
why this choice, where it lives in the code, and how it was verified.
Each entry traces to specific files and tests so the decision -> code ->
test chain is auditable.

- D01 2023-09-30 domain scope -> synthetic_generator.py SERVICE_MIX
- D02 2023-10-02 linkage philosophy -> reconstruct/rules.py, tests T04/T05
- D03 2023-10-06 site contracts -> configs/demo.json, org_profiles.csv
- D04 2023-10-09 prediction target -> forecast/snapshot.py, tests T12/T19
- D05 2023-10-12 modeling frame -> forecast/models.py, test T16
- D06 2023-10-20 evaluation split -> forecast/pipeline.py, tests T14/T15
- PC01 2024-08-06 interval granularity -> protocol v1.1, protocol_changes.csv
