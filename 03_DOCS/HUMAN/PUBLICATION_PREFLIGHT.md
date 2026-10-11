# Public Publication Preflight — KTMA_TASK018

This project is being prepared for a **public GitHub repository** at `https://github.com/PSM44/KT.MovemAcc.git`.

## Publication scope

HUMAN authorized preparing a public candidate that includes real financial artifacts, with personal identifiers redacted where detected. Final push authorization is **not granted**.

## Artifact classes

- ORIGINAL_LOCAL: original evidence remains intact in the local workspace.
- PUBLIC_REDACTED_COPY: deterministic copy under `PUBLIC_RELEASE/` with RUT/tax-ID patterns redacted.
- PUBLIC_UNMODIFIED_FILE: proposed public file without transformation.
- EXCLUDED_FILE: caches, runtime environments, temporary probes, secret-like files, or superseded sensitive originals.

## Redacted public copies

- `10_LEGACY/HISTORICAL_REFERENCES/Test1.xlsx` remains original local evidence; public candidate uses `PUBLIC_RELEASE/10_LEGACY/HISTORICAL_REFERENCES/Test1.PUBLIC_REDACTED.xlsx`.
- `10_LEGACY/HISTORICAL_REFERENCES/TesteAcc001.xlsx` remains original local evidence; public candidate uses `PUBLIC_RELEASE/10_LEGACY/HISTORICAL_REFERENCES/TesteAcc001.PUBLIC_REDACTED.xlsx`.

## Status labels

- IMPLEMENTED: PH1 specialist engine and regression suite exist.
- TESTED: PH1 regression tests pass locally.
- PARTIAL: PH2 criteria extraction exists but criteria are not financially approved.
- PENDING: final HUMAN Git transaction authorization.
- FINANCIALLY_APPROVED: none recorded by this task for PH2/FM population.
- NOT_APPROVED: PH2 candidate criteria and FM financial population.

## Gate

Do not run `git init`, `git add`, `git commit`, `git tag`, `git push` or release publication until MORCH/HUMAN completes the final gate.
