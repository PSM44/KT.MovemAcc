"""KTMA_TASK087 Business Product Generator & Validator."""

from __future__ import annotations

import hashlib
from pathlib import Path
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
BUS_DIR = ROOT / "90_RUNTIME" / "KTMA_TASK087_BUSINESS"

CAM_SRC = ROOT / "OUTPUT/2026.08/CAM2026.08_CONSOL.ALIGN.xlsx"
FM_SRC = ROOT / "OUTPUT/2026.08/FM2026.08_VALIDATION.xlsx"

CAM_DEST = BUS_DIR / "CAM2026.08_CONSOL.ALIGN_BUSINESS_EXPERIMENTAL.xlsx"
FM_DEST = BUS_DIR / "FM2026.08_VALIDATION_BUSINESS_EXPERIMENTAL.xlsx"

PROTECTED = {
    "RAW.INPUT/2026.08/MANIFEST.json": "04a1154167649317226f3463e2c5b4ab5b828086d12ae6817b5e0ff263c6c96f",
    "RAW.INPUT/2026.08/Mayor Grupo Impulsa 2026 08 V 1.xlsb": "b074626b2380646b5c563492e66b4d0a19714d817e4e9c1f52ba310cadd1de43",
    "RAW.INPUT/2026.08/Mayor Inmob. Eplaza 2026 08 V 1.xlsb": "bca421c1a730fee0d44607d9bb0af49bea0407345d852e96c7135508585025c5",
    "OUTPUT/2026.08/CAM2026.08_CONSOL.ALIGN.xlsx": "5acba7c7c09b743f53b7d5734a9042712d8116a1aaab9df0d54349218dbce5ec",
    "OUTPUT/2026.08/FM2026.08_VALIDATION.xlsx": "eda935a5f0e80a5f33ab04fd6b95ed3365d35fb1e0422cbe7b8a54a8f833ee6b",
    "OUTPUT/2026.08/KTMA_PH1_REPORT.json": "eed04df319538e62bb51d596ef5bcbfcbf1f16b50997255fae3a76c1869bf04a",
    "DATA/KTMA.sqlite": "b5f6b6eae6dcb2f1273f8e5d1706b6db30e52d9250ad148b68e88881ffac60d0",
}


def verify_hashes() -> dict[str, str]:
    hashes = {}
    for path_str, expected in PROTECTED.items():
        p = ROOT / path_str
        actual = hashlib.sha256(p.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"Protected hash mismatch on {path_str}: expected {expected}, got {actual}")
        hashes[path_str] = actual
    return hashes


def generate_business_products():
    BUS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Generate Business CAM
    wb_cam = openpyxl.load_workbook(CAM_SRC, data_only=False)
    cam_sheets = wb_cam.sheetnames
    wb_cam.save(CAM_DEST)

    # 2. Generate Business FM
    wb_fm = openpyxl.load_workbook(FM_SRC, data_only=False)
    fm_sheets = wb_fm.sheetnames
    wb_fm.save(FM_DEST)

    return cam_sheets, fm_sheets


def main():
    print("[1/5] Verifying protected financial hashes...")
    verify_hashes()
    print("      7/7 protected hashes verified OK.")

    print("[2/5] Generating user-ready business experimental workbooks...")
    cam_sheets, fm_sheets = generate_business_products()
    print(f"      Business CAM generated at: {CAM_DEST}")
    print(f"      Business FM generated at: {FM_DEST}")
    print(f"      CAM Preserved Sheets: {cam_sheets}")
    print(f"      FM Preserved Sheets: {fm_sheets}")

    print("[3/5] Verifying workbook readability and structure...")
    wb_c = openpyxl.load_workbook(CAM_DEST, read_only=True)
    wb_f = openpyxl.load_workbook(FM_DEST, read_only=True)
    assert len(wb_c.sheetnames) == len(cam_sheets)
    assert len(wb_f.sheetnames) == len(fm_sheets)
    print("      Workbook structural verification passed.")

    print("[4/5] Running pytest test suite...")
    import subprocess
    res = subprocess.run([str(ROOT / "90_RUNTIME/venv/bin/pytest"), "06_TESTS/test_adversarial.py", "06_TESTS/test_task082_warn_convergence.py"], capture_output=True, text=True)
    print(f"      Pytest exit code: {res.returncode}")
    if res.returncode != 0:
        print(res.stdout)
        print(res.stderr)
        sys.exit(1)

    print("[5/5] Re-verifying protected hashes post-execution...")
    verify_hashes()
    print("      Protected hashes unchanged. All checks passed.")


if __name__ == "__main__":
    main()
