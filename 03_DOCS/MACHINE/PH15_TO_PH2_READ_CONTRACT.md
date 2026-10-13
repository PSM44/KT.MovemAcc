# PH1.5 To PH2 Read-Only Data Contract

Status: verified for PH1.5 schema version `1`

PH2 implementation is not authorized here. This contract defines the read-only data surface PH2 may consume later.

## Boundary

Allowed:

- read periods, entities, source file identities, processing runs, observations, consolidated values, rule versions, lineage, and discrepancies
- use deterministic period/entity/account filters
- preserve decimal strings exactly

Not allowed:

- arbitrary user SQL through ordinary CLI
- writes, updates, deletes, schema changes, or source-history replacement
- Funding Memo mapping, FM0 comparisons, or PH2 business rules

## Commands

```powershell
python -m kt_movemacc ph15-query periods
python -m kt_movemacc ph15-query entities
python -m kt_movemacc ph15-query source-files --period 2026.08
python -m kt_movemacc ph15-query runs --period 2026.08
python -m kt_movemacc ph15-query account --period 2026.08 --account-code 121011
python -m kt_movemacc ph15-query consolidated --period 2026.08 --semantic-key "PROYECTO HERNANDO DE AGUIRRE#1"
python -m kt_movemacc ph15-query rule-versions
python -m kt_movemacc ph15-query discrepancies --period 2026.08
python -m kt_movemacc ph15-query hernando --period 2026.08
```

## Python Interface

Module: `kt_movemacc.ph15_database`

- `available_periods(db_path)`
- `available_entities(db_path)`
- `source_versions(db_path, period)`
- `processing_runs(db_path, period)`
- `observations_by_code(db_path, period, account_code)`
- `consolidated_values(db_path, period, account_code=None, semantic_key=None)`
- `rule_versions(db_path)`
- `unresolved_discrepancies(db_path, period)`
- `lineage_for_hernando(db_path, period)`
- `read_contract_query(db_path, query, period="2026.08", account_code=None, semantic_key=None)`

All query helpers open SQLite in read-only mode when they read existing data.

## Parameterization

- `period`: required for period-scoped queries; format `AAAA.MM`
- `entity_code`: returned as `EPLAZA` or `IMPULSA`
- `account_code`: stable accounting code, not title text
- `semantic_key`: hierarchy-aware heading key, for example `PROYECTO HERNANDO DE AGUIRRE#1`

Repeated headings must be addressed by semantic key, not label alone.

## Return Contract

Financial values are serialized as strings with six decimal places:

```json
{
  "value_uf": "2846.550000",
  "value_clp": "113583842.000000"
}
```

Use `null` for absent source rows or descriptions. Use `"0.000000"` for real zero financial values. Do not treat missing and zero as equivalent.

Ordering is deterministic:

- periods by `period_code`
- entities by `entity_code`
- source files by `entity_code`
- observations by `entity_code`, then source order
- consolidated rows by stored consolidated order for the selected successful run

## Version Selection

Read helpers select the latest successful processing run for run-scoped consolidated values. Source rows and observations are period/entity scoped and are idempotent across repeated imports of the same source hashes.

Source version policy is `REJECT`: changed source hashes for an existing period/entity fail the import and roll back. `NEW_VERSION` and `REPLACE` are future design decisions requiring HUMAN-MORCH approval.

## Independent Validation

TASK043 verified:

- 15 approved PH1 criteria independently from persisted source observations
- 54 CAM headings independently from persisted source observations
- `PROYECTO HERNANDO DE AGUIRRE#1` = `550120.960000` UF
- database `PRAGMA integrity_check` = `ok`
- no unresolved discrepancies for the latest August 2026 run

## Backup And Recovery

Use SQLite backup, not file copy during active writes. The module exposes:

```python
backup_database(db_path, backup_path)
```

Restored backups must pass:

```sql
PRAGMA integrity_check;
PRAGMA foreign_key_check;
```

## Known Limitations

- Excel Desktop recalculation is outside PH1.5 database import.
- PH2-specific mapping and Funding Memo comparisons are intentionally absent.
- The database contains private financial data and must remain outside public publication packages.
