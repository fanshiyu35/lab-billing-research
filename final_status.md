# Final status — v1.4 (2026-09-22)

## Actually completed
- Full engineering pipeline (module A reconstruction, module B forecast),
  the study dataset (three participating sites), Streamlit interface, Power BI adapter
  materials, method/data/test documentation, review packet, release gate.
- Acceptance suite T01-T25: passing (outputs/qa/junit.xml).
- Validation against hidden ground truth: see
  outputs/runs/<latest>/module_b/validation_report.json.

## Not executed / failed
- Native Power BI .pbix: NOT_BUILT/NOT_TESTED (no Windows/Power BI
  environment).
- REAL-LOCAL pipeline: disabled; data authorization NOT_OBTAINED.

## Study-dataset results
- All quantitative results come from the study dataset of three participating
  sites; inference beyond these sites is not claimed.

## Real research support scope
- None yet. Research-level claims require real authorized data.

## Applicant attribution
- DOCUMENTED_PENDING_REVIEW. The applicant must review and confirm the
  decision register and contribution index before any attribution.

## External materials actually obtained
- None. external/status.json = NOT_OBTAINED.

## Power BI status
- NOT_BUILT/NOT_TESTED (see powerbi/STATUS.md).

## Next human actions
1. Applicant reviews research/research_decisions.csv and
   evidence/contribution_index.md and answers the outstanding unknowns
   (governance/unknowns.csv).
2. Business owner confirms target definition and landmark/H (U03/U04).
3. Decide whether native Power BI delivery is required (U05).
4. If real research proceeds: obtain documented data authorization, then
   follow external/EXTERNAL_VALIDATION_PROTOCOL_DRAFT.md.
