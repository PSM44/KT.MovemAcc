# PH1 Data Flow

```text
RAW.INPUT/<period>/*.xlsb
  -> pyxlsb CUENTAS DE MAYOR reader
  -> AccountRow records with source row/sheet lineage
  -> source-backed subtotal membership inference
  -> code-based EPLAZA/IMPULSA alignment
  -> openpyxl five-sheet workbook
  -> OUTPUT/<period>/CAM<period>_CONSOL.ALIGN.xlsx
  -> OUTPUT/<period>/KTMA_PH1_REPORT.json
```

## Stages

1. Parse the two XLSB files without modifying RAW inputs.
2. Preserve CM ledger financial rows in physical columns A:J and add K `VISIBILIDAD_UF` for UF presentation filtering.
3. Infer heading/account membership from source values, never fixed row positions.
4. Align consolidated account rows by account code and generate CAM hierarchical title formulas for direct child groups/accounts.
5. Preserve conflicting descriptions and one-company-only accounts in CAM and `AUDIT.PH1`.
6. Write source hashes and acceptance-gate status to `CONTROL`.
7. Validate XLSX ZIP/package integrity and formula XML for broken references.

## Boundaries
PH1 intentionally excludes PH2 criteria, Funding Memo population, macros, external links, and fabricated Excel Desktop acceptance. Human visual/usability acceptance remains a separate gate.
