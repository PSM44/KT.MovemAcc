# PH1 User Guide

## Purpose
PH1 generates `OUTPUT/2026.08/CAM2026.08_CONSOL.ALIGN.xlsx` from the two RAW August 2026 CUENTAS DE MAYOR XLSB files. The workbook is for accounting reconciliation and downstream RORCH integration; it is not PH2 or Funding Memo population.

## Windows VS Code
Open VS Code directly at:

```text
C:\01. GitHub\Kumquat.TECH\KT.MovemAcc
```

Use a Windows PowerShell terminal from the project root:

```powershell
py -3.12 -m venv 90_RUNTIME\venv_win
.\90_RUNTIME\venv_win\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python -m kt_movemacc ph1 --period 2026.08
kt_movemacc ph1 --period 2026.08
```

If `py -3.12` is unavailable, use an installed Python 3.11+ interpreter. Windows execution and Excel Desktop recalculation must be recorded as acceptance evidence before claiming Windows/HUMAN completion.

## WSL
The WSL path proven during PH1 recovery is:

```bash
cd "/mnt/c/01. GitHub/Kumquat.TECH/KT.MovemAcc"
90_RUNTIME/venv_clean/bin/python -m kt_movemacc ph1 --period 2026.08
90_RUNTIME/venv_clean/bin/kt_movemacc ph1 --period 2026.08
```

## RAW Files
Place source files under the project-relative folder `RAW.INPUT/<period>/`. The standard resolver uses exact filenames derived from the period and `V 1`; it does not auto-select alternate versions such as `V 2`. For August 2026 the expected files are:

```text
RAW.INPUT/2026.08/Mayor Inmob. Eplaza 2026 08 V 1.xlsb
RAW.INPUT/2026.08/Mayor Grupo Impulsa 2026 08 V 1.xlsb
```

The period is selected with `--period 2026.08`. Optional overrides are available:

```powershell
python -m kt_movemacc ph1 --period 2026.08 --raw-eplaza <path> --raw-impulsa <path> --out-dir <path>
```

## Output Sheets
The PH1 workbook contains exactly:

- `CAM2026.08_CONSOL.ALIGN`: consolidated account alignment using stable account codes.
- `CM2026.08_EPLAZA`: EPLAZA ledger in the A:J CUENTAS DE MAYOR layout.
- `CM2026.08_IMPULSA`: IMPULSA ledger in the A:J CUENTAS DE MAYOR layout.
- `AUDIT.PH1`: conflicts, source-only accounts, formula reconciliation, and hierarchy exceptions.
- `CONTROL`: source hashes, account counts, formula/package status, and acceptance-gate notes.

In CM sheets, column G is `VALORES UF` and column J is `VALORES $$`. Column K is `VISIBILIDAD_UF`: `MOSTRAR` means the row/group has nonzero UF value or an auditable ambiguous hierarchy; `OCULTAR` means UF is zero/blank for presentation filtering only. Records are preserved.

## Approved PH1 subtotal criteria

HUMAN–MORCH approved CR-001 through CR-015 are recorded in `04_CONFIG/CRITERIA/PH1_CRITERIA_REGISTER.json` and summarized in `03_DOCS/HUMAN/PH1_APPROVED_CRITERIA.md`. These criteria govern PH1 subtotal review only and do not approve PH2/Funding Memo rules.

## Expected Messages
A successful accepted-baseline run prints parsed account counts, five sheet names, formula count, broken-reference count, output path, SHA-256, and `PH1 STATUS: PASS`. The August 2026 HUMAN-accepted baseline includes 15 verified criteria, 14 resolved historical exceptions, 54 CAM headings with formulas, Excel COM recalculation evidence, and 16 passing regression tests. Future periods still require their own reconciliation.

## Troubleshooting
- `RAW inputs not found`: verify the period folder and standard file names, or pass explicit RAW paths.
- `ModuleNotFoundError`: activate the venv and run `python -m pip install -e .`.
- Excel repair warning: rerun tests and inspect `OUTPUT/2026.08/KTMA_PH1_REPORT.json`; XML package integrity should show zero broken references.
- Unexpected totals: inspect `AUDIT.PH1` before editing formulas manually.
