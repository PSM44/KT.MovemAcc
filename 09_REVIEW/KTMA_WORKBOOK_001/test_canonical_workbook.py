"""Tests for Canonical Financial Workbook Generator."""

from __future__ import annotations

import sqlite3
from pathlib import Path
import pytest

from kt_movemacc.canonical_workbook import generate_canonical_financial_workbook


@pytest.fixture
def canonical_test_db(tmp_path):
    db_path = tmp_path / "KTMA.sqlite"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE entities (
            entity_id INTEGER PRIMARY KEY,
            entity_code TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL
        );
        CREATE TABLE accounting_periods (
            period_id INTEGER PRIMARY KEY,
            period_code TEXT NOT NULL UNIQUE,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL
        );
        CREATE TABLE source_files (
            source_file_id INTEGER PRIMARY KEY,
            period_id INTEGER NOT NULL REFERENCES accounting_periods(period_id),
            entity_id INTEGER NOT NULL REFERENCES entities(entity_id),
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            byte_size INTEGER NOT NULL,
            imported_at TEXT NOT NULL
        );
        CREATE TABLE original_source_rows (
            original_row_id INTEGER PRIMARY KEY,
            source_file_id INTEGER NOT NULL REFERENCES source_files(source_file_id),
            source_sheet TEXT NOT NULL,
            source_row_number INTEGER NOT NULL,
            row_type TEXT NOT NULL,
            filtro TEXT,
            account_code TEXT,
            heading_text TEXT,
            account_description TEXT,
            debitos_uf TEXT NOT NULL,
            creditos_uf TEXT NOT NULL,
            valores_uf TEXT NOT NULL,
            debitos_clp TEXT NOT NULL,
            creditos_clp TEXT NOT NULL,
            valores_clp TEXT NOT NULL,
            raw_payload_json TEXT
        );
        CREATE TABLE consolidated_balances (
            consolidated_id INTEGER PRIMARY KEY,
            period_id INTEGER NOT NULL REFERENCES accounting_periods(period_id),
            run_id INTEGER NOT NULL,
            row_type TEXT NOT NULL,
            account_code TEXT,
            semantic_key TEXT,
            heading_text TEXT,
            eplaza_description TEXT,
            impulsa_description TEXT,
            eplaza_value_uf TEXT,
            impulsa_value_uf TEXT,
            total_value_uf TEXT,
            eplaza_value_clp TEXT,
            impulsa_value_clp TEXT,
            total_value_clp TEXT,
            evidence_json TEXT
        );
    """)
    conn.execute("INSERT INTO entities VALUES (1, 'EPLAZA', 'Eplaza')")
    conn.execute("INSERT INTO entities VALUES (2, 'IMPULSA', 'Impulsa')")
    conn.execute("INSERT INTO accounting_periods VALUES (1, '2026.08', 2026, 8)")
    conn.execute("INSERT INTO source_files VALUES (1, 1, 1, 'test.xlsb', 'Mayor Eplaza.xlsb', 'sha256_1', 1000, '2026-10-30')")
    conn.execute("INSERT INTO source_files VALUES (2, 1, 2, 'test.xlsb', 'Mayor Impulsa.xlsb', 'sha256_2', 1000, '2026-10-30')")
    
    # Eplaza source rows
    conn.execute("INSERT INTO original_source_rows VALUES (1, 1, 'Sheet1', 1, 'TITLE', 'NO', NULL, NULL, NULL, '0', '0', '0', '0', '0', '0', '{}')")
    conn.execute("INSERT INTO original_source_rows VALUES (2, 1, 'Sheet1', 3, 'HEADING', 'SI', NULL, 'EFECTIVO', NULL, '100', '0', '100', '1000', '0', '1000', '{}')")
    conn.execute("INSERT INTO original_source_rows VALUES (3, 1, 'Sheet1', 4, 'ACCOUNT', 'SI', '110111', NULL, 'Caja', '25.17', '0', '25.17', '1000000', '0', '1000000', '{}')")
    conn.execute("INSERT INTO original_source_rows VALUES (4, 1, 'Sheet1', 5, 'ACCOUNT', 'NO', '110113', NULL, 'Fondo Fijo', '0', '0', '0', '0', '0', '0', '{}')")
    
    # Impulsa source rows
    conn.execute("INSERT INTO original_source_rows VALUES (5, 2, 'Sheet1', 1, 'TITLE', 'NO', NULL, NULL, NULL, '0', '0', '0', '0', '0', '0', '{}')")
    conn.execute("INSERT INTO original_source_rows VALUES (6, 2, 'Sheet1', 3, 'HEADING', 'SI', NULL, 'EFECTIVO', NULL, '50', '0', '50', '500000', '0', '500000', '{}')")
    conn.execute("INSERT INTO original_source_rows VALUES (7, 2, 'Sheet1', 4, 'ACCOUNT', 'NO', '110111', NULL, 'Caja', '0', '0', '0', '0', '0', '0', '{}')")
    conn.execute("INSERT INTO original_source_rows VALUES (8, 2, 'Sheet1', 5, 'ACCOUNT', 'NO', '110113', NULL, 'Fondo Fijo', '0', '0', '0', '0', '0', '0', '{}')")
    
    # Consolidated balances
    conn.execute("INSERT INTO consolidated_balances VALUES (1, 1, 1, 'ACCOUNT', '110111', '110111', NULL, 'Caja', 'Caja', '25.17', '0', '25.17', '1000000', '0', '1000000', '{\"eplaza_source_row\": 4, \"impulsa_source_row\": 4, \"key\": \"110111\"}')")
    conn.execute("INSERT INTO consolidated_balances VALUES (2, 1, 1, 'ACCOUNT', '110113', '110113', NULL, 'Fondo Fijo', 'Fondo Fijo', '0', '0', '0', '0', '0', '0', '{\"eplaza_source_row\": 5, \"impulsa_source_row\": 5, \"key\": \"110113\"}')")
    conn.commit()
    conn.close()
    return db_path


def test_generate_canonical_financial_workbook(canonical_test_db, tmp_path):
    out_file = tmp_path / "KTMA_FINANCIAL_WORKBOOK_2026.08.xlsx"
    downloads_file = tmp_path / "Downloads" / "KTMA_FINANCIAL_WORKBOOK_2026.08.xlsx"

    res = generate_canonical_financial_workbook(
        db_path=canonical_test_db,
        output_path=out_file,
        downloads_copy_path=downloads_file,
    )

    assert res["closure_bot_verdict"] == "PASS"
    assert res["source_reconciliation"] == "PASS"
    assert res["fm_reconciliation"] == "PASS"
    assert Path(out_file).exists()