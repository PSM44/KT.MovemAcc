"""PH1.5 SQLite foundation for persisted accounting lineage.

This module is intentionally independent from the PH1 workbook writer.  It
reuses the accepted XLSB parser and semantic criteria definitions, then stores
source rows, normalized observations, consolidated balances, and reconciliation
checks in a local SQLite database.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable, Optional

from kt_movemacc import engine
from kt_movemacc.cli import _standard_raw_paths

SCHEMA_VERSION = 1
DEFAULT_DB_PATH = Path("DATA") / "KTMA.sqlite"
ENTITY_CODES = ("EPLAZA", "IMPULSA")
DECIMAL_SCALE = Decimal("0.000001")


@dataclass(frozen=True)
class ImportResult:
    period: str
    database_path: Path
    run_id: int
    source_files: int
    source_rows: int
    observations: int
    consolidated_rows: int
    rule_checks: int
    reconciliation_status: str
    idempotent: bool


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decimal_text(value: object, places: Decimal = DECIMAL_SCALE) -> str:
    """Convert numeric source values to canonical decimal text for SQLite."""
    dec = Decimal(str(value or 0))
    return str(dec.quantize(places, rounding=ROUND_HALF_UP))


def connect(db_path: Path = DEFAULT_DB_PATH, *, read_only: bool = False) -> sqlite3.Connection:
    db_path = Path(db_path)
    if read_only:
        uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database(db_path: Path = DEFAULT_DB_PATH) -> None:
    with connect(db_path) as conn:
        apply_migrations(conn)


def apply_migrations(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    current = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()[0]
    if current >= SCHEMA_VERSION:
        return
    conn.executescript(SCHEMA_SQL_V1)
    conn.execute(
        "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
        (SCHEMA_VERSION, "ph15_foundation_v1"),
    )


SCHEMA_SQL_V1 = """
CREATE TABLE entities (
    entity_id INTEGER PRIMARY KEY,
    entity_code TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL
);

CREATE TABLE accounting_periods (
    period_id INTEGER PRIMARY KEY,
    period_code TEXT NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    UNIQUE(year, month)
);

CREATE TABLE source_files (
    source_file_id INTEGER PRIMARY KEY,
    period_id INTEGER NOT NULL REFERENCES accounting_periods(period_id) ON DELETE RESTRICT,
    entity_id INTEGER NOT NULL REFERENCES entities(entity_id) ON DELETE RESTRICT,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    byte_size INTEGER NOT NULL,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(period_id, entity_id)
);

CREATE TABLE processing_runs (
    run_id INTEGER PRIMARY KEY,
    period_id INTEGER NOT NULL REFERENCES accounting_periods(period_id) ON DELETE RESTRICT,
    run_type TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    input_fingerprint TEXT NOT NULL,
    message TEXT
);

CREATE TABLE original_source_rows (
    original_row_id INTEGER PRIMARY KEY,
    source_file_id INTEGER NOT NULL REFERENCES source_files(source_file_id) ON DELETE CASCADE,
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
    raw_payload_json TEXT NOT NULL,
    UNIQUE(source_file_id, source_sheet, source_row_number)
);

CREATE TABLE account_observations (
    observation_id INTEGER PRIMARY KEY,
    original_row_id INTEGER NOT NULL UNIQUE REFERENCES original_source_rows(original_row_id) ON DELETE CASCADE,
    period_id INTEGER NOT NULL REFERENCES accounting_periods(period_id) ON DELETE RESTRICT,
    entity_id INTEGER NOT NULL REFERENCES entities(entity_id) ON DELETE RESTRICT,
    row_type TEXT NOT NULL,
    account_code TEXT,
    semantic_key TEXT,
    label TEXT NOT NULL,
    debit_uf TEXT NOT NULL,
    credit_uf TEXT NOT NULL,
    value_uf TEXT NOT NULL,
    debit_clp TEXT NOT NULL,
    credit_clp TEXT NOT NULL,
    value_clp TEXT NOT NULL,
    is_zero INTEGER NOT NULL CHECK(is_zero IN (0,1)),
    source_order INTEGER NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE
);

CREATE TABLE hierarchy_context (
    hierarchy_id INTEGER PRIMARY KEY,
    period_id INTEGER NOT NULL REFERENCES accounting_periods(period_id) ON DELETE RESTRICT,
    entity_id INTEGER NOT NULL REFERENCES entities(entity_id) ON DELETE RESTRICT,
    parent_observation_id INTEGER NOT NULL REFERENCES account_observations(observation_id) ON DELETE CASCADE,
    child_observation_id INTEGER NOT NULL REFERENCES account_observations(observation_id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL,
    inference_status TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    UNIQUE(parent_observation_id, child_observation_id, relationship_type)
);

CREATE TABLE rule_versions (
    rule_version_id INTEGER PRIMARY KEY,
    rule_set_name TEXT NOT NULL,
    version_code TEXT NOT NULL,
    source_path TEXT,
    source_sha256 TEXT,
    approval_status TEXT NOT NULL,
    UNIQUE(rule_set_name, version_code)
);

CREATE TABLE calculation_lineage (
    lineage_id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES processing_runs(run_id) ON DELETE CASCADE,
    rule_version_id INTEGER REFERENCES rule_versions(rule_version_id) ON DELETE RESTRICT,
    rule_id TEXT NOT NULL,
    company_code TEXT NOT NULL,
    target_observation_id INTEGER REFERENCES account_observations(observation_id) ON DELETE SET NULL,
    semantic_key TEXT NOT NULL,
    formula_text TEXT NOT NULL,
    calculated_uf TEXT NOT NULL,
    source_uf TEXT NOT NULL,
    difference_uf TEXT NOT NULL,
    status TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE consolidated_balances (
    consolidated_id INTEGER PRIMARY KEY,
    period_id INTEGER NOT NULL REFERENCES accounting_periods(period_id) ON DELETE RESTRICT,
    run_id INTEGER NOT NULL REFERENCES processing_runs(run_id) ON DELETE CASCADE,
    row_type TEXT NOT NULL,
    account_code TEXT,
    semantic_key TEXT,
    heading_text TEXT,
    eplaza_description TEXT,
    impulsa_description TEXT,
    eplaza_value_uf TEXT NOT NULL,
    impulsa_value_uf TEXT NOT NULL,
    total_value_uf TEXT NOT NULL,
    eplaza_value_clp TEXT NOT NULL,
    impulsa_value_clp TEXT NOT NULL,
    total_value_clp TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE reconciliation_checks (
    check_id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES processing_runs(run_id) ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    status TEXT NOT NULL,
    expected_value TEXT,
    observed_value TEXT,
    difference_value TEXT,
    tolerance TEXT,
    evidence_json TEXT NOT NULL
);

CREATE INDEX idx_observations_period_entity_code ON account_observations(period_id, entity_id, account_code);
CREATE INDEX idx_observations_semantic ON account_observations(period_id, entity_id, semantic_key);
CREATE INDEX idx_consolidated_period_code ON consolidated_balances(period_id, account_code);
CREATE UNIQUE INDEX idx_consolidated_run_business_key
    ON consolidated_balances(period_id, run_id, row_type, IFNULL(account_code, IFNULL(semantic_key, heading_text)));
CREATE INDEX idx_lineage_rule ON calculation_lineage(rule_id, company_code);
CREATE INDEX idx_reconciliation_run_status ON reconciliation_checks(run_id, status);

INSERT OR IGNORE INTO entities(entity_code, display_name) VALUES
    ('EPLAZA', 'Inmobiliaria Eplaza'),
    ('IMPULSA', 'Grupo Impulsa');
"""


def _period_parts(period: str) -> tuple[int, int]:
    year_s, month_s = period.split(".")
    return int(year_s), int(month_s)


def _ensure_period(conn: sqlite3.Connection, period: str) -> int:
    year, month = _period_parts(period)
    conn.execute(
        "INSERT OR IGNORE INTO accounting_periods(period_code, year, month) VALUES (?, ?, ?)",
        (period, year, month),
    )
    return conn.execute("SELECT period_id FROM accounting_periods WHERE period_code = ?", (period,)).fetchone()[0]


def _entity_id(conn: sqlite3.Connection, entity_code: str) -> int:
    return conn.execute("SELECT entity_id FROM entities WHERE entity_code = ?", (entity_code,)).fetchone()[0]


def _source_file(
    conn: sqlite3.Connection,
    *,
    period_id: int,
    entity_id: int,
    path: Path,
    allow_hash_change: bool,
) -> tuple[int, bool]:
    digest = sha256(path)
    existing = conn.execute(
        "SELECT source_file_id, sha256 FROM source_files WHERE period_id = ? AND entity_id = ?",
        (period_id, entity_id),
    ).fetchone()
    if existing:
        if existing["sha256"] != digest:
            raise ValueError(f"Source hash changed for {path.name}: {existing['sha256']} != {digest}")
        return int(existing["source_file_id"]), True

    cur = conn.execute(
        """
        INSERT INTO source_files(period_id, entity_id, file_path, file_name, sha256, byte_size)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (period_id, entity_id, str(path), path.name, digest, path.stat().st_size),
    )
    return int(cur.lastrowid), False


def _insert_source_rows(
    conn: sqlite3.Connection,
    *,
    period_id: int,
    entity_id: int,
    source_file_id: int,
    rows: list[engine.AccountRow],
    entity_code: str,
) -> int:
    inserted = 0
    for order, row in enumerate(rows, start=1):
        raw_payload = {
            "source_sheet": row.source_sheet,
            "source_row": row.source_row,
            "filtro": row.filtro,
            "account_code": row.code,
            "heading": row.heading,
            "description": row.description,
            "heading_key": row.heading_key,
        }
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO original_source_rows(
                source_file_id, source_sheet, source_row_number, row_type, filtro, account_code,
                heading_text, account_description, debitos_uf, creditos_uf, valores_uf,
                debitos_clp, creditos_clp, valores_clp, raw_payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_file_id,
                row.source_sheet,
                row.source_row,
                row.row_type,
                row.filtro,
                row.code,
                row.heading,
                row.description,
                decimal_text(row.deb_uf),
                decimal_text(row.cred_uf),
                decimal_text(row.bal_uf),
                decimal_text(row.deb_clp),
                decimal_text(row.cred_clp),
                decimal_text(row.bal_clp),
                json.dumps(raw_payload, ensure_ascii=False, sort_keys=True),
            ),
        )
        if cur.rowcount:
            inserted += 1
        original_row_id = conn.execute(
            """
            SELECT original_row_id FROM original_source_rows
            WHERE source_file_id = ? AND source_sheet = ? AND source_row_number = ?
            """,
            (source_file_id, row.source_sheet, row.source_row),
        ).fetchone()[0]
        label = row.label
        semantic_key = row.heading_key if row.row_type == "HEADING" else row.code
        idempotency_key = f"{entity_code}:{source_file_id}:{row.source_sheet}:{row.source_row}"
        conn.execute(
            """
            INSERT OR IGNORE INTO account_observations(
                original_row_id, period_id, entity_id, row_type, account_code, semantic_key, label,
                debit_uf, credit_uf, value_uf, debit_clp, credit_clp, value_clp,
                is_zero, source_order, idempotency_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                original_row_id,
                period_id,
                entity_id,
                row.row_type,
                row.code,
                semantic_key,
                label,
                decimal_text(row.deb_uf),
                decimal_text(row.cred_uf),
                decimal_text(row.bal_uf),
                decimal_text(row.deb_clp),
                decimal_text(row.cred_clp),
                decimal_text(row.bal_clp),
                1 if row.is_zero else 0,
                order,
                idempotency_key,
            ),
        )
    return inserted


def _observation_lookup(conn: sqlite3.Connection, period_id: int, entity_id: int) -> dict[str, int]:
    rows = conn.execute(
        """
        SELECT observation_id, account_code, semantic_key FROM account_observations
        WHERE period_id = ? AND entity_id = ?
        """,
        (period_id, entity_id),
    ).fetchall()
    lookup = {}
    for row in rows:
        if row["account_code"]:
            lookup[f"code:{row['account_code']}"] = row["observation_id"]
        if row["semantic_key"]:
            lookup[f"heading:{row['semantic_key']}"] = row["observation_id"]
    return lookup


def _insert_hierarchy(
    conn: sqlite3.Connection,
    *,
    period_id: int,
    entity_id: int,
    rows: list[engine.AccountRow],
) -> None:
    blocks = engine.infer_formula_blocks(rows)
    lookup = _observation_lookup(conn, period_id, entity_id)
    for parent_idx, block in blocks.items():
        parent = rows[parent_idx]
        parent_key = f"heading:{parent.heading_key}"
        parent_id = lookup.get(parent_key)
        if parent_id is None:
            continue
        for child_idx in block.account_indexes:
            child = rows[child_idx]
            child_id = lookup.get(f"code:{child.code}") if child.code else None
            if child_id is None:
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO hierarchy_context(
                    period_id, entity_id, parent_observation_id, child_observation_id,
                    relationship_type, inference_status, evidence_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    period_id,
                    entity_id,
                    parent_id,
                    child_id,
                    "SUBTOTAL_MEMBER",
                    block.status,
                    json.dumps({"diffs": block.diffs}, ensure_ascii=False, sort_keys=True),
                ),
            )


def _criteria_file_metadata(root: Path) -> tuple[str, str, str]:
    path = root / "04_CONFIG" / "CRITERIA" / "PH1_CRITERIA_REGISTER.json"
    if not path.exists():
        return ("PH1_CRITERIA", "UNKNOWN", "")
    data = json.loads(path.read_text(encoding="utf-8"))
    return (str(path), data.get("version", "UNKNOWN"), sha256(path))


def _insert_rule_version(conn: sqlite3.Connection, root: Path) -> int:
    source_path, version, digest = _criteria_file_metadata(root)
    conn.execute(
        """
        INSERT OR IGNORE INTO rule_versions(rule_set_name, version_code, source_path, source_sha256, approval_status)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("PH1_APPROVED_CRITERIA", version, source_path, digest, "HUMAN_MORCH_APPROVED"),
    )
    return conn.execute(
        "SELECT rule_version_id FROM rule_versions WHERE rule_set_name = ? AND version_code = ?",
        ("PH1_APPROVED_CRITERIA", version),
    ).fetchone()[0]


def _insert_consolidated(
    conn: sqlite3.Connection,
    *,
    period_id: int,
    run_id: int,
    aligned: list[engine.AlignedRow],
) -> int:
    inserted = 0
    for row in aligned:
        ep_uf = Decimal(decimal_text(row.ep.bal_uf if row.ep else 0))
        im_uf = Decimal(decimal_text(row.im.bal_uf if row.im else 0))
        ep_clp = Decimal(decimal_text(row.ep.bal_clp if row.ep else 0))
        im_clp = Decimal(decimal_text(row.im.bal_clp if row.im else 0))
        evidence = {
            "eplaza_source_row": row.ep.source_row if row.ep else None,
            "impulsa_source_row": row.im.source_row if row.im else None,
            "key": row.key,
        }
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO consolidated_balances(
                period_id, run_id, row_type, account_code, semantic_key, heading_text,
                eplaza_description, impulsa_description, eplaza_value_uf, impulsa_value_uf,
                total_value_uf, eplaza_value_clp, impulsa_value_clp, total_value_clp, evidence_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                period_id,
                run_id,
                row.row_type,
                row.code,
                row.key,
                row.heading,
                row.ep_desc,
                row.im_desc,
                str(ep_uf),
                str(im_uf),
                str((ep_uf + im_uf).quantize(DECIMAL_SCALE)),
                str(ep_clp),
                str(im_clp),
                str((ep_clp + im_clp).quantize(DECIMAL_SCALE)),
                json.dumps(evidence, ensure_ascii=False, sort_keys=True),
            ),
        )
        inserted += int(cur.rowcount or 0)
    return inserted


def _rule_target_observation_id(
    conn: sqlite3.Connection,
    *,
    period_id: int,
    company_code: str,
    semantic_key: str,
) -> Optional[int]:
    entity_id = _entity_id(conn, company_code)
    row = conn.execute(
        """
        SELECT observation_id FROM account_observations
        WHERE period_id = ? AND entity_id = ? AND semantic_key = ?
        """,
        (period_id, entity_id, semantic_key),
    ).fetchone()
    return int(row["observation_id"]) if row else None


def _insert_rule_lineage(
    conn: sqlite3.Connection,
    *,
    period_id: int,
    run_id: int,
    rule_version_id: int,
    criteria_matrix: Iterable[dict[str, object]],
) -> int:
    inserted = 0
    for item in criteria_matrix:
        target_id = _rule_target_observation_id(
            conn,
            period_id=period_id,
            company_code=str(item["COMPANY"]),
            semantic_key=str(item["SEMANTIC_KEY"]),
        )
        cur = conn.execute(
            """
            INSERT INTO calculation_lineage(
                run_id, rule_version_id, rule_id, company_code, target_observation_id,
                semantic_key, formula_text, calculated_uf, source_uf, difference_uf, status, evidence_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                rule_version_id,
                item["RULE_ID"],
                item["COMPANY"],
                target_id,
                item["SEMANTIC_KEY"],
                item["EXCEL_FORMULA"],
                decimal_text(item["PYTHON_CALCULATED_UF"]),
                decimal_text(item["SOURCE_UF"]),
                decimal_text(item["DIFFERENCE_UF"]),
                item["STATUS"],
                json.dumps(item.get("EVIDENCE", {}), ensure_ascii=False, sort_keys=True),
            ),
        )
        inserted += int(cur.rowcount or 0)
    return inserted


def _insert_check(
    conn: sqlite3.Connection,
    run_id: int,
    name: str,
    status: str,
    expected: object,
    observed: object,
    difference: object,
    evidence: dict[str, object],
    tolerance: str = "0.010000",
) -> None:
    conn.execute(
        """
        INSERT INTO reconciliation_checks(
            run_id, check_name, status, expected_value, observed_value, difference_value, tolerance, evidence_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            name,
            status,
            decimal_text(expected) if expected is not None else None,
            decimal_text(observed) if observed is not None else None,
            decimal_text(difference) if difference is not None else None,
            tolerance,
            json.dumps(evidence, ensure_ascii=False, sort_keys=True),
        ),
    )


def _latest_run_id(conn: sqlite3.Connection, period: str) -> int:
    row = conn.execute(
        """
        SELECT pr.run_id
        FROM processing_runs pr
        JOIN accounting_periods ap ON ap.period_id = pr.period_id
        WHERE ap.period_code = ? AND pr.status = 'PASS'
        ORDER BY pr.run_id DESC
        LIMIT 1
        """,
        (period,),
    ).fetchone()
    if row is None:
        raise LookupError(f"No successful PH1.5 run found for period {period}")
    return int(row["run_id"])


def _observation_value(
    conn: sqlite3.Connection,
    *,
    period_id: int,
    entity_code: str,
    semantic_key: str,
) -> Decimal:
    row = conn.execute(
        """
        SELECT ao.value_uf
        FROM account_observations ao
        JOIN entities e ON e.entity_id = ao.entity_id
        WHERE ao.period_id = ? AND e.entity_code = ? AND ao.semantic_key = ?
        """,
        (period_id, entity_code, semantic_key),
    ).fetchone()
    return Decimal(row["value_uf"]) if row else Decimal("0.000000")


def _rule_member_sum_from_observations(
    conn: sqlite3.Connection,
    *,
    period_id: int,
    company_code: str,
    evidence_json: str,
    formula_text: str,
) -> Decimal:
    evidence = json.loads(evidence_json or "{}")
    members = evidence.get("members", [])
    values = [
        _observation_value(conn, period_id=period_id, entity_code=company_code, semantic_key=member["key"])
        for member in members
    ]
    if formula_text.startswith("=-"):
        return (-values[0]).quantize(DECIMAL_SCALE) if values else Decimal("0.000000")
    return sum(values, Decimal("0.000000")).quantize(DECIMAL_SCALE)


def independent_rule_matrix(db_path: Path, period: str = "2026.08") -> list[dict[str, object]]:
    with connect(db_path, read_only=True) as conn:
        run_id = _latest_run_id(conn, period)
        period_id = conn.execute("SELECT period_id FROM accounting_periods WHERE period_code = ?", (period,)).fetchone()[0]
        rows = conn.execute(
            """
            SELECT rule_id, company_code, semantic_key, formula_text, calculated_uf,
                   source_uf, difference_uf, status, evidence_json
            FROM calculation_lineage
            WHERE run_id = ?
            ORDER BY rule_id
            """,
            (run_id,),
        ).fetchall()
        matrix = []
        for row in rows:
            observed = Decimal(row["calculated_uf"])
            independent = _rule_member_sum_from_observations(
                conn,
                period_id=period_id,
                company_code=row["company_code"],
                evidence_json=row["evidence_json"],
                formula_text=row["formula_text"],
            )
            source = _observation_value(
                conn,
                period_id=period_id,
                entity_code=row["company_code"],
                semantic_key=row["semantic_key"],
            )
            diff = independent - source
            observed_diff = observed - independent
            status = "INDEPENDENTLY_VERIFIED" if abs(diff) <= Decimal("0.010000") and abs(observed_diff) <= Decimal("0.010000") else "FAILED"
            matrix.append(
                {
                    "rule_id": row["rule_id"],
                    "company": row["company_code"],
                    "semantic_key": row["semantic_key"],
                    "formula_text": row["formula_text"],
                    "source_uf": str(source),
                    "independent_calculated_uf": str(independent),
                    "stored_calculated_uf": row["calculated_uf"],
                    "difference_uf": str(diff.quantize(DECIMAL_SCALE)),
                    "stored_vs_independent_uf": str(observed_diff.quantize(DECIMAL_SCALE)),
                    "status": status,
                }
            )
        return matrix


def independent_cam_heading_matrix(db_path: Path, period: str = "2026.08") -> list[dict[str, object]]:
    with connect(db_path, read_only=True) as conn:
        run_id = _latest_run_id(conn, period)
        period_id = conn.execute("SELECT period_id FROM accounting_periods WHERE period_code = ?", (period,)).fetchone()[0]
        rows = conn.execute(
            """
            SELECT row_type, semantic_key, heading_text, eplaza_value_uf, impulsa_value_uf, total_value_uf
            FROM consolidated_balances
            WHERE run_id = ? AND row_type = 'HEADING'
            ORDER BY consolidated_id
            """,
            (run_id,),
        ).fetchall()
        matrix = []
        for row in rows:
            key = row["semantic_key"]
            ep = _observation_value(conn, period_id=period_id, entity_code="EPLAZA", semantic_key=key) if key else Decimal("0.000000")
            im = _observation_value(conn, period_id=period_id, entity_code="IMPULSA", semantic_key=key) if key else Decimal("0.000000")
            expected = (ep + im).quantize(DECIMAL_SCALE)
            stored_total = Decimal(row["total_value_uf"])
            diff = stored_total - expected
            stored_ep_diff = Decimal(row["eplaza_value_uf"]) - ep
            stored_im_diff = Decimal(row["impulsa_value_uf"]) - im
            status = (
                "INDEPENDENTLY_VERIFIED"
                if abs(diff) <= Decimal("0.010000")
                and abs(stored_ep_diff) <= Decimal("0.010000")
                and abs(stored_im_diff) <= Decimal("0.010000")
                else "FAILED"
            )
            matrix.append(
                {
                    "semantic_key": key,
                    "heading_text": row["heading_text"],
                    "source_eplaza_uf": str(ep),
                    "source_impulsa_uf": str(im),
                    "independent_total_uf": str(expected),
                    "stored_eplaza_uf": row["eplaza_value_uf"],
                    "stored_impulsa_uf": row["impulsa_value_uf"],
                    "stored_total_uf": row["total_value_uf"],
                    "difference_uf": str(diff.quantize(DECIMAL_SCALE)),
                    "status": status,
                }
            )
        return matrix


def integrity_report(db_path: Path) -> dict[str, object]:
    with connect(db_path, read_only=True) as conn:
        return {
            "integrity_check": conn.execute("PRAGMA integrity_check").fetchone()[0],
            "foreign_key_check": [dict(row) for row in conn.execute("PRAGMA foreign_key_check").fetchall()],
            "quick_check": conn.execute("PRAGMA quick_check").fetchone()[0],
        }


def backup_database(db_path: Path, backup_path: Path) -> None:
    backup_path = Path(backup_path)
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path, read_only=True) as source:
        target = sqlite3.connect(backup_path)
        try:
            source.backup(target)
        finally:
            target.close()


def _reconcile_and_store(
    conn: sqlite3.Connection,
    *,
    period_id: int,
    run_id: int,
    metrics: dict[str, object],
) -> str:
    failures = 0
    for item in metrics["approved_criteria"]["matrix"]:
        target_source = _observation_value(
            conn,
            period_id=period_id,
            entity_code=str(item["COMPANY"]),
            semantic_key=str(item["SEMANTIC_KEY"]),
        )
        independent = sum(
            (
                _observation_value(
                    conn,
                    period_id=period_id,
                    entity_code=str(item["COMPANY"]),
                    semantic_key=str(member["key"]),
                )
                for member in item["EVIDENCE"]["members"]
            ),
            Decimal("0.000000"),
        )
        if str(item["EXCEL_FORMULA"]).startswith("=-"):
            independent = -_observation_value(
                conn,
                period_id=period_id,
                entity_code=str(item["COMPANY"]),
                semantic_key=str(item["EVIDENCE"]["members"][0]["key"]),
            )
        independent = independent.quantize(DECIMAL_SCALE)
        diff = independent - target_source
        status = "PASS" if abs(diff) <= Decimal("0.010000") and item["STATUS"] == "NUMERICALLY_VERIFIED" else "HUMAN_MORCH_REVIEW_REQUIRED"
        failures += 0 if status == "PASS" else 1
        _insert_check(
            conn,
            run_id,
            f"PH1_RULE_{item['RULE_ID']}",
            status,
            target_source,
            independent,
            diff,
            {"destination": item["EXCEL_DESTINATION"], "formula": item["EXCEL_FORMULA"]},
        )

    hernando = conn.execute(
        """
        SELECT * FROM consolidated_balances
        WHERE period_id = ? AND semantic_key = 'PROYECTO HERNANDO DE AGUIRRE#1'
        ORDER BY consolidated_id DESC LIMIT 1
        """,
        (period_id,),
    ).fetchone()
    if hernando:
        total = Decimal(hernando["total_value_uf"])
        diff = total - Decimal("550120.960000")
        status = "PASS" if abs(diff) <= Decimal("0.010000") else "HUMAN_MORCH_REVIEW_REQUIRED"
        failures += 0 if status == "PASS" else 1
        _insert_check(
            conn,
            run_id,
            "HERNANDO_DE_AGUIRRE_CONSOLIDATED_UF",
            status,
            "550120.960000",
            total,
            diff,
            {"semantic_key": hernando["semantic_key"], "heading_text": hernando["heading_text"]},
        )
    else:
        failures += 1
        _insert_check(conn, run_id, "HERNANDO_DE_AGUIRRE_CONSOLIDATED_UF", "HUMAN_MORCH_REVIEW_REQUIRED", "550120.960000", None, None, {})

    cam_rows = conn.execute(
        """
        SELECT consolidated_id, row_type, account_code, semantic_key, heading_text,
               eplaza_value_uf, impulsa_value_uf, total_value_uf
        FROM consolidated_balances
        WHERE period_id = ? AND run_id = ? AND row_type = 'HEADING'
        ORDER BY consolidated_id
        """,
        (period_id, run_id),
    ).fetchall()
    for row in cam_rows:
        expected_ep = _observation_value(conn, period_id=period_id, entity_code="EPLAZA", semantic_key=row["semantic_key"]) if row["semantic_key"] else Decimal("0.000000")
        expected_im = _observation_value(conn, period_id=period_id, entity_code="IMPULSA", semantic_key=row["semantic_key"]) if row["semantic_key"] else Decimal("0.000000")
        expected = expected_ep + expected_im
        observed = Decimal(row["total_value_uf"])
        diff = observed - expected
        ep_diff = Decimal(row["eplaza_value_uf"]) - expected_ep
        im_diff = Decimal(row["impulsa_value_uf"]) - expected_im
        status = "PASS" if abs(diff) <= Decimal("0.010000") and abs(ep_diff) <= Decimal("0.010000") and abs(im_diff) <= Decimal("0.010000") else "HUMAN_MORCH_REVIEW_REQUIRED"
        failures += 0 if status == "PASS" else 1
        label = row["semantic_key"] or row["heading_text"] or f"heading_{row['consolidated_id']}"
        safe_label = "".join(ch if ch.isalnum() else "_" for ch in label.upper()).strip("_")
        _insert_check(
            conn,
            run_id,
            f"CAM_HEADING_TOTAL_UF_{safe_label}",
            status,
            expected,
            observed,
            diff,
            {
                "row_type": row["row_type"],
                "account_code": row["account_code"],
                "semantic_key": row["semantic_key"],
                "heading_text": row["heading_text"],
            },
        )

    return "PASS" if failures == 0 else "PARTIAL"


def import_period(
    db_path: Path = DEFAULT_DB_PATH,
    *,
    root: Path = Path("."),
    period: str,
    raw_eplaza: Optional[Path] = None,
    raw_impulsa: Optional[Path] = None,
    allow_hash_change: bool = False,
) -> ImportResult:
    root = Path(root).resolve()
    raw_eplaza, raw_impulsa = _resolve_inputs(root, period, raw_eplaza, raw_impulsa)
    input_fingerprint = "|".join([sha256(raw_eplaza), sha256(raw_impulsa)])

    with connect(db_path) as conn:
        try:
            conn.execute("BEGIN")
            apply_migrations(conn)
            period_id = _ensure_period(conn, period)
            run = conn.execute(
                """
                INSERT INTO processing_runs(period_id, run_type, status, input_fingerprint, message)
                VALUES (?, ?, ?, ?, ?)
                """,
                (period_id, "PH15_IMPORT", "RUNNING", input_fingerprint, "Import started"),
            )
            run_id = int(run.lastrowid)
            ep_rows = engine.parse_xlsb(raw_eplaza)
            im_rows = engine.parse_xlsb(raw_impulsa)

            source_file_count = 0
            source_row_count = 0
            idempotent = True
            for entity_code, path, rows in (
                ("EPLAZA", raw_eplaza, ep_rows),
                ("IMPULSA", raw_impulsa, im_rows),
            ):
                entity_id = _entity_id(conn, entity_code)
                source_file_id, existed = _source_file(
                    conn,
                    period_id=period_id,
                    entity_id=entity_id,
                    path=path,
                    allow_hash_change=allow_hash_change,
                )
                source_file_count += 1
                inserted_rows = _insert_source_rows(
                    conn,
                    period_id=period_id,
                    entity_id=entity_id,
                    source_file_id=source_file_id,
                    rows=rows,
                    entity_code=entity_code,
                )
                source_row_count += inserted_rows
                idempotent = idempotent and existed and inserted_rows == 0
                _insert_hierarchy(conn, period_id=period_id, entity_id=entity_id, rows=rows)

            aligned = engine.align(ep_rows, im_rows)
            workbook, metrics, _audit = engine.write_workbook(period, ep_rows, im_rows, aligned, raw_eplaza, raw_impulsa)
            del workbook
            consolidated_count = _insert_consolidated(conn, period_id=period_id, run_id=run_id, aligned=aligned)
            rule_version_id = _insert_rule_version(conn, root)
            rule_checks = _insert_rule_lineage(
                conn,
                period_id=period_id,
                run_id=run_id,
                rule_version_id=rule_version_id,
                criteria_matrix=metrics["approved_criteria"]["matrix"],
            )
            reconciliation_status = _reconcile_and_store(conn, period_id=period_id, run_id=run_id, metrics=metrics)
            conn.execute(
                "UPDATE processing_runs SET status = ?, completed_at = CURRENT_TIMESTAMP, message = ? WHERE run_id = ?",
                (reconciliation_status, "Import completed", run_id),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return ImportResult(
        period=period,
        database_path=Path(db_path),
        run_id=run_id,
        source_files=source_file_count,
        source_rows=source_row_count,
        observations=_count(db_path, "account_observations"),
        consolidated_rows=consolidated_count,
        rule_checks=rule_checks,
        reconciliation_status=reconciliation_status,
        idempotent=idempotent,
    )


def _resolve_inputs(root: Path, period: str, raw_eplaza: Optional[Path], raw_impulsa: Optional[Path]) -> tuple[Path, Path]:
    default_ep, default_im = _standard_raw_paths(root, period)
    ep = Path(raw_eplaza).resolve() if raw_eplaza else default_ep
    im = Path(raw_impulsa).resolve() if raw_impulsa else default_im
    if ep == im:
        raise ValueError(f"Ambiguous RAW inputs: EPLAZA and IMPULSA resolve to the same file {ep}")
    missing = [str(path) for path in (ep, im) if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing RAW input(s): " + " | ".join(missing))
    return ep, im


def _count(db_path: Path, table: str) -> int:
    with connect(db_path, read_only=True) as conn:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def lineage_for_hernando(db_path: Path, period: str = "2026.08") -> dict[str, object]:
    with connect(db_path, read_only=True) as conn:
        row = conn.execute(
            """
            SELECT cb.*, pr.run_id
            FROM consolidated_balances cb
            JOIN accounting_periods ap ON ap.period_id = cb.period_id
            JOIN processing_runs pr ON pr.run_id = cb.run_id
            WHERE ap.period_code = ? AND cb.semantic_key = 'PROYECTO HERNANDO DE AGUIRRE#1'
            ORDER BY cb.consolidated_id DESC LIMIT 1
            """,
            (period,),
        ).fetchone()
        if row is None:
            raise LookupError("No Hernando de Aguirre consolidated row found")
        evidence = json.loads(row["evidence_json"])
        sources = conn.execute(
            """
            SELECT e.entity_code, sf.file_name, sf.sha256, osr.source_sheet, osr.source_row_number,
                   ao.label, ao.value_uf, ao.value_clp
            FROM account_observations ao
            JOIN entities e ON e.entity_id = ao.entity_id
            JOIN original_source_rows osr ON osr.original_row_id = ao.original_row_id
            JOIN source_files sf ON sf.source_file_id = osr.source_file_id
            JOIN accounting_periods ap ON ap.period_id = ao.period_id
            WHERE ap.period_code = ? AND ao.semantic_key = 'PROYECTO HERNANDO DE AGUIRRE#1'
            ORDER BY e.entity_code
            """,
            (period,),
        ).fetchall()
        rule = conn.execute(
            """
            SELECT rule_id, formula_text, calculated_uf, source_uf, difference_uf, status, evidence_json
            FROM calculation_lineage
            WHERE run_id = ? AND semantic_key = 'PROYECTO HERNANDO DE AGUIRRE#1'
            ORDER BY lineage_id DESC LIMIT 1
            """,
            (row["run_id"],),
        ).fetchone()
        return {
            "period": period,
            "semantic_key": row["semantic_key"],
            "heading_text": row["heading_text"],
            "eplaza_uf": row["eplaza_value_uf"],
            "impulsa_uf": row["impulsa_value_uf"],
            "consolidated_uf": row["total_value_uf"],
            "source_evidence": [dict(src) for src in sources],
            "consolidated_evidence": evidence,
            "rule": dict(rule) if rule else None,
        }


def reconciliation_matrix(db_path: Path, period: str = "2026.08") -> list[dict[str, object]]:
    with connect(db_path, read_only=True) as conn:
        rows = conn.execute(
            """
            SELECT rc.check_name, rc.status, rc.expected_value, rc.observed_value,
                   rc.difference_value, rc.tolerance, rc.evidence_json
            FROM reconciliation_checks rc
            JOIN processing_runs pr ON pr.run_id = rc.run_id
            JOIN accounting_periods ap ON ap.period_id = pr.period_id
            WHERE ap.period_code = ?
            ORDER BY rc.check_id
            """,
            (period,),
        ).fetchall()
        return [dict(row) | {"evidence": json.loads(row["evidence_json"])} for row in rows]


def available_periods(db_path: Path) -> list[dict[str, object]]:
    with connect(db_path, read_only=True) as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT period_code, year, month FROM accounting_periods ORDER BY period_code"
            ).fetchall()
        ]


def available_entities(db_path: Path) -> list[dict[str, object]]:
    with connect(db_path, read_only=True) as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT entity_code, display_name FROM entities ORDER BY entity_code"
            ).fetchall()
        ]


def source_versions(db_path: Path, period: str) -> list[dict[str, object]]:
    with connect(db_path, read_only=True) as conn:
        return [
            dict(row)
            for row in conn.execute(
                """
                SELECT ap.period_code, e.entity_code, sf.file_name, sf.file_path,
                       sf.sha256, sf.byte_size, sf.imported_at
                FROM source_files sf
                JOIN accounting_periods ap ON ap.period_id = sf.period_id
                JOIN entities e ON e.entity_id = sf.entity_id
                WHERE ap.period_code = ?
                ORDER BY e.entity_code
                """,
                (period,),
            ).fetchall()
        ]


def processing_runs(db_path: Path, period: str) -> list[dict[str, object]]:
    with connect(db_path, read_only=True) as conn:
        return [
            dict(row)
            for row in conn.execute(
                """
                SELECT pr.run_id, ap.period_code, pr.run_type, pr.status,
                       pr.started_at, pr.completed_at, pr.input_fingerprint, pr.message
                FROM processing_runs pr
                JOIN accounting_periods ap ON ap.period_id = pr.period_id
                WHERE ap.period_code = ?
                ORDER BY pr.run_id
                """,
                (period,),
            ).fetchall()
        ]


def observations_by_code(db_path: Path, period: str, account_code: str) -> list[dict[str, object]]:
    with connect(db_path, read_only=True) as conn:
        return [
            dict(row)
            for row in conn.execute(
                """
                SELECT ap.period_code, e.entity_code, ao.row_type, ao.account_code,
                       ao.semantic_key, ao.label, ao.debit_uf, ao.credit_uf, ao.value_uf,
                       ao.debit_clp, ao.credit_clp, ao.value_clp, ao.is_zero,
                       osr.source_sheet, osr.source_row_number, sf.file_name, sf.sha256
                FROM account_observations ao
                JOIN accounting_periods ap ON ap.period_id = ao.period_id
                JOIN entities e ON e.entity_id = ao.entity_id
                JOIN original_source_rows osr ON osr.original_row_id = ao.original_row_id
                JOIN source_files sf ON sf.source_file_id = osr.source_file_id
                WHERE ap.period_code = ? AND ao.account_code = ?
                ORDER BY e.entity_code, ao.source_order
                """,
                (period, account_code),
            ).fetchall()
        ]


def consolidated_values(db_path: Path, period: str, *, account_code: Optional[str] = None, semantic_key: Optional[str] = None) -> list[dict[str, object]]:
    with connect(db_path, read_only=True) as conn:
        run_id = _latest_run_id(conn, period)
        where = ["cb.run_id = ?"]
        params: list[object] = [run_id]
        if account_code is not None:
            where.append("cb.account_code = ?")
            params.append(account_code)
        if semantic_key is not None:
            where.append("cb.semantic_key = ?")
            params.append(semantic_key)
        return [
            dict(row)
            for row in conn.execute(
                f"""
                SELECT cb.row_type, cb.account_code, cb.semantic_key, cb.heading_text,
                       cb.eplaza_description, cb.impulsa_description,
                       cb.eplaza_value_uf, cb.impulsa_value_uf, cb.total_value_uf,
                       cb.eplaza_value_clp, cb.impulsa_value_clp, cb.total_value_clp
                FROM consolidated_balances cb
                WHERE {' AND '.join(where)}
                ORDER BY cb.consolidated_id
                """,
                params,
            ).fetchall()
        ]


def rule_versions(db_path: Path) -> list[dict[str, object]]:
    with connect(db_path, read_only=True) as conn:
        return [
            dict(row)
            for row in conn.execute(
                """
                SELECT rule_set_name, version_code, source_path, source_sha256, approval_status
                FROM rule_versions
                ORDER BY rule_set_name, version_code
                """
            ).fetchall()
        ]


def unresolved_discrepancies(db_path: Path, period: str) -> list[dict[str, object]]:
    with connect(db_path, read_only=True) as conn:
        return [
            dict(row) | {"evidence": json.loads(row["evidence_json"])}
            for row in conn.execute(
                """
                SELECT rc.check_name, rc.status, rc.expected_value, rc.observed_value,
                       rc.difference_value, rc.tolerance, rc.evidence_json
                FROM reconciliation_checks rc
                JOIN processing_runs pr ON pr.run_id = rc.run_id
                JOIN accounting_periods ap ON ap.period_id = pr.period_id
                WHERE ap.period_code = ? AND rc.status <> 'PASS'
                ORDER BY rc.check_id
                """,
                (period,),
            ).fetchall()
        ]


def read_contract_query(
    db_path: Path,
    query: str,
    *,
    period: str = "2026.08",
    account_code: Optional[str] = None,
    semantic_key: Optional[str] = None,
) -> object:
    if query == "periods":
        return available_periods(db_path)
    if query == "entities":
        return available_entities(db_path)
    if query == "source-files":
        return source_versions(db_path, period)
    if query == "runs":
        return processing_runs(db_path, period)
    if query == "account":
        if not account_code:
            raise ValueError("account query requires account_code")
        return observations_by_code(db_path, period, account_code)
    if query == "consolidated":
        return consolidated_values(db_path, period, account_code=account_code, semantic_key=semantic_key)
    if query == "rule-versions":
        return rule_versions(db_path)
    if query == "discrepancies":
        return unresolved_discrepancies(db_path, period)
    if query == "hernando":
        return lineage_for_hernando(db_path, period)
    raise ValueError(f"Unsupported read-only query: {query}")


def database_summary(db_path: Path) -> dict[str, int]:
    with connect(db_path, read_only=True) as conn:
        return {
            "schema_version": conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0],
            "entities": conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0],
            "periods": conn.execute("SELECT COUNT(*) FROM accounting_periods").fetchone()[0],
            "source_files": conn.execute("SELECT COUNT(*) FROM source_files").fetchone()[0],
            "source_rows": conn.execute("SELECT COUNT(*) FROM original_source_rows").fetchone()[0],
            "observations": conn.execute("SELECT COUNT(*) FROM account_observations").fetchone()[0],
            "hierarchy_edges": conn.execute("SELECT COUNT(*) FROM hierarchy_context").fetchone()[0],
            "consolidated_balances": conn.execute("SELECT COUNT(*) FROM consolidated_balances").fetchone()[0],
            "lineage_rows": conn.execute("SELECT COUNT(*) FROM calculation_lineage").fetchone()[0],
            "reconciliation_checks": conn.execute("SELECT COUNT(*) FROM reconciliation_checks").fetchone()[0],
        }
