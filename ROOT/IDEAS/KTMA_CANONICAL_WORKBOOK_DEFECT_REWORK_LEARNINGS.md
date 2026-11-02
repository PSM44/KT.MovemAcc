# KTMA Canonical Workbook Defect Rework Learnings

## Defects Fixed in Commit 558b598

### 1. FM Coefficient Application (07_FM_Targets_Summary)
- **Problem**: Target totals accumulated raw values without applying `rule.coefficient`
- **Fix**: Multiply each account's Eplaza and Impulsa values by `rule.coefficient` before accumulation
- **Code location**: `target_totals` accumulation loop in `generate_canonical_financial_workbook()`

### 2. FM Entity Column Segregation (04_FM_Mapping)
- **Problem**: Impulsa rows incorrectly placed Impulsa values in Eplaza Value UF/CLP columns
- **Fix**: Columns L/M and O/P now always show Eplaza/Impulsa values respectively, regardless of entity row
- **Code location**: Entity loop in FM Mapping sheet generation

### 3. Query Table Artificial Rows (06_Query_Table)
- **Problem**: Zero-value rows created for entities with no actual balance
- **Fix**: Only generate rows when entity has non-zero value; deduplicate by account_code
- **Code location**: Query Table generation with `unique_consol_rows` deduplication

### 4. FM Invariant Verification
- **Problem**: Invariant check didn't apply coefficients
- **Fix**: Verification now uses coefficient-adjusted values matching target accumulation
- **Code location**: `fm_invariant_pass` check block

## Key Technical Insights
- Consolidated balances have 7 duplicate rows per account (period variants) - must deduplicate
- Coefficients are always +1 in current mapping but framework supports negative
- Entity separation must be enforced at column level, not row level
