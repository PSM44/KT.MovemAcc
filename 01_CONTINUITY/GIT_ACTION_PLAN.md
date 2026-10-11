# GIT ACTION PLAN (AUTHORIZED)

## 01. Initialize
`git init`
`git checkout -b main`

## 02. Staging (Exact Paths)
`git add README.md AGENTS.md ROADMAP.md BACKLOG.md CURRENT_STATE.json NEXT_DAG.md 01_CONTINUITY/GIT_PLAN.md 04_CONFIG/INGESTION_CONTRACT.json 05_SRC/ph1_logic.py 05_SRC/__init__.py 06_TESTS/SYNTHETIC_TEST_SUITE.md 06_TESTS/test_ingestion.py 06_TESTS/test_ph1.py 06_TESTS/__init__.py .gitignore`

## 03. Commit
`git commit -m "KT.MovemAcc Initial Baseline"`

## 04. Remote
`git remote add origin https://github.com/PSM44/KT.MovemAcc.git`
`git push -u origin main`
