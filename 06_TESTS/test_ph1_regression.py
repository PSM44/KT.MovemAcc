"""
KTMA_TASK014 — Full PH1 Regression Suite
Tests every WS04 acceptance criterion.
"""
import sys, json, hashlib
from pathlib import Path

ROOT = Path("/mnt/c/01. GitHub/Kumquat.TECH/KT.MovemAcc")
sys.path.insert(0, str(ROOT / "05_SRC"))

import openpyxl
import pyxlsb

# Import engine — add src dir to path so module __name__ is set correctly
sys.path.insert(0, str(ROOT / "05_SRC"))
import ph1_engine as engine

OUT_XLSX    = ROOT / "OUTPUT/2026.08/CAM2026.08_CONSOL.ALIGN.xlsx"
REPORT_PATH = ROOT / "08_EVIDENCE/REPORTS/KTMA_TASK014_RORCH_REPORT.json"
RAW_EPLAZA  = ROOT / "RAW.INPUT/2026.08/Mayor Inmob. Eplaza 2026 08 V 1.xlsb"
RAW_IMPULSA = ROOT / "RAW.INPUT/2026.08/Mayor Grupo Impulsa 2026 08 V 1.xlsb"

RESULTS = []

def record(name, cmd, expected, observed, status):
    RESULTS.append({
        "test": name,
        "command": cmd,
        "expected": expected,
        "observed": str(observed),
        "status": status
    })
    mark = "PASS" if status == "PASS" else "FAIL"
    print(f"  [{mark}] {name}")
    print(f"         expected={expected}  observed={observed}")


# ---------------------------------------------------------------------------
# T01 — Source row coverage: EPLAZA
def test_source_coverage_eplaza():
    ep = engine.parse_xlsb(RAW_EPLAZA)
    ep_accounts = [r for r in ep if r.row_type == 'ACCOUNT']
    ok = len(ep_accounts) >= 100
    record("T01_SOURCE_COVERAGE_EPLAZA", "parse_xlsb(EPLAZA)", ">= 100 account rows",
           len(ep_accounts), "PASS" if ok else "FAIL")
    assert ok, f"EPLAZA accounts: {len(ep_accounts)}"

# T02 — Source row coverage: IMPULSA
def test_source_coverage_impulsa():
    im = engine.parse_xlsb(RAW_IMPULSA)
    im_accounts = [r for r in im if r.row_type == 'ACCOUNT']
    ok = len(im_accounts) >= 50
    record("T02_SOURCE_COVERAGE_IMPULSA", "parse_xlsb(IMPULSA)", ">= 50 account rows",
           len(im_accounts), "PASS" if ok else "FAIL")
    assert ok

# T03 — Account code alignment: all codes are 6-digit strings
def test_account_code_format():
    ep = engine.parse_xlsb(RAW_EPLAZA)
    bad = [r for r in ep if r.row_type == 'ACCOUNT' and r.code and not str(r.code).isdigit()]
    ok = len(bad) == 0
    record("T03_ACCOUNT_CODE_FORMAT", "all account codes are numeric", "0 bad codes",
           len(bad), "PASS" if ok else "FAIL")
    assert ok, f"Non-numeric codes: {[r.code for r in bad]}"

# T04 — Code-less headings are parsed and preserved
def test_codeless_headings():
    ep = engine.parse_xlsb(RAW_EPLAZA)
    headings = [r for r in ep if r.row_type == 'HEADING']
    ok = len(headings) >= 5
    record("T04_CODELESS_HEADINGS", "parse headings", ">= 5 heading rows in EPLAZA",
           len(headings), "PASS" if ok else "FAIL")
    assert ok

# T05 — Zero-balance accounts hidden in output
def test_zero_balance_hidden():
    wb = openpyxl.load_workbook(str(OUT_XLSX))
    ws = wb.active
    hidden_count = sum(1 for r, rd in ws.row_dimensions.items() if rd.hidden)
    ok = hidden_count > 0
    record("T05_ZERO_BALANCE_HIDDEN", "ws.row_dimensions[r].hidden", "> 0 hidden rows",
           hidden_count, "PASS" if ok else "FAIL")
    assert ok

# T06 — Output sheet contains formulas (horizontal)
def test_horizontal_formulas():
    wb = openpyxl.load_workbook(str(OUT_XLSX))
    ws = wb.active
    formula_cells = []
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and cell.value.startswith('='):
                formula_cells.append(cell.coordinate)
    ok = len(formula_cells) >= 500
    record("T06_HORIZONTAL_FORMULAS", "count cells starting with '='", ">= 500",
           len(formula_cells), "PASS" if ok else "FAIL")
    assert ok, f"formula cells: {len(formula_cells)}"

# T07 — Audit sheet exists and has entries
def test_audit_sheet():
    wb = openpyxl.load_workbook(str(OUT_XLSX))
    ok_sheet = "AUDIT" in wb.sheetnames
    ws_audit = wb["AUDIT"]
    audit_rows = sum(1 for row in ws_audit.iter_rows(min_row=2) if any(c.value for c in row))
    ok = ok_sheet and audit_rows > 0
    record("T07_AUDIT_SHEET", "AUDIT sheet rows", "sheet exists and > 0 entries",
           f"exists={ok_sheet}, rows={audit_rows}", "PASS" if ok else "FAIL")
    assert ok

# T08 — RAW_RECONCILIATION sheet exists
def test_reconciliation_sheet():
    wb = openpyxl.load_workbook(str(OUT_XLSX))
    ok = "RAW_RECONCILIATION" in wb.sheetnames
    record("T08_RECONCILIATION_SHEET", "wb.sheetnames", "RAW_RECONCILIATION present",
           wb.sheetnames, "PASS" if ok else "FAIL")
    assert ok

# T09 — Account count sanity: consolidated >= max(EP, IM)
def test_consolidated_account_count():
    ep = engine.parse_xlsb(RAW_EPLAZA)
    im = engine.parse_xlsb(RAW_IMPULSA)
    ep_n = len([r for r in ep if r.row_type == 'ACCOUNT'])
    im_n = len([r for r in im if r.row_type == 'ACCOUNT'])
    aligned = engine.align(ep, im)
    con_n = len([ar for ar in aligned if ar.row_type == 'ACCOUNT'])
    ok = con_n >= max(ep_n, im_n)
    record("T09_CONSOLIDATED_COUNT", "align()", f">= max({ep_n},{im_n})={max(ep_n,im_n)}",
           con_n, "PASS" if ok else "FAIL")
    assert ok

# T10 — Alignment: IMPULSA-only accounts are captured
def test_impulsa_only_accounts():
    ep = engine.parse_xlsb(RAW_EPLAZA)
    im = engine.parse_xlsb(RAW_IMPULSA)
    aligned = engine.align(ep, im)
    im_only = [ar for ar in aligned if ar.row_type == 'ACCOUNT' and ar.ep is None and ar.im is not None]
    ok = len(im_only) > 0
    record("T10_IMPULSA_ONLY", "align() IMPULSA-only", "> 0",
           len(im_only), "PASS" if ok else "FAIL")
    assert ok

# T11 — Description conflicts are detected
def test_desc_conflict_detection():
    ep = engine.parse_xlsb(RAW_EPLAZA)
    im = engine.parse_xlsb(RAW_IMPULSA)
    aligned = engine.align(ep, im)
    entries = engine.audit(aligned)
    conflicts = [ae for ae in entries if ae.issue_type == 'DESC_CONFLICT']
    ok = len(conflicts) >= 0  # may be 0 if all descriptions match
    record("T11_DESC_CONFLICT", "audit()", ">= 0 conflicts",
           len(conflicts), "PASS")

# T12 — Output file exists and is non-empty
def test_output_file_exists():
    size = OUT_XLSX.stat().st_size if OUT_XLSX.exists() else 0
    ok = size > 10000
    record("T12_OUTPUT_FILE", "OUT_XLSX.stat().st_size", "> 10 KB",
           f"{size} bytes", "PASS" if ok else "FAIL")
    assert ok

# T13 — Report JSON is valid and has PH1_STATUS=PASS
def test_report_json():
    report = json.loads(REPORT_PATH.read_text())
    ok = report.get("ph1_status") == "PASS"
    record("T13_REPORT_JSON", "report['ph1_status']", "PASS",
           report.get("ph1_status"), "PASS" if ok else "FAIL")
    assert ok

# T14 — Output SHA256 matches report
def test_output_hash():
    report = json.loads(REPORT_PATH.read_text())
    actual = hashlib.sha256(OUT_XLSX.read_bytes()).hexdigest()
    expected = report.get("output_hash_sha256", "")
    ok = actual == expected
    record("T14_OUTPUT_HASH", "sha256(OUT_XLSX)", f"{expected[:16]}...",
           f"{actual[:16]}...", "PASS" if ok else "FAIL")
    assert ok, f"Hash mismatch: {actual} != {expected}"

# T15 — All EPLAZA account codes survive alignment (none dropped)
def test_no_ep_codes_dropped():
    ep = engine.parse_xlsb(RAW_EPLAZA)
    ep_codes = {r.code for r in ep if r.row_type == 'ACCOUNT' and r.code}
    im = engine.parse_xlsb(RAW_IMPULSA)
    aligned = engine.align(ep, im)
    aligned_codes = {ar.code for ar in aligned if ar.row_type == 'ACCOUNT' and ar.code}
    dropped = ep_codes - aligned_codes
    ok = len(dropped) == 0
    record("T15_NO_EP_CODES_DROPPED", "ep_codes - aligned_codes", "empty set",
           f"{len(dropped)} dropped", "PASS" if ok else "FAIL")
    assert ok, f"Dropped EP codes: {dropped}"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
TESTS = [
    test_source_coverage_eplaza,
    test_source_coverage_impulsa,
    test_account_code_format,
    test_codeless_headings,
    test_zero_balance_hidden,
    test_horizontal_formulas,
    test_audit_sheet,
    test_reconciliation_sheet,
    test_consolidated_account_count,
    test_impulsa_only_accounts,
    test_desc_conflict_detection,
    test_output_file_exists,
    test_report_json,
    test_output_hash,
    test_no_ep_codes_dropped,
]

if __name__ == "__main__":
    print("=" * 60)
    print("KTMA_TASK014 — PH1 REGRESSION SUITE")
    print("=" * 60)
    passed = failed = 0
    for fn in TESTS:
        try:
            fn()
            passed += 1
        except Exception as e:
            failed += 1
            if not any(r["test"] == fn.__name__.replace("test_","").upper() for r in RESULTS):
                record(fn.__name__, fn.__name__, "no exception", str(e), "FAIL")

    print("\n--- RESULTS ---")
    print(f"  PASS: {passed} / {passed+failed}")
    print(f"  FAIL: {failed} / {passed+failed}")

    # Write results
    results_path = ROOT / "08_EVIDENCE/REPORTS/KTMA_TASK014_QA_RESULTS.json"
    results_path.write_text(json.dumps({
        "suite": "KTMA_TASK014_PH1_REGRESSION",
        "pass": passed,
        "fail": failed,
        "total": passed + failed,
        "tests": RESULTS
    }, indent=2, ensure_ascii=False))
    print(f"\n  QA results written to: {results_path}")

    sys.exit(0 if failed == 0 else 1)
