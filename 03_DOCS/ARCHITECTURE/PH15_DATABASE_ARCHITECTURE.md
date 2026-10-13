# PH1.5 Database Architecture

## Purpose

PH1.5 introduces a local SQLite database between RAW XLSB ingestion and later reporting. The accepted PH1 workbook generator remains the default reporting path; the database is invoked explicitly with `ph15-db`.

The database stores financial source rows, normalized observations, hierarchy context, approved PH1 rule lineage, consolidated balances, and reconciliation checks. It is intended for inspection, traceability, and future reporting integration, not as a replacement for the HUMAN-accepted PH1 workbook.

## Storage

Default path:

```text
DATA/KTMA.sqlite
```

SQLite sidecar files are ignored by Git:

```text
DATA/*.sqlite
DATA/*.sqlite-*
DATA/*.db
DATA/*.db-*
```

RAW XLSB files are read only. PH1 workbook output is not modified by `ph15-db`.

## Flow

```text
RAW.INPUT/<AAAA.MM>/*.xlsb
  -> kt_movemacc.engine.parse_xlsb
  -> PH1.5 SQLite import transaction
  -> source_files / original_source_rows / account_observations
  -> hierarchy_context / consolidated_balances / calculation_lineage
  -> reconciliation_checks and queryable lineage
```

PH1.5 reuses the accepted PH1 parser and semantic criteria definitions from `src/kt_movemacc/engine.py`. This avoids a second accounting parser.

## Transaction Boundary

One `ph15-db --period <period>` execution is one SQLite transaction:

- apply schema migrations
- register accounting period and processing run
- hash and register source files
- insert original rows and normalized observations
- insert hierarchy edges
- calculate consolidated balances
- store rule lineage and reconciliation checks
- mark the processing run `PASS` or `PARTIAL`

Any exception rolls the transaction back.

## Idempotency And Source Version Policy

Source files are unique by `(period_id, entity_id)`. Original rows are unique by `(source_file_id, source_sheet, source_row_number)`. Observations use an idempotency key of entity, source file, sheet, and row number.

Repeated imports of the same source hashes add a new processing run and run-scoped reconciliation evidence, but do not duplicate source rows or observations.

The safe source version policy is `REJECT`: if a file for an existing period/entity resolves to a different SHA-256, PH1.5 raises an error and does not replace accepted financial history. `NEW_VERSION` and `REPLACE` are not implemented and require HUMAN-MORCH approval.

## Decimal Policy

SQLite stores financial numbers as canonical text because SQLite has no fixed decimal type. PH1.5 converts values through `Decimal(str(value))` and stores six decimal places. Arithmetic used for persisted totals is Decimal based.

## Provenance

The database preserves:

- source file name, path, byte size, and SHA-256
- source sheet and original row number
- original source row type and labels
- account code or hierarchy semantic key
- source values separately from derived consolidated values
- calculation rule, formula text, source UF, calculated UF, and difference

## Current Limitations

- PH1.5 currently validates the approved PH1 criteria and CAM heading totals available through the accepted PH1 engine.
- Excel Desktop formula recalculation is not part of `ph15-db`; PH1.5 stores Python/SQL lineage and reconciliation evidence.
- PH2 reporting is not implemented.
- The local SQLite database may contain financial data and must not be included in public publication packages.
- The ordinary read surface is `ph15-query`; unrestricted SQL is reserved for specialist/audit use.
