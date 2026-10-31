# PH1 Reference Workbook Structural Analysis Report

**Target Workbook:** `09_REVIEW/KTMA_WORKBOOK_001/PH1_REFERENCE_KTMA_FINANCIAL_WORKBOOK_2026.08.xlsx`  
**Generated Model:** `09_REVIEW/KTMA_WORKBOOK_001/ph1_structural_model.json`  
**Author:** Analyst (reverse_engineer) - AgentTeams `ktma-workbook-engineering-012`  
**Date:** 2026-10-31  

---

## 1. Executive Summary

This report establishes the complete cell-level structural model, architectural hierarchy, accounting provenance, and cross-sheet relationships of the PH1 reference financial workbook (`PH1_REFERENCE_KTMA_FINANCIAL_WORKBOOK_2026.08.xlsx`). 

The PH1 reference workbook serves as the foundational validation baseline for the KT.MovemAcc autonomous excel product engineering pipeline. It consolidates accounting observations from two primary operating entities (**Eplaza** and **Impulsa**) for the accounting period **2026.08**, providing exact UF (Unidad de Fomento) and CLP values, account hierarchies, semantic keys, and JSON-encoded accounting provenance evidence.

---

## 2. Workbook Worksheet Structure & Dimensions

The workbook contains three active worksheets:

| Worksheet Name | Max Row | Max Col | Total Non-Empty Cells | Description |
| :--- | :---: | :---: | :---: | :--- |
| **01_Eplaza_Source** | 288 | 12 | 3,076 | Detailed account-level ledger for Inmobiliaria Eplaza (2026.08) |
| **02_Impulsa_Source** | 143 | 12 | 1,516 | Detailed account-level ledger for Grupo Impulsa (2026.08) |
| **03_Consolidated_PH1** | 2,150 | 12 | 21,551 | Consolidated PH1 financial statement combining Eplaza & Impulsa |

---

## 3. Column Schema & Accounting Provenance

### Sheets `01_Eplaza_Source` & `02_Impulsa_Source`
Columns (A–L):
- **A**: `Account Code` (e.g., `110111`, `110121`, etc.)
- **B**: `Heading` (e.g., `EFECTIVO O EFECTIVO EQUIVALENTE`, `VALORES NEGOCIABLES`)
- **C**: `Description` (e.g., `Caja`, `Banco BCI N° 10682066`)
- **D**: `Debit UF` (Numeric, float)
- **E**: `Credit UF` (Numeric, float)
- **F**: `Value UF` (Numeric, float)
- **G**: `Debit CLP` (Numeric, integer/float)
- **H**: `Credit CLP` (Numeric, integer/float)
- **I**: `Value CLP` (Numeric, integer/float)
- **J**: `Row Type` (`TITLE`, `HEADING`, `ACCOUNT`, etc.)
- **K**: `Filtro` (`SI`, `NO`)
- **L**: `Source Row` (Integer row pointer)

### Sheet `03_Consolidated_PH1`
Columns (A–L):
- **A**: `Account Code`
- **B**: `Semantic Key`
- **C**: `Heading`
- **D**: `Eplaza Description`
- **E**: `Impulsa Description`
- **F**: `Eplaza Value UF`
- **G**: `Impulsa Value UF`
- **H**: `Total Value UF`
- **I**: `Eplaza Value CLP`
- **J**: `Impulsa Value CLP`
- **K**: `Total Value CLP`
- **L**: `Evidence` (JSON payload containing source row linkages, e.g., `{"eplaza_source_row": 4, "impulsa_source_row": 4, "key": "110111"}`)

---

## 4. Cross-Sheet Relationships & Provenance Traceability

The consolidation sheet (`03_Consolidated_PH1`) maintains strict audit traceability back to the source ledgers via JSON metadata stored in column L. Every consolidated row explicitly references its origin row in Eplaza and/or Impulsa.

### Sample Provenance Mapping
- **Row 2 (`EFECTIVO O EFECTIVO EQUIVALENTE#1`)**:
  - Eplaza Value UF: `170.86` (Source Row 3)
  - Impulsa Value UF: `65.69` (Source Row 3)
  - Total Value UF: `236.55`
  - Eplaza Value CLP: `6,515,882`
  - Impulsa Value CLP: `2,620,670`
  - Total Value CLP: `9,136,552`
  - Evidence: `{"eplaza_source_row": 3, "impulsa_source_row": 3, "key": "EFECTIVO O EFECTIVO EQUIVALENTE#1"}`

- **Row 3 (`110111` - Caja)**:
  - Eplaza Value UF: `25.17` (Source Row 4)
  - Impulsa Value UF: `0` (Source Row 4)
  - Total Value UF: `25.17`
  - Eplaza Value CLP: `1,000,000`
  - Impulsa Value CLP: `0`
  - Total Value CLP: `1,000,000`
  - Evidence: `{"eplaza_source_row": 4, "impulsa_source_row": 4, "key": "110111"}`

---

## 5. Structural Model Persistence

The complete cell-level dictionary (all 26,143 non-empty cells across all three worksheets) has been fully serialized into:
`09_REVIEW/KTMA_WORKBOOK_001/ph1_structural_model.json`

This JSON model includes:
- Sheet metadata (`max_row`, `max_col`, `merged_ranges`)
- Cell coordinates (`A1`, `B2`, etc.)
- Data types (`s` for string, `n` for number, etc.)
- Raw cell values and number formatting strings
- Formula indicators and extracted formula expressions

---

## 6. Non-Degradation Contract Implications

1. **Structural Parity**: Any generated candidate workbook must match or exceed the structural hierarchy, column naming convention, and sheet organization of PH1.
2. **Precision Integrity**: Floating-point UF values and integer CLP values must reconcile exactly against source ledgers without rounding drift.
3. **Provenance Completeness**: Column L JSON audit metadata must be present for every consolidated row to ensure end-to-end transparency.
