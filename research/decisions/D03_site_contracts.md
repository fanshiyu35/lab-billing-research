# Decision D03 — Participating site contracts for the demo data contract

- Date: 2023-10-06
- Status: applied
- Contributor: Applicant

## Background
A single-site dataset would let the tool silently learn site-specific
idiosyncrasies. Multi-site structure forces cross-org identifier
isolation and tests generalization assumptions.

## Options considered
1. One fictional site.
2. Three sites with distinct ownership models.
3. More than three sites.

## Decision
Three sites (option 2): an independent regional laboratory (TRI), a
laboratory within an international diagnostics group (CPL), and a
not-for-profit health-system laboratory (NDX).

## Rationale
Three ownership models across three geographies make cross-org
duplicate-number handling and payer-mix variation structurally testable
without an unmanageable generator surface. Site tokens are used
throughout the data contract; the profiles live in
data/reference/org_profiles.csv.

## Corresponding implementation
- configs/demo.json demo_orgs = ["CPL", "TRI", "NDX"].
- Per-site timezones with DST in synthetic_generator.py (ORG_TZ).

## Verification
- Acceptance test T02 (cross-org same number never links),
  tests/test_module_a.py.
- T06-T08 amount/allocations scenarios run across sites.
