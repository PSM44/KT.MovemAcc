# KT.MovemAcc

Accounting integration workspace for RAW EPLAZA + RAW IMPULSA → PH1 alignment → PH2 criteria → Funding Memo validation → audit/output.

## Public repository preflight

This workspace is being prepared for a **public** repository publication candidate. HUMAN authorized preparation that includes real accounting RAW files, historical workbooks, Funding Memo templates and generated financial outputs. Final public push authorization is **not granted**.

## Current implementation status

- PH1: IMPLEMENTED and regression-tested using real August 2026 inputs.
- PH2 criteria: PARTIAL; extracted/candidate criteria are **not financially approved**.
- FM: VALIDATION-only; no unresolved financial cells should be treated as approved population.
- Git publication: PENDING final HUMAN gate.

## Structure

- `00_GOVERNANCE/`
- `01_CONTINUITY/`
- `02_SKILLS/`
- `03_DOCS/`
- `04_CONFIG/`
- `05_SRC/`
- `06_TESTS/`
- `07_TOOLS/`
- `08_EVIDENCE/`
- `09_SPECIALISTS/`
- `10_LEGACY/`
- `RAW.INPUT/` — real RAW financial inputs authorized for publication preparation.
- `OUTPUT/` — generated financial outputs/validation workbooks.
- `90_RUNTIME/` — local runtime environment; excluded from publication.

## Publication gate

Do not execute `git init`, `git add`, `git commit`, `git tag`, `git push` or GitHub release without explicit final HUMAN authorization.
