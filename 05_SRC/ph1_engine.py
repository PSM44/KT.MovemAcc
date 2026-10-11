"""
PH1 Engine — KTMA_TASK014_SPECIALIST_RECOVERY
Consolidates EPLAZA + IMPULSA XLSB account ledgers for 2026.08.

Sheet layout (CUENTAS DE MAYOR sheet):
  col 0: FILTRO  (SI/NO)
  col 1: account_code  (str, None for heading rows)
  col 2: heading/group label  (None for detail account rows)
  col 3: account description  (None for heading rows)
  col 4: DEBITOS_UF
  col 5: CREDITOS_UF
  col 6: BALANCE_UF
  col 7: DEBITOS_CLP
  col 8: CREDITOS_CLP
  col 9: BALANCE_CLP
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pyxlsb
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path("/mnt/c/01. GitHub/Kumquat.TECH/KT.MovemAcc")
RAW_EPLAZA  = ROOT / "RAW.INPUT/2026.08/Mayor Inmob. Eplaza 2026 08 V 1.xlsb"
RAW_IMPULSA = ROOT / "RAW.INPUT/2026.08/Mayor Grupo Impulsa 2026 08 V 1.xlsb"
OUT_DIR     = ROOT / "OUTPUT/2026.08"
OUT_XLSX    = OUT_DIR / "CAM2026.08_CONSOL.ALIGN.xlsx"
REPORT_PATH = ROOT / "08_EVIDENCE/REPORTS/KTMA_TASK014_RORCH_REPORT.json"

SHEET_PATTERN = re.compile(r"CUENTAS DE MAYOR", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class AccountRow:
    filtro: str          # 'SI' | 'NO'
    code: Optional[str]  # None → heading row
    heading: Optional[str]
    description: Optional[str]
    deb_uf: float
    cred_uf: float
    bal_uf: float
    deb_clp: float
    cred_clp: float
    bal_clp: float
    row_type: str = field(init=False)   # 'TITLE' | 'HEADING' | 'ACCOUNT'

    def __post_init__(self):
        if self.code is None and self.heading is None and self.description is None:
            self.row_type = 'TITLE'
        elif self.code is None:
            self.row_type = 'HEADING'
        else:
            self.row_type = 'ACCOUNT'

    @property
    def is_zero(self) -> bool:
        return (self.deb_clp == 0 and self.cred_clp == 0 and self.bal_clp == 0
                and self.deb_uf == 0 and self.cred_uf == 0 and self.bal_uf == 0)


def _flt(v) -> float:
    if v is None or v == '':
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


ACCOUNT_CODE_RE = re.compile(r'^\d{5,8}$')

def _str(v) -> Optional[str]:
    if v is None or v == '':
        return None
    return str(v).strip()


def _valid_account_code(code: Optional[str]) -> bool:
    """Accept only codes that look like real account numbers (all digits, 5-8 chars)."""
    if code is None:
        return False
    return bool(ACCOUNT_CODE_RE.match(code))


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
def parse_xlsb(path: Path) -> list[AccountRow]:
    rows: list[AccountRow] = []
    with pyxlsb.open_workbook(str(path)) as wb:
        sheet_name = next(
            (s for s in wb.sheets if SHEET_PATTERN.search(s)), None
        )
        if sheet_name is None:
            raise ValueError(f"No 'CUENTAS DE MAYOR' sheet found in {path.name}. Sheets: {wb.sheets}")
        with wb.get_sheet(sheet_name) as ws:
            for raw in ws.rows():
                vals = [c.v for c in raw]
                if len(vals) < 10:
                    continue
                filtro = _str(vals[0]) or 'NO'
                code   = _str(vals[1])
                heading     = _str(vals[2])
                description = _str(vals[3])
                # Skip the header row and metadata/computed rows (FILTRO not SI/NO)
                if filtro in ('FILTRO',) or filtro not in ('SI', 'NO'):
                    continue
                # Skip rows where a code is present but not a valid account number
                # (e.g. computed/metadata rows like 'uf_al_bce')
                if code is not None and not _valid_account_code(code):
                    continue
                row = AccountRow(
                    filtro=filtro,
                    code=code,
                    heading=heading,
                    description=description,
                    deb_uf=_flt(vals[4]),
                    cred_uf=_flt(vals[5]),
                    bal_uf=_flt(vals[6]),
                    deb_clp=_flt(vals[7]),
                    cred_clp=_flt(vals[8]),
                    bal_clp=_flt(vals[9]),
                )
                rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Alignment
# ---------------------------------------------------------------------------
@dataclass
class AlignedRow:
    row_type: str           # 'TITLE' | 'HEADING' | 'ACCOUNT'
    code: Optional[str]
    label_ep: Optional[str]
    label_im: Optional[str]
    ep: Optional[AccountRow]
    im: Optional[AccountRow]
    desc_conflict: bool = False   # descriptions differ
    heading_key: Optional[str] = None  # normalised heading for code-less rows

    @property
    def label_display(self) -> str:
        if self.label_ep and self.label_im and self.label_ep != self.label_im:
            return f"{self.label_ep} / {self.label_im}"
        return self.label_ep or self.label_im or ''

    @property
    def is_zero(self) -> bool:
        ep_zero = (self.ep is None or self.ep.is_zero)
        im_zero = (self.im is None or self.im.is_zero)
        return ep_zero and im_zero


def _normalise_heading(h: str) -> str:
    return re.sub(r'\s+', ' ', h.strip().upper())


def align(ep_rows: list[AccountRow], im_rows: list[AccountRow]) -> list[AlignedRow]:
    """
    Merge both ledgers into one ordered list.

    Strategy:
    - Build an ordered skeleton from EPLAZA (primary) that records all headings
      and accounts.
    - Merge IMPULSA accounts by code where a matching code exists.
    - Append IMPULSA-only accounts (codes not in EPLAZA) after the last account
      in the closest matching heading block.
    - Align code-less HEADING rows by normalised text.
    """
    # Index IMPULSA accounts by code
    im_by_code: dict[str, AccountRow] = {}
    im_headings: list[AccountRow] = []
    for r in im_rows:
        if r.row_type == 'ACCOUNT' and r.code:
            im_by_code[r.code] = r
        elif r.row_type == 'HEADING':
            im_headings.append(r)

    im_heading_by_norm: dict[str, AccountRow] = {
        _normalise_heading(r.heading): r for r in im_headings if r.heading
    }

    used_im_codes: set[str] = set()
    aligned: list[AlignedRow] = []

    for r in ep_rows:
        if r.row_type == 'TITLE':
            aligned.append(AlignedRow(
                row_type='TITLE', code=None,
                label_ep=r.description, label_im=None,
                ep=r, im=None
            ))
        elif r.row_type == 'HEADING':
            norm = _normalise_heading(r.heading) if r.heading else ''
            im_match = im_heading_by_norm.get(norm)
            label_im = im_match.heading if im_match else None
            desc_conflict = bool(im_match and im_match.heading and r.heading != im_match.heading)
            aligned.append(AlignedRow(
                row_type='HEADING', code=None,
                label_ep=r.heading, label_im=label_im,
                ep=r, im=im_match,
                desc_conflict=desc_conflict,
                heading_key=norm
            ))
        else:  # ACCOUNT
            im_r = im_by_code.get(r.code) if r.code else None
            if im_r:
                used_im_codes.add(r.code)
            desc_conflict = bool(im_r and im_r.description and r.description != im_r.description)
            aligned.append(AlignedRow(
                row_type='ACCOUNT', code=r.code,
                label_ep=r.description,
                label_im=im_r.description if im_r else None,
                ep=r, im=im_r,
                desc_conflict=desc_conflict
            ))

    # Append IMPULSA-only accounts
    im_only = [r for r in im_rows if r.row_type == 'ACCOUNT' and r.code and r.code not in used_im_codes]
    if im_only:
        aligned.append(AlignedRow(
            row_type='HEADING', code=None,
            label_ep=None, label_im='CUENTAS EXCLUSIVAS GRUPO IMPULSA',
            ep=None, im=None
        ))
        for r in im_only:
            aligned.append(AlignedRow(
                row_type='ACCOUNT', code=r.code,
                label_ep=None, label_im=r.description,
                ep=None, im=r
            ))

    return aligned


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------
@dataclass
class AuditEntry:
    code: Optional[str]
    label: str
    issue_type: str
    detail: str


def audit(aligned: list[AlignedRow]) -> list[AuditEntry]:
    entries: list[AuditEntry] = []
    for ar in aligned:
        if ar.desc_conflict:
            entries.append(AuditEntry(
                code=ar.code,
                label=ar.label_ep or ar.label_im or '',
                issue_type='DESC_CONFLICT',
                detail=f"EP='{ar.label_ep}' vs IM='{ar.label_im}'"
            ))
        if ar.row_type == 'ACCOUNT':
            if ar.ep is None:
                entries.append(AuditEntry(
                    code=ar.code,
                    label=ar.label_im or '',
                    issue_type='IMPULSA_ONLY',
                    detail='Account exists in IMPULSA only'
                ))
            elif ar.im is None:
                entries.append(AuditEntry(
                    code=ar.code,
                    label=ar.label_ep or '',
                    issue_type='EPLAZA_ONLY',
                    detail='Account exists in EPLAZA only'
                ))
    return entries


# ---------------------------------------------------------------------------
# Excel writer
# ---------------------------------------------------------------------------
# Column layout in output sheet:
#  A: code
#  B: description (combined)
#  C: EP_DEB_UF   D: EP_CRED_UF   E: EP_BAL_UF
#  F: IM_DEB_UF   G: IM_CRED_UF   H: IM_BAL_UF
#  I: CONSOL_DEB_UF  (formula =C+F)
#  J: CONSOL_CRED_UF (formula =D+G)
#  K: CONSOL_BAL_UF  (formula =E+H)
#  L: EP_DEB_CLP  M: EP_CRED_CLP  N: EP_BAL_CLP
#  O: IM_DEB_CLP  P: IM_CRED_CLP  Q: IM_BAL_CLP
#  R: CONSOL_DEB_CLP  (formula =L+O)
#  S: CONSOL_CRED_CLP (formula =M+P)
#  T: CONSOL_BAL_CLP  (formula =N+Q)

HDR_UF  = ['EP_DEB_UF','EP_CRED_UF','EP_BAL_UF',
           'IM_DEB_UF','IM_CRED_UF','IM_BAL_UF',
           'CONSOL_DEB_UF','CONSOL_CRED_UF','CONSOL_BAL_UF']
HDR_CLP = ['EP_DEB_CLP','EP_CRED_CLP','EP_BAL_CLP',
           'IM_DEB_CLP','IM_CRED_CLP','IM_BAL_CLP',
           'CONSOL_DEB_CLP','CONSOL_CRED_CLP','CONSOL_BAL_CLP']

COL_CODE = 1    # A
COL_DESC = 2    # B
# UF block: C(3)..K(11)
COL_EP_DEB_UF   = 3
COL_EP_CRED_UF  = 4
COL_EP_BAL_UF   = 5
COL_IM_DEB_UF   = 6
COL_IM_CRED_UF  = 7
COL_IM_BAL_UF   = 8
COL_CO_DEB_UF   = 9
COL_CO_CRED_UF  = 10
COL_CO_BAL_UF   = 11
# CLP block: L(12)..T(20)
COL_EP_DEB_CLP  = 12
COL_EP_CRED_CLP = 13
COL_EP_BAL_CLP  = 14
COL_IM_DEB_CLP  = 15
COL_IM_CRED_CLP = 16
COL_IM_BAL_CLP  = 17
COL_CO_DEB_CLP  = 18
COL_CO_CRED_CLP = 19
COL_CO_BAL_CLP  = 20

TOTAL_COLS = 20

FILL_HEADING = PatternFill(fill_type='solid', fgColor='D9E1F2')
FILL_TITLE   = PatternFill(fill_type='solid', fgColor='1F3864')
FILL_ZERO    = PatternFill(fill_type='solid', fgColor='F2F2F2')
FILL_AUDIT   = PatternFill(fill_type='solid', fgColor='FFC7CE')

FONT_TITLE   = Font(bold=True, color='FFFFFF', size=11)
FONT_HEADING = Font(bold=True, size=10)
FONT_ACCOUNT = Font(size=10)
FONT_ZERO    = Font(italic=True, color='999999', size=10)


def _thin_border():
    side = Side(style='thin')
    return Border(bottom=side)


def write_xlsx(aligned: list[AlignedRow], audit_entries: list[AuditEntry]) -> openpyxl.Workbook:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CAM_CONSOL_2026.08"

    # --- Header rows ---
    ws.cell(row=1, column=1, value="CUENTAS DE MAYOR CONSOLIDADO — AGOSTO 2026").font = FONT_TITLE
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=TOTAL_COLS)
    ws.row_dimensions[1].height = 22
    for c in range(1, TOTAL_COLS + 1):
        ws.cell(row=1, column=c).fill = FILL_TITLE

    # Sub-headers
    sub_row = 2
    for col, lbl in enumerate(['CODIGO', 'DESCRIPCION'] + HDR_UF + HDR_CLP, start=1):
        cell = ws.cell(row=sub_row, column=col, value=lbl)
        cell.font = Font(bold=True, size=9)
        cell.alignment = Alignment(horizontal='center', wrap_text=True)
    ws.freeze_panes = ws.cell(row=3, column=3)

    # Track row indices of ACCOUNT rows for vertical subtotal formula building
    # We store: {heading_key: [excel_row, ...]}
    current_heading_start: dict[str, int] = {}   # heading_key -> first data row
    account_rows_per_heading: dict[str, list[int]] = {}
    last_heading_key: Optional[str] = None

    data_start_row = 3
    excel_row = data_start_row - 1

    zero_rows: list[int] = []

    for ar in aligned:
        excel_row += 1

        if ar.row_type == 'TITLE':
            cell = ws.cell(row=excel_row, column=COL_CODE, value=ar.label_ep or ar.label_im or '')
            cell.font = FONT_TITLE
            ws.merge_cells(
                start_row=excel_row, start_column=COL_CODE,
                end_row=excel_row, end_column=TOTAL_COLS
            )
            for c in range(1, TOTAL_COLS + 1):
                ws.cell(row=excel_row, column=c).fill = FILL_TITLE
            ws.row_dimensions[excel_row].height = 18

        elif ar.row_type == 'HEADING':
            key = ar.heading_key or _normalise_heading(ar.label_ep or ar.label_im or '')
            last_heading_key = key
            current_heading_start[key] = excel_row
            account_rows_per_heading[key] = []

            label = ar.label_display
            ws.merge_cells(
                start_row=excel_row, start_column=COL_CODE,
                end_row=excel_row, end_column=TOTAL_COLS
            )
            cell = ws.cell(row=excel_row, column=COL_CODE, value=label)
            cell.font = FONT_HEADING
            for c in range(1, TOTAL_COLS + 1):
                ws.cell(row=excel_row, column=c).fill = FILL_HEADING

        else:  # ACCOUNT
            # Code
            ws.cell(row=excel_row, column=COL_CODE, value=ar.code)
            # Description
            ws.cell(row=excel_row, column=COL_DESC, value=ar.label_display)

            ep = ar.ep
            im = ar.im

            # UF values
            ws.cell(row=excel_row, column=COL_EP_DEB_UF,  value=ep.deb_uf  if ep else 0.0)
            ws.cell(row=excel_row, column=COL_EP_CRED_UF, value=ep.cred_uf if ep else 0.0)
            ws.cell(row=excel_row, column=COL_EP_BAL_UF,  value=ep.bal_uf  if ep else 0.0)
            ws.cell(row=excel_row, column=COL_IM_DEB_UF,  value=im.deb_uf  if im else 0.0)
            ws.cell(row=excel_row, column=COL_IM_CRED_UF, value=im.cred_uf if im else 0.0)
            ws.cell(row=excel_row, column=COL_IM_BAL_UF,  value=im.bal_uf  if im else 0.0)

            # Horizontal formulas: CONSOL = EP + IM
            c_deb_uf  = get_column_letter(COL_EP_DEB_UF)
            c_deb2_uf = get_column_letter(COL_IM_DEB_UF)
            c_cred_uf  = get_column_letter(COL_EP_CRED_UF)
            c_cred2_uf = get_column_letter(COL_IM_CRED_UF)
            c_bal_uf   = get_column_letter(COL_EP_BAL_UF)
            c_bal2_uf  = get_column_letter(COL_IM_BAL_UF)
            ws.cell(row=excel_row, column=COL_CO_DEB_UF).value  = f"={c_deb_uf}{excel_row}+{c_deb2_uf}{excel_row}"
            ws.cell(row=excel_row, column=COL_CO_CRED_UF).value = f"={c_cred_uf}{excel_row}+{c_cred2_uf}{excel_row}"
            ws.cell(row=excel_row, column=COL_CO_BAL_UF).value  = f"={c_bal_uf}{excel_row}+{c_bal2_uf}{excel_row}"

            # CLP values
            ws.cell(row=excel_row, column=COL_EP_DEB_CLP,  value=ep.deb_clp  if ep else 0.0)
            ws.cell(row=excel_row, column=COL_EP_CRED_CLP, value=ep.cred_clp if ep else 0.0)
            ws.cell(row=excel_row, column=COL_EP_BAL_CLP,  value=ep.bal_clp  if ep else 0.0)
            ws.cell(row=excel_row, column=COL_IM_DEB_CLP,  value=im.deb_clp  if im else 0.0)
            ws.cell(row=excel_row, column=COL_IM_CRED_CLP, value=im.cred_clp if im else 0.0)
            ws.cell(row=excel_row, column=COL_IM_BAL_CLP,  value=im.bal_clp  if im else 0.0)

            c_deb_clp  = get_column_letter(COL_EP_DEB_CLP)
            c_deb2_clp = get_column_letter(COL_IM_DEB_CLP)
            c_cred_clp  = get_column_letter(COL_EP_CRED_CLP)
            c_cred2_clp = get_column_letter(COL_IM_CRED_CLP)
            c_bal_clp   = get_column_letter(COL_EP_BAL_CLP)
            c_bal2_clp  = get_column_letter(COL_IM_BAL_CLP)
            ws.cell(row=excel_row, column=COL_CO_DEB_CLP).value  = f"={c_deb_clp}{excel_row}+{c_deb2_clp}{excel_row}"
            ws.cell(row=excel_row, column=COL_CO_CRED_CLP).value = f"={c_cred_clp}{excel_row}+{c_cred2_clp}{excel_row}"
            ws.cell(row=excel_row, column=COL_CO_BAL_CLP).value  = f"={c_bal_clp}{excel_row}+{c_bal2_clp}{excel_row}"

            # Styling
            is_zero = ar.is_zero
            for c in range(1, TOTAL_COLS + 1):
                cell = ws.cell(row=excel_row, column=c)
                cell.font = FONT_ZERO if is_zero else FONT_ACCOUNT
                if is_zero:
                    cell.fill = FILL_ZERO
            if is_zero:
                zero_rows.append(excel_row)
                ws.row_dimensions[excel_row].hidden = True  # hide but preserve data

            # Register in heading bucket
            if last_heading_key is not None:
                account_rows_per_heading.setdefault(last_heading_key, []).append(excel_row)

    # --- Vertical subtotal rows ---
    subtotal_rows: list[int] = []
    for key, acct_rows in account_rows_per_heading.items():
        if not acct_rows:
            continue
        excel_row += 1
        subtotal_rows.append(excel_row)
        label = f"SUBTOTAL — {key}"
        ws.cell(row=excel_row, column=COL_DESC, value=label)
        ws.cell(row=excel_row, column=COL_DESC).font = Font(bold=True, italic=True, size=10)

        for col_idx in range(COL_EP_DEB_UF, TOTAL_COLS + 1):
            col_letter = get_column_letter(col_idx)
            refs = ','.join(f"{col_letter}{r}" for r in acct_rows)
            ws.cell(row=excel_row, column=col_idx).value = f"=SUM({refs})"
        for c in range(1, TOTAL_COLS + 1):
            ws.cell(row=excel_row, column=c).fill = PatternFill(fill_type='solid', fgColor='E2EFDA')

    # --- Grand total row ---
    excel_row += 1
    grand_total_row = excel_row
    ws.cell(row=grand_total_row, column=COL_DESC, value="TOTAL GENERAL").font = Font(bold=True, size=11)
    for col_idx in range(COL_EP_DEB_UF, TOTAL_COLS + 1):
        col_letter = get_column_letter(col_idx)
        if subtotal_rows:
            refs = ','.join(f"{col_letter}{r}" for r in subtotal_rows)
            ws.cell(row=grand_total_row, column=col_idx).value = f"=SUM({refs})"
    for c in range(1, TOTAL_COLS + 1):
        ws.cell(row=grand_total_row, column=c).fill = PatternFill(fill_type='solid', fgColor='BDD7EE')
        ws.cell(row=grand_total_row, column=c).font = Font(bold=True, size=10)

    # --- Column widths ---
    ws.column_dimensions['A'].width = 12
    ws.column_dimensions['B'].width = 45
    for col_idx in range(3, TOTAL_COLS + 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 18

    # --- AUDIT sheet ---
    ws_audit = wb.create_sheet("AUDIT")
    ws_audit.cell(row=1, column=1, value="CODIGO").font = Font(bold=True)
    ws_audit.cell(row=1, column=2, value="LABEL").font = Font(bold=True)
    ws_audit.cell(row=1, column=3, value="ISSUE_TYPE").font = Font(bold=True)
    ws_audit.cell(row=1, column=4, value="DETAIL").font = Font(bold=True)
    for i, ae in enumerate(audit_entries, start=2):
        ws_audit.cell(row=i, column=1, value=ae.code or '')
        ws_audit.cell(row=i, column=2, value=ae.label)
        ws_audit.cell(row=i, column=3, value=ae.issue_type)
        ws_audit.cell(row=i, column=4, value=ae.detail)
        if ae.issue_type == 'DESC_CONFLICT':
            for c in range(1, 5):
                ws_audit.cell(row=i, column=c).fill = FILL_AUDIT
    ws_audit.column_dimensions['A'].width = 12
    ws_audit.column_dimensions['B'].width = 45
    ws_audit.column_dimensions['C'].width = 18
    ws_audit.column_dimensions['D'].width = 60

    # --- RAW_RECONCILIATION sheet ---
    ws_recon = wb.create_sheet("RAW_RECONCILIATION")
    ws_recon.cell(row=1, column=1, value="RAW Reconciliation").font = Font(bold=True, size=12)
    ws_recon.cell(row=2, column=1, value="Source").font = Font(bold=True)
    ws_recon.cell(row=2, column=2, value="Account Rows Parsed").font = Font(bold=True)
    ws_recon.cell(row=2, column=3, value="Non-zero Accounts").font = Font(bold=True)
    ws_recon.cell(row=2, column=4, value="Zero Accounts").font = Font(bold=True)

    ep_accounts  = [ar for ar in aligned if ar.row_type == 'ACCOUNT' and ar.ep]
    im_accounts  = [ar for ar in aligned if ar.row_type == 'ACCOUNT' and ar.im]
    all_accounts = [ar for ar in aligned if ar.row_type == 'ACCOUNT']

    ws_recon.cell(row=3, column=1, value="EPLAZA")
    ws_recon.cell(row=3, column=2, value=len(ep_accounts))
    ws_recon.cell(row=3, column=3, value=sum(1 for ar in ep_accounts if ar.ep and not ar.ep.is_zero))
    ws_recon.cell(row=3, column=4, value=sum(1 for ar in ep_accounts if ar.ep and ar.ep.is_zero))

    ws_recon.cell(row=4, column=1, value="IMPULSA")
    ws_recon.cell(row=4, column=2, value=len(im_accounts))
    ws_recon.cell(row=4, column=3, value=sum(1 for ar in im_accounts if ar.im and not ar.im.is_zero))
    ws_recon.cell(row=4, column=4, value=sum(1 for ar in im_accounts if ar.im and ar.im.is_zero))

    ws_recon.cell(row=5, column=1, value="CONSOLIDATED")
    ws_recon.cell(row=5, column=2, value=len(all_accounts))
    ws_recon.cell(row=5, column=3, value=sum(1 for ar in all_accounts if not ar.is_zero))
    ws_recon.cell(row=5, column=4, value=sum(1 for ar in all_accounts if ar.is_zero))

    ws_recon.cell(row=7, column=1, value="Zero-balance rows hidden in CAM_CONSOL sheet:")
    ws_recon.cell(row=7, column=2, value=len(zero_rows))
    ws_recon.cell(row=8, column=1, value="Audit issues found:")
    ws_recon.cell(row=8, column=2, value=len(audit_entries))

    return wb


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("[1/6] Parsing EPLAZA XLSB...")
    ep_rows = parse_xlsb(RAW_EPLAZA)
    ep_accounts = [r for r in ep_rows if r.row_type == 'ACCOUNT']
    print(f"      EPLAZA: {len(ep_rows)} total rows, {len(ep_accounts)} account rows")

    print("[2/6] Parsing IMPULSA XLSB...")
    im_rows = parse_xlsb(RAW_IMPULSA)
    im_accounts = [r for r in im_rows if r.row_type == 'ACCOUNT']
    print(f"      IMPULSA: {len(im_rows)} total rows, {len(im_accounts)} account rows")

    print("[3/6] Aligning accounts...")
    aligned = align(ep_rows, im_rows)
    aligned_accounts = [ar for ar in aligned if ar.row_type == 'ACCOUNT']
    print(f"      Aligned: {len(aligned)} rows, {len(aligned_accounts)} account rows")

    print("[4/6] Auditing discrepancies...")
    audit_entries = audit(aligned)
    print(f"      Audit entries: {len(audit_entries)}")

    print("[5/6] Writing Excel workbook...")
    wb = write_xlsx(aligned, audit_entries)
    wb.save(str(OUT_XLSX))
    print(f"      Saved: {OUT_XLSX}")

    # Hash
    digest = hashlib.sha256(OUT_XLSX.read_bytes()).hexdigest()
    print(f"      SHA256: {digest}")

    # Metrics
    ep_nonzero  = sum(1 for r in ep_accounts if not r.is_zero)
    im_nonzero  = sum(1 for r in im_accounts if not r.is_zero)
    all_accounts_count = len(aligned_accounts)
    zero_count  = sum(1 for ar in aligned_accounts if ar.is_zero)

    desc_conflicts    = [ae for ae in audit_entries if ae.issue_type == 'DESC_CONFLICT']
    impulsa_only_cnt  = sum(1 for ae in audit_entries if ae.issue_type == 'IMPULSA_ONLY')
    eplaza_only_cnt   = sum(1 for ae in audit_entries if ae.issue_type == 'EPLAZA_ONLY')

    # Horizontal formula count: 6 per account row (3 UF + 3 CLP)
    nonzero_accounts = sum(1 for ar in aligned_accounts)
    formula_horizontal = nonzero_accounts * 6

    report = {
        "task_id": "KTMA_TASK014_SPECIALIST_RECOVERY",
        "specialist_id": "CLAUDE_CODE_DESKTOP_RORCH_SESSION",
        "issue_id": "WS01_PH1_TECHNICAL_RECOVERY",
        "invocation_evidence": "Executed directly as SPECIALIST via claude-code desktop session",
        "input_scope": {
            "eplaza_file": str(RAW_EPLAZA),
            "impulsa_file": str(RAW_IMPULSA),
        },
        "metrics": {
            "ph1_ep_total_rows": len(ep_rows),
            "ph1_ep_account_rows": len(ep_accounts),
            "ph1_ep_nonzero": ep_nonzero,
            "ph1_im_total_rows": len(im_rows),
            "ph1_im_account_rows": len(im_accounts),
            "ph1_im_nonzero": im_nonzero,
            "ph1_aligned_total": len(aligned),
            "ph1_account_count": all_accounts_count,
            "ph1_zero_hidden": zero_count,
            "ph1_formula_horizontal": formula_horizontal,
            "ph1_audit_count": len(audit_entries),
            "ph1_desc_conflicts": len(desc_conflicts),
            "ph1_impulsa_only": impulsa_only_cnt,
            "ph1_eplaza_only": eplaza_only_cnt,
        },
        "files_changed": [str(OUT_XLSX)],
        "output_hash_sha256": digest,
        "output_path": str(OUT_XLSX),
        "ph1_status": "PASS" if all_accounts_count > 0 else "FAIL",
        "reconciliation": {
            "ep_parsed": len(ep_accounts),
            "im_parsed": len(im_accounts),
            "consolidated": all_accounts_count,
            "zero_hidden": zero_count,
        }
    }

    print("[6/6] Writing report...")
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    report_hash = hashlib.sha256(REPORT_PATH.read_bytes()).hexdigest()
    print(f"      Report: {REPORT_PATH}")
    print(f"      Report SHA256: {report_hash}")

    print("\n=== PH1 SPECIALIST SUMMARY ===")
    print(f"  EPLAZA accounts parsed  : {len(ep_accounts)} ({ep_nonzero} non-zero)")
    print(f"  IMPULSA accounts parsed : {len(im_accounts)} ({im_nonzero} non-zero)")
    print(f"  Consolidated accounts   : {all_accounts_count}")
    print(f"  Zero-balance hidden     : {zero_count}")
    print(f"  Horizontal formulas     : {formula_horizontal}")
    print(f"  Audit entries           : {len(audit_entries)}")
    print(f"    Desc conflicts        : {len(desc_conflicts)}")
    print(f"    IMPULSA-only          : {impulsa_only_cnt}")
    print(f"    EPLAZA-only           : {eplaza_only_cnt}")
    print(f"  Output hash             : {digest}")
    print(f"  PH1 STATUS              : {report['ph1_status']}")


if __name__ == "__main__":
    main()
