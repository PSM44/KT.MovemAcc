# Candidate Workbook Structural Analysis Report

**Target Workbook:** `09_REVIEW/KTMA_WORKBOOK_001/CANDIDATE_KTMA_FINANCIAL_WORKBOOK_2026.08.xlsx`  
**Generated Model:** `09_REVIEW/KTMA_WORKBOOK_001/candidate_structural_model.json`  
**Author:** Analyst (reverse_engineer) - AgentTeams `ktma-workbook-engineering-012`  
**Date:** 2026-10-31  

---

## 1. Executive Summary

This report provides the complete cell-level structural model, worksheet architecture, and inventory of the candidate financial workbook (`CANDIDATE_KTMA_FINANCIAL_WORKBOOK_2026.08.xlsx`). 

The candidate workbook represents an expanded 7-sheet integrated financial model for accounting period **2026.08**, incorporating detailed source ledgers, consolidated PH1 balances, Funding Memo (FM) mapping allocations, functional audits, queryable tables, and FM targets summary.

---

## 2. Worksheet Structure & Dimensions

| Worksheet Name | Max Row | Max Col | Total Non-Empty Cells | Description |
| :--- | :---: | :---: | :---: | :--- |
| **01_Sources_Eplaza** | 288 | 15 | 3,867 | Eplaza source ledger with extended attribution columns |
| **02_Sources_Impulsa** | 143 | 15 | 1,903 | Impulsa source ledger with extended attribution columns |
| **03_Consolidated_PH1** | 1,772 | 14 | 20,349 | Consolidated PH1 financial statement |
| **04_FM_Mapping** | 133 | 23 | 2,927 | Funding Memo v1.0.1 account allocation mapping |
| **05_Audit** | 13 | 6 | 74 | Functional audit and control verification items |
| **06_Query_Table** | 1,373 | 12 | 15,104 | Queryable Excel table for analytical reporting |
| **07_FM_Targets_Summary** | 17 | 14 | 238 | High-level Funding Memo targets summary |

---

## 3. Structural Comparison with PH1 Reference

- **Sheet Count**: Candidate contains 7 sheets vs. 3 sheets in PH1 reference.
- **Extended Worksheets**: Candidate adds `04_FM_Mapping`, `05_Audit`, `06_Query_Table`, and `07_FM_Targets_Summary` to support funding memo compliance and interactive querying.
- **Column Width & Attributes**: Source sheets and consolidation tables feature extended column dimensions (up to 15 columns for sources, 23 columns for mapping) capturing granular metadata, coefficients, and assignment statuses.

---

## 4. Structural Model Persistence

The complete cell inventory (44,462 non-empty cells across all 7 worksheets) has been serialized to:
`09_REVIEW/KTMA_WORKBOOK_001/candidate_structural_model.json`
