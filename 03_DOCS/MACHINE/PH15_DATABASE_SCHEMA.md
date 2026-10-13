# PH1.5 Database Schema

Schema version: `1`

Engine: Python standard-library `sqlite3`

Default database: `DATA/KTMA.sqlite`

## Tables

| Table | Purpose |
| --- | --- |
| `schema_migrations` | Applied schema versions. |
| `entities` | Accounting entities, currently `EPLAZA` and `IMPULSA`. |
| `accounting_periods` | Period codes such as `2026.08`. |
| `source_files` | RAW XLSB file identity, path, hash, size, and import timestamp. |
| `processing_runs` | One row per PH1.5 import execution. |
| `original_source_rows` | Physical source rows from the CUENTAS DE MAYOR sheet. |
| `account_observations` | Normalized source observations with codes, labels, semantic keys, and values. |
| `hierarchy_context` | Inferred subtotal membership edges and evidence. |
| `rule_versions` | Approved rule-set provenance. |
| `calculation_lineage` | Rule-by-rule calculation output and evidence. |
| `consolidated_balances` | Run-scoped EPLAZA, IMPULSA, and consolidated UF/CLP balances. |
| `reconciliation_checks` | PASS/PARTIAL evidence for rule and traceability checks. |

## Keys And Constraints

- `source_files` is unique by `(period_id, entity_id)`.
- `original_source_rows` is unique by `(source_file_id, source_sheet, source_row_number)`.
- `account_observations.original_row_id` is unique and references the original row.
- `account_observations.idempotency_key` is unique.
- `hierarchy_context` is unique by parent, child, and relationship type.
- `rule_versions` is unique by `(rule_set_name, version_code)`.
- `consolidated_balances` has a run-scoped unique business key over row type and account/semantic key.
- Foreign keys are enabled on every connection with `PRAGMA foreign_keys = ON`.

## Indexes

- `idx_observations_period_entity_code`
- `idx_observations_semantic`
- `idx_consolidated_period_code`
- `idx_consolidated_run_business_key`
- `idx_lineage_rule`
- `idx_reconciliation_run_status`

## Hierarchy Representation

Headings use PH1 semantic keys such as:

```text
PROYECTO HERNANDO DE AGUIRRE#1
VALORES NEGOCIABLES#2
```

Account rows use stable account codes where present. `hierarchy_context` stores parent and child observation IDs plus the inference status from the accepted PH1 hierarchy logic.

## Decimal Representation

Financial values are stored as text with six decimal places. This preserves fixed decimal semantics while staying inside standard SQLite.

Example:

```text
550120.960000
0.000000
```

## CLI

Initialize and import August 2026:

```powershell
python -m kt_movemacc ph15-db --period 2026.08
kt_movemacc ph15-db --period 2026.08
```

Print the Hernando de Aguirre lineage:

```powershell
python -m kt_movemacc ph15-db --period 2026.08 --print-lineage
```

Read-only query contract examples:

```powershell
python -m kt_movemacc ph15-query periods
python -m kt_movemacc ph15-query entities
python -m kt_movemacc ph15-query account --period 2026.08 --account-code 121011
python -m kt_movemacc ph15-query consolidated --period 2026.08 --semantic-key "PROYECTO HERNANDO DE AGUIRRE#1"
python -m kt_movemacc ph15-query discrepancies --period 2026.08
```

The read-only CLI uses parameterized helper functions and does not expose arbitrary SQL.

## Source Versioning

Current policy: `REJECT`.

If a source file for an already imported period/entity has a different SHA-256, PH1.5 raises an error and rolls back the transaction. It does not silently replace, overwrite, or create an alternate accepted version. A future `NEW_VERSION` policy requires explicit HUMAN-MORCH approval and a schema migration.

## Query Examples

Hernando consolidated UF:

```sql
SELECT heading_text, eplaza_value_uf, impulsa_value_uf, total_value_uf
FROM consolidated_balances
WHERE semantic_key = 'PROYECTO HERNANDO DE AGUIRRE#1'
ORDER BY consolidated_id DESC
LIMIT 1;
```

Failed or review-required reconciliation checks:

```sql
SELECT check_name, status, expected_value, observed_value, difference_value
FROM reconciliation_checks
WHERE status <> 'PASS';
```

Source row trace:

```sql
SELECT e.entity_code, sf.file_name, osr.source_sheet, osr.source_row_number,
       ao.label, ao.value_uf
FROM account_observations ao
JOIN entities e ON e.entity_id = ao.entity_id
JOIN original_source_rows osr ON osr.original_row_id = ao.original_row_id
JOIN source_files sf ON sf.source_file_id = osr.source_file_id
WHERE ao.semantic_key = 'PROYECTO HERNANDO DE AGUIRRE#1';
```
