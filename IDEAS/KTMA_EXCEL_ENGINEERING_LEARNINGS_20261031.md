# KTMA Excel Product Engineering Learnings (2026-10-31)

## 1. Cell-Level Reverse Engineering & Comparison
- Reverse-engineering PH1 reference and candidate workbooks via openpyxl allowed precise extraction of structural metadata (sheets, dimensions, formulas, styles, structured tables).
- Cell comparison matrix revealed that baseline workbooks must query aligned consolidated balances (`consolidated_balances`) and raw sources (`original_source_rows`) rather than intermediate unpopulated views (`account_observations`).

## 2. Non-Degradation Contract & Executable Validation
- Enforcing an executable pytest non-degradation suite (`test_non_degradation.py`) guarantees that required sheets, schema columns, accounting invariants ($D = E + F$), and traceability linkages never regress across iterations.

## 3. Native Excel COM Automation & Spreadsheet Inquire
- Level B validation via `win32com.client` confirmed that generated workbooks open successfully in native Excel, execute full workbook recalculation (`CalculateFull`) with zero errors, and interface correctly with Spreadsheet Inquire add-ins.

## 4. Path Guardian & Closure Bot Governance
- Strict path governance prevents Windows POSIX absolute path violations (e.g. `C:` directories inside workspace root) and ensures robust SHA-256 round-trip delivery verification.
- Closure Bot successfully separates `TECHNICAL_PASS`, `PRODUCT_PASS`, and `HUMAN_ACCEPTANCE` (pending formal review).
