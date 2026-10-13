from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest

from kt_movemacc import ph15_database as db

ROOT = Path.cwd()
PERIOD = "2026.08"
RAW_EPLAZA = ROOT / "RAW.INPUT/2026.08/Mayor Inmob. Eplaza 2026 08 V 1.xlsb"
RAW_IMPULSA = ROOT / "RAW.INPUT/2026.08/Mayor Grupo Impulsa 2026 08 V 1.xlsb"


def test_schema_initialization_and_foreign_keys(tmp_path):
    db_path = tmp_path / "KTMA.sqlite"
    db.initialize_database(db_path)
    with db.connect(db_path, read_only=True) as conn:
        assert conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == db.SCHEMA_VERSION
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
    assert {"source_files", "original_source_rows", "account_observations", "calculation_lineage"} <= tables


def test_august_ingestion_idempotency_persistence_and_reconciliation(tmp_path):
    db_path = tmp_path / "KTMA.sqlite"
    first = db.import_period(db_path, root=ROOT, period=PERIOD)
    second = db.import_period(db_path, root=ROOT, period=PERIOD)
    summary = db.database_summary(db_path)

    assert first.reconciliation_status == "PASS"
    assert first.source_rows == 429
    assert first.rule_checks == 15
    assert first.consolidated_rows == 307
    assert second.idempotent is True
    assert second.source_rows == 0
    assert summary["source_files"] == 2
    assert summary["observations"] == 429
    assert summary["consolidated_balances"] == 614
    assert summary["reconciliation_checks"] == 140

    lineage = db.lineage_for_hernando(db_path, PERIOD)
    assert lineage["eplaza_uf"] == "550120.960000"
    assert lineage["impulsa_uf"] == "0.000000"
    assert lineage["consolidated_uf"] == "550120.960000"
    assert lineage["rule"]["rule_id"] == "CR-004"


def test_decimal_precision_is_canonical_text():
    assert db.decimal_text(550120.96) == "550120.960000"
    assert Decimal(db.decimal_text(0.1 + 0.2)) == Decimal("0.300000")


def test_transaction_rollback_on_failure(tmp_path, monkeypatch):
    db_path = tmp_path / "KTMA.sqlite"

    def fail_consolidated(*args, **kwargs):
        raise RuntimeError("controlled rollback probe")

    monkeypatch.setattr(db, "_insert_consolidated", fail_consolidated)
    with pytest.raises(RuntimeError, match="controlled rollback probe"):
        db.import_period(db_path, root=ROOT, period=PERIOD)

    with db.connect(db_path, read_only=True) as conn:
        assert conn.execute("SELECT COUNT(*) FROM source_files").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM original_source_rows").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM processing_runs").fetchone()[0] == 0


def test_source_hash_change_is_rejected_after_prior_import(tmp_path):
    db_path = tmp_path / "KTMA.sqlite"
    db.import_period(db_path, root=ROOT, period=PERIOD)
    with db.connect(db_path) as conn:
        period_id = conn.execute("SELECT period_id FROM accounting_periods WHERE period_code = ?", (PERIOD,)).fetchone()[0]
        entity_id = conn.execute("SELECT entity_id FROM entities WHERE entity_code = 'EPLAZA'").fetchone()[0]
        with pytest.raises(ValueError, match="Source hash changed"):
            db._source_file(
                conn,
                period_id=period_id,
                entity_id=entity_id,
                path=RAW_IMPULSA,
                allow_hash_change=False,
            )
        with pytest.raises(ValueError, match="Source hash changed"):
            db._source_file(
                conn,
                period_id=period_id,
                entity_id=entity_id,
                path=RAW_IMPULSA,
                allow_hash_change=True,
            )


def test_missing_and_ambiguous_inputs_are_explicit(tmp_path):
    db_path = tmp_path / "KTMA.sqlite"
    with pytest.raises(FileNotFoundError):
        db.import_period(db_path, root=ROOT, period="2099.01")
    with pytest.raises(ValueError, match="same file"):
        db.import_period(db_path, root=ROOT, period=PERIOD, raw_eplaza=RAW_EPLAZA, raw_impulsa=RAW_EPLAZA)


def test_repeated_titles_and_hierarchy_edges_are_queryable(tmp_path):
    db_path = tmp_path / "KTMA.sqlite"
    db.import_period(db_path, root=ROOT, period=PERIOD)
    with db.connect(db_path, read_only=True) as conn:
        repeated = conn.execute(
            """
            SELECT label, COUNT(*) AS n
            FROM account_observations
            WHERE row_type = 'HEADING'
            GROUP BY label
            HAVING COUNT(*) > 1
            """
        ).fetchall()
        edges = conn.execute("SELECT COUNT(*) FROM hierarchy_context").fetchone()[0]
    assert any(row["label"] == "VALORES NEGOCIABLES" for row in repeated)
    assert edges > 0


def test_multiple_periods_with_explicit_inputs(tmp_path):
    db_path = tmp_path / "KTMA.sqlite"
    db.import_period(db_path, root=ROOT, period="2026.08", raw_eplaza=RAW_EPLAZA, raw_impulsa=RAW_IMPULSA)
    db.import_period(db_path, root=ROOT, period="2026.09", raw_eplaza=RAW_EPLAZA, raw_impulsa=RAW_IMPULSA)
    with db.connect(db_path, read_only=True) as conn:
        assert conn.execute("SELECT COUNT(*) FROM accounting_periods").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM source_files").fetchone()[0] == 4


def test_foreign_key_integrity_and_read_only_reopen(tmp_path):
    db_path = tmp_path / "KTMA.sqlite"
    db.import_period(db_path, root=ROOT, period=PERIOD)
    with db.connect(db_path) as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO account_observations(
                    original_row_id, period_id, entity_id, row_type, label, debit_uf, credit_uf,
                    value_uf, debit_clp, credit_clp, value_clp, is_zero, source_order, idempotency_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (999999, 1, 1, "ACCOUNT", "bad", "0", "0", "0", "0", "0", "0", 1, 1, "bad"),
            )
    with db.connect(db_path, read_only=True) as conn:
        assert conn.execute("SELECT COUNT(*) FROM account_observations").fetchone()[0] == 429


def test_independent_financial_matrices_and_read_contract(tmp_path):
    db_path = tmp_path / "KTMA.sqlite"
    db.import_period(db_path, root=ROOT, period=PERIOD)

    rules = db.independent_rule_matrix(db_path, PERIOD)
    headings = db.independent_cam_heading_matrix(db_path, PERIOD)

    assert len(rules) == 15
    assert all(row["status"] == "INDEPENDENTLY_VERIFIED" for row in rules)
    assert len(headings) == 54
    assert all(row["status"] == "INDEPENDENTLY_VERIFIED" for row in headings)

    assert db.read_contract_query(db_path, "periods") == [{"period_code": PERIOD, "year": 2026, "month": 8}]
    assert len(db.read_contract_query(db_path, "entities")) == 2
    assert db.read_contract_query(db_path, "discrepancies", period=PERIOD) == []
    account = db.read_contract_query(db_path, "account", period=PERIOD, account_code="121011")
    assert account[0]["value_uf"] == "2846.550000"
    consolidated = db.read_contract_query(
        db_path,
        "consolidated",
        period=PERIOD,
        semantic_key="PROYECTO HERNANDO DE AGUIRRE#1",
    )
    assert consolidated[0]["total_value_uf"] == "550120.960000"


def test_integrity_check_backup_restore_and_lock_behavior(tmp_path):
    db_path = tmp_path / "KTMA.sqlite"
    backup_path = tmp_path / "backup.sqlite"
    db.import_period(db_path, root=ROOT, period=PERIOD)

    integrity = db.integrity_report(db_path)
    assert integrity["integrity_check"] == "ok"
    assert integrity["quick_check"] == "ok"
    assert integrity["foreign_key_check"] == []

    db.backup_database(db_path, backup_path)
    assert db.database_summary(backup_path)["observations"] == 429

    locker = sqlite3.connect(db_path)
    try:
        locker.execute("BEGIN EXCLUSIVE")
        locked = sqlite3.connect(db_path, timeout=0)
        try:
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                locked.execute("INSERT INTO entities(entity_code, display_name) VALUES ('LOCK', 'Lock')")
        finally:
            locked.close()
    finally:
        locker.rollback()
        locker.close()


def test_source_xlsb_hashes_are_not_modified(tmp_path):
    before = {RAW_EPLAZA: db.sha256(RAW_EPLAZA), RAW_IMPULSA: db.sha256(RAW_IMPULSA)}
    db.import_period(tmp_path / "KTMA.sqlite", root=ROOT, period=PERIOD)
    after = {RAW_EPLAZA: db.sha256(RAW_EPLAZA), RAW_IMPULSA: db.sha256(RAW_IMPULSA)}
    assert after == before
