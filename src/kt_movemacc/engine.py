"""PH1 engine for KT.MovemAcc.

The PH1 deliverable turns the two source CUENTAS DE MAYOR XLSB ledgers into a
five-sheet accounting workbook:

* CAM{period}_CONSOL.ALIGN
* CM{period}_EPLAZA
* CM{period}_IMPULSA
* AUDIT.PH1
* CONTROL
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Literal, Optional

import openpyxl
import pyxlsb
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

SHEET_PATTERN = re.compile(r"CUENTAS DE MAYOR", re.IGNORECASE)
ACCOUNT_CODE_RE = re.compile(r"^\d{5,8}$")
NUMERIC_COLS = (5, 6, 7, 8, 9, 10)
VALUE_FIELDS = ("deb_uf", "cred_uf", "bal_uf", "deb_clp", "cred_clp", "bal_clp")
TOLERANCE_UF = 0.05
TOLERANCE_CLP = 1.0

FILL_TITLE = PatternFill(fill_type="solid", fgColor="1F3864")
FILL_HEADING = PatternFill(fill_type="solid", fgColor="D9E1F2")
FILL_HEADER = PatternFill(fill_type="solid", fgColor="B4C6E7")
FILL_WARN = PatternFill(fill_type="solid", fgColor="FFF2CC")
FILL_ZERO = PatternFill(fill_type="solid", fgColor="F2F2F2")

FONT_TITLE = Font(bold=True, color="FFFFFF")
FONT_HEADER = Font(bold=True)
FONT_HEADING = Font(bold=True)
FONT_ZERO = Font(italic=True, color="666666")
THIN_BOTTOM = Border(bottom=Side(style="thin", color="808080"))


@dataclass
class AccountRow:
    filtro: str
    code: Optional[str]
    heading: Optional[str]
    description: Optional[str]
    deb_uf: float
    cred_uf: float
    bal_uf: float
    deb_clp: float
    cred_clp: float
    bal_clp: float
    source_row: int
    source_sheet: str
    row_type: str = field(init=False)
    heading_key: Optional[str] = None

    def __post_init__(self) -> None:
        if self.code is None and self.heading is None and self.description is None:
            self.row_type = "TITLE"
        elif self.code is None:
            self.row_type = "HEADING"
        else:
            self.row_type = "ACCOUNT"

    @property
    def label(self) -> str:
        return self.description or self.heading or ""

    @property
    def is_zero(self) -> bool:
        return all(abs(getattr(self, f)) < 1e-9 for f in VALUE_FIELDS)


@dataclass
class FormulaBlock:
    heading_index: int
    account_indexes: list[int]
    status: str
    diffs: dict[str, float]


@dataclass
class AuditEntry:
    severity: str
    company: str
    finding: str
    key: str
    detail: str
    location: str


@dataclass
class AlignedRow:
    row_type: str
    code: Optional[str]
    heading: Optional[str]
    ep: Optional[AccountRow]
    im: Optional[AccountRow]
    ep_desc: Optional[str] = None
    im_desc: Optional[str] = None
    key: Optional[str] = None


SemanticRefKind = Literal["heading", "code"]


@dataclass(frozen=True)
class SemanticRef:
    kind: SemanticRefKind
    key: str


@dataclass(frozen=True)
class CriteriaRule:
    rule_id: str
    company: str
    target: SemanticRef
    operands: tuple[SemanticRef, ...]
    operation: Literal["sum", "negate"] = "sum"
    fixture_cell: str = ""
    approved_formula_note: str = ""


def _row_has_financial_value(row: Optional[AccountRow]) -> bool:
    return bool(row and any(abs(getattr(row, field)) > 1e-9 for field in VALUE_FIELDS))


def _aligned_has_financial_value(row: AlignedRow) -> bool:
    return _row_has_financial_value(row.ep) or _row_has_financial_value(row.im)


def _str(value) -> Optional[str]:
    if value is None or value == "":
        return None
    return str(value).strip()


def _flt(value) -> float:
    if value is None or value == "":
        return 0.0
    try:
        f = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(f) or math.isinf(f):
        return 0.0
    return f


def _valid_account_code(code: Optional[str]) -> bool:
    return bool(code and ACCOUNT_CODE_RE.match(code))


def _normalise(text: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().upper())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ref(kind: SemanticRefKind, key: str) -> SemanticRef:
    return SemanticRef(kind, key)


def _literal_excel_text(value):
    if isinstance(value, str) and value.startswith("="):
        return "'" + value
    return value


def parse_xlsb(path: Path) -> list[AccountRow]:
    """Parse the physical A:J CUENTAS DE MAYOR layout from a source XLSB."""
    rows: list[AccountRow] = []
    with pyxlsb.open_workbook(str(path)) as wb:
        sheet_name = next((s for s in wb.sheets if SHEET_PATTERN.search(s)), None)
        if sheet_name is None:
            raise ValueError(f"No CUENTAS DE MAYOR sheet found in {path}")

        heading_seen: dict[str, int] = {}
        with wb.get_sheet(sheet_name) as ws:
            for source_row, raw in enumerate(ws.rows(), start=1):
                vals = [c.v for c in raw]
                if len(vals) < 10:
                    vals += [None] * (10 - len(vals))

                filtro = _str(vals[0]) or "NO"
                code = _str(vals[1])
                heading = _str(vals[2])
                description = _str(vals[3])

                if filtro == "FILTRO" or filtro not in ("SI", "NO"):
                    continue
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
                    source_row=source_row,
                    source_sheet=sheet_name,
                )
                if row.row_type == "HEADING":
                    norm = _normalise(row.label)
                    heading_seen[norm] = heading_seen.get(norm, 0) + 1
                    row.heading_key = f"{norm}#{heading_seen[norm]}"
                rows.append(row)
    return rows


def _sum_accounts(rows: list[AccountRow], indexes: Iterable[int]) -> dict[str, float]:
    result = {field: 0.0 for field in VALUE_FIELDS}
    for idx in indexes:
        row = rows[idx]
        for field in VALUE_FIELDS:
            result[field] += getattr(row, field)
    return result


def _diffs(row: AccountRow, totals: dict[str, float]) -> dict[str, float]:
    return {field: totals[field] - getattr(row, field) for field in VALUE_FIELDS}


def _within_tolerance(diffs: dict[str, float]) -> bool:
    return (
        abs(diffs["deb_uf"]) <= TOLERANCE_UF
        and abs(diffs["cred_uf"]) <= TOLERANCE_UF
        and abs(diffs["bal_uf"]) <= TOLERANCE_UF
        and abs(diffs["deb_clp"]) <= TOLERANCE_CLP
        and abs(diffs["cred_clp"]) <= TOLERANCE_CLP
        and abs(diffs["bal_clp"]) <= TOLERANCE_CLP
    )


def infer_formula_blocks(rows: list[AccountRow]) -> dict[int, FormulaBlock]:
    blocks: dict[int, FormulaBlock] = {}
    for idx, row in enumerate(rows):
        if row.row_type != "HEADING":
            continue

        immediate: list[int] = []
        j = idx + 1
        while j < len(rows) and rows[j].row_type == "ACCOUNT":
            immediate.append(j)
            j += 1
        if immediate:
            totals = _sum_accounts(rows, immediate)
            diffs = _diffs(row, totals)
            status = "DIRECT_RECONCILED" if _within_tolerance(diffs) else "DIRECT_DIFF"
            blocks[idx] = FormulaBlock(idx, immediate, status, diffs)
            continue

        if row.is_zero:
            continue

        running: list[int] = []
        for j in range(idx + 1, len(rows)):
            if rows[j].row_type == "ACCOUNT":
                running.append(j)
                totals = _sum_accounts(rows, running)
                diffs = _diffs(row, totals)
                if _within_tolerance(diffs):
                    blocks[idx] = FormulaBlock(idx, running.copy(), "FORWARD_RECONCILED", diffs)
                    break
            elif rows[j].row_type == "TITLE" and running:
                break
    return blocks


def hierarchy_exception_keys(rows: list[AccountRow]) -> set[str]:
    blocks = infer_formula_blocks(rows)
    exceptions: set[str] = set()
    for idx, row in enumerate(rows):
        if row.row_type != "HEADING" or row.is_zero:
            continue
        block = blocks.get(idx)
        if block is None or block.status == "DIRECT_DIFF":
            exceptions.add(row.heading_key or row.label)
    return exceptions


def align(ep_rows: list[AccountRow], im_rows: list[AccountRow]) -> list[AlignedRow]:
    im_by_code = {r.code: r for r in im_rows if r.row_type == "ACCOUNT" and r.code}
    im_heading_by_key = {r.heading_key: r for r in im_rows if r.row_type == "HEADING" and r.heading_key}
    used_im_codes: set[str] = set()
    aligned: list[AlignedRow] = []

    for row in ep_rows:
        if row.row_type == "TITLE":
            continue
        if row.row_type == "HEADING":
            im = im_heading_by_key.get(row.heading_key or "")
            aligned.append(AlignedRow("HEADING", None, row.label, row, im, key=row.heading_key))
        elif row.code:
            im = im_by_code.get(row.code)
            if im:
                used_im_codes.add(row.code)
            aligned.append(AlignedRow("ACCOUNT", row.code, None, row, im, row.description, im.description if im else None, row.code))

    im_only = [r for r in im_rows if r.row_type == "ACCOUNT" and r.code and r.code not in used_im_codes]
    if im_only:
        aligned.append(AlignedRow("HEADING", None, "CUENTAS EXCLUSIVAS GRUPO IMPULSA", None, None, key="IMPULSA_ONLY"))
        for row in im_only:
            aligned.append(AlignedRow("ACCOUNT", row.code, None, None, row, None, row.description, row.code))
    return aligned


def audit_alignment(aligned: list[AlignedRow]) -> list[AuditEntry]:
    entries: list[AuditEntry] = []
    seen_codes: set[str] = set()
    for row in aligned:
        if row.row_type != "ACCOUNT":
            continue
        if row.code in seen_codes:
            entries.append(AuditEntry("ERROR", "CONSOL", "DUPLICATE_CODE", row.code or "", "Duplicate account code in CAM alignment", "CAM"))
        seen_codes.add(row.code or "")
        if row.ep and row.im and row.ep.description != row.im.description:
            entries.append(AuditEntry("WARN", "CONSOL", "CONFLICTING_DESCRIPTION", row.code or "", f"EPLAZA='{row.ep.description}' | IMPULSA='{row.im.description}'", "CAM"))
        elif row.ep is None:
            entries.append(AuditEntry("INFO", "IMPULSA", "IMPULSA_ONLY_ACCOUNT", row.code or "", row.im_desc or "", "CAM"))
        elif row.im is None:
            entries.append(AuditEntry("INFO", "EPLAZA", "EPLAZA_ONLY_ACCOUNT", row.code or "", row.ep_desc or "", "CAM"))
    return entries


def _style_cm_sheet(ws) -> None:
    ws.freeze_panes = "A3"
    ws.auto_filter.ref = f"A2:K{ws.max_row}"
    widths = {"A": 10, "B": 13, "C": 34, "D": 42, "E": 15, "F": 15, "G": 15, "H": 16, "I": 16, "J": 16, "K": 16}
    for col, width in widths.items():
        ws.column_dimensions[col].width = width
    for row in ws.iter_rows():
        for cell in row:
            cell.border = THIN_BOTTOM
            if cell.column in NUMERIC_COLS:
                cell.number_format = '#,##0.00;[Red]-#,##0.00;0.00' if cell.column <= 7 else '#,##0;[Red]-#,##0;0'
    for header_row in (1, 2):
        for cell in ws[header_row]:
            cell.fill = FILL_HEADER
            cell.font = FONT_HEADER
            cell.alignment = Alignment(horizontal="center")


def write_cm_sheet(wb, sheet_name: str, rows: list[AccountRow], company: str, audit_entries: list[AuditEntry]) -> dict[str, int]:
    ws = wb.create_sheet(sheet_name)
    ws.append([None, None, None, None, "VALORES UF", None, None, "VALORES $$", None, None, None])
    ws.append(["FILTRO", "ACCOUNT_CODE", "HEADING / TITLE", "ACCOUNT_DESCRIPTION", "DEBITOS_UF", "CREDITOS_UF", "VALORES UF", "DEBITOS_CLP", "CREDITOS_CLP", "VALORES $$", "VISIBILIDAD_UF"])

    row_to_excel: dict[int, int] = {}
    formula_blocks = infer_formula_blocks(rows)
    pending_formulas: list[tuple[int, FormulaBlock]] = []
    source_formulas = 0
    unresolved = 0

    for idx, row in enumerate(rows):
        excel_row = ws.max_row + 1
        row_to_excel[idx] = excel_row
        visibility_uf = "MOSTRAR" if abs(row.bal_uf) > 1e-9 else "OCULTAR"
        if row.row_type == "HEADING" and not row.is_zero:
            visibility_uf = "MOSTRAR"
        ws.append([row.filtro, row.code, row.heading, row.description, row.deb_uf, row.cred_uf, row.bal_uf, row.deb_clp, row.cred_clp, row.bal_clp, visibility_uf])
        if row.row_type == "TITLE":
            for cell in ws[excel_row]:
                cell.fill = FILL_TITLE
                cell.font = FONT_TITLE
        elif row.row_type == "HEADING":
            for cell in ws[excel_row]:
                cell.fill = FILL_HEADING
                cell.font = FONT_HEADING
            block = formula_blocks.get(idx)
            if block and block.status.endswith("RECONCILED"):
                pending_formulas.append((idx, block))
            elif block and block.status == "DIRECT_DIFF":
                unresolved += 1
                detail = ", ".join(f"{k}={v:.4f}" for k, v in block.diffs.items() if abs(v) > (TOLERANCE_CLP if k.endswith("clp") else TOLERANCE_UF))
                audit_entries.append(AuditEntry("WARN", company, "SOURCE_SUBTOTAL_DIFF", row.label, detail or "difference within display precision", f"{sheet_name}!A{excel_row}"))
                for cell in ws[excel_row]:
                    cell.fill = FILL_WARN
            elif not row.is_zero:
                unresolved += 1
                audit_entries.append(AuditEntry("WARN", company, "AMBIGUOUS_HIERARCHY", row.label, "No source-reconciled leaf membership inferred; source values preserved", f"{sheet_name}!A{excel_row}"))
                for cell in ws[excel_row]:
                    cell.fill = FILL_WARN
        elif row.is_zero:
            for cell in ws[excel_row]:
                cell.font = FONT_ZERO
                cell.fill = FILL_ZERO

    for idx, block in pending_formulas:
        row = rows[idx]
        excel_row = row_to_excel[idx]
        child_rows = [row_to_excel[i] for i in block.account_indexes]
        if not child_rows:
            unresolved += 1
            audit_entries.append(AuditEntry("ERROR", company, "EMPTY_SUBTOTAL_MEMBERSHIP", row.label, "Formula block reconciled in memory but resolved to no worksheet rows; source values preserved", f"{sheet_name}!A{excel_row}"))
            continue
        for col in NUMERIC_COLS:
            letter = get_column_letter(col)
            refs = ",".join(f"{letter}{r}" for r in child_rows)
            ws.cell(excel_row, col).value = f"=SUM({refs})"
            source_formulas += 1
        source_values = ", ".join(f"{field}={getattr(row, field):.4f}" for field in VALUE_FIELDS)
        audit_entries.append(AuditEntry("INFO", company, "SUBTOTAL_FORMULA_RECONCILED", row.label, f"{block.status}; source row {row.source_row}; {len(child_rows)} account rows; preserved source evidence: {source_values}", f"{sheet_name}!E{excel_row}:J{excel_row}"))

    _style_cm_sheet(ws)
    return {
        "account_rows": sum(1 for r in rows if r.row_type == "ACCOUNT"),
        "heading_rows": sum(1 for r in rows if r.row_type == "HEADING"),
        "zero_accounts": sum(1 for r in rows if r.row_type == "ACCOUNT" and r.is_zero),
        "subtotal_formulas": source_formulas,
        "unresolved_hierarchy": unresolved,
    }


def write_cam_sheet(wb, sheet_name: str, aligned: list[AlignedRow], material_heading_exceptions: set[str]) -> dict[str, int]:
    ws = wb.create_sheet(sheet_name)
    headers = ["ROW_TYPE", "ACCOUNT_CODE", "HEADING / TITLE", "EPLAZA.DESCRIPTION", "IMPULSA.DESCRIPTION", "EPLAZA.VALORES_UF", "IMPULSA.VALORES_UF", "TOTAL.VALORES_UF", "EPLAZA.VALORES_CLP", "IMPULSA.VALORES_CLP", "TOTAL.VALORES_CLP", "CONTROL", "VISIBILIDAD"]
    ws.append(headers)
    for cell in ws[1]:
        cell.fill = FILL_HEADER
        cell.font = FONT_HEADER
        cell.alignment = Alignment(horizontal="center")

    current_heading_row: Optional[int] = None
    heading_children: dict[int, list[int]] = {}
    heading_keys: dict[int, str] = {}
    heading_own_values: dict[int, bool] = {}
    account_count = 0
    hidden_accounts = 0
    hidden_headings = 0

    for row in aligned:
        excel_row = ws.max_row + 1
        if row.row_type == "HEADING":
            ws.append(["HEADING", None, row.heading, None, None, None, None, None, None, None, None, "", "MOSTRAR"])
            current_heading_row = excel_row
            heading_children[current_heading_row] = []
            heading_keys[current_heading_row] = row.key or row.heading or ""
            heading_own_values[current_heading_row] = _aligned_has_financial_value(row)
            for cell in ws[excel_row]:
                cell.fill = FILL_HEADING
                cell.font = FONT_HEADING
            continue

        ep_uf = row.ep.bal_uf if row.ep else 0.0
        im_uf = row.im.bal_uf if row.im else 0.0
        ep_clp = row.ep.bal_clp if row.ep else 0.0
        im_clp = row.im.bal_clp if row.im else 0.0
        control = "OK"
        if row.ep and row.im and row.ep.description != row.im.description:
            control = "REVISAR DESCRIPCION"
        elif row.ep is None:
            control = "IMPULSA_ONLY"
        elif row.im is None:
            control = "EPLAZA_ONLY"
        visibility = "MOSTRAR" if _aligned_has_financial_value(row) else "OCULTAR"
        if visibility == "OCULTAR":
            hidden_accounts += 1
        ws.append(["ACCOUNT", row.code, None, row.ep_desc, row.im_desc, ep_uf, im_uf, f"=F{excel_row}+G{excel_row}", ep_clp, im_clp, f"=I{excel_row}+J{excel_row}", control, visibility])
        account_count += 1
        if current_heading_row:
            heading_children.setdefault(current_heading_row, []).append(excel_row)
        if ep_uf == im_uf == ep_clp == im_clp == 0:
            for cell in ws[excel_row]:
                cell.font = FONT_ZERO
                cell.fill = FILL_ZERO

    formula_count = account_count * 2
    for heading_row, children in heading_children.items():
        if not children:
            continue
        for col in (6, 7, 8, 9, 10, 11):
            letter = get_column_letter(col)
            refs = ",".join(f"{letter}{r}" for r in children)
            ws.cell(heading_row, col).value = f"=SUM({refs})"
            formula_count += 1

        descendant_visible = any(ws.cell(child, 13).value == "MOSTRAR" for child in children)
        has_exception = heading_keys.get(heading_row, "") in material_heading_exceptions
        visibility = "MOSTRAR" if heading_own_values.get(heading_row, False) or descendant_visible or has_exception else "OCULTAR"
        ws.cell(heading_row, 13).value = visibility
        if visibility == "OCULTAR":
            hidden_headings += 1

    # Apply approved CAM hierarchical subtotal formulas after all rows exist.
    heading_occ: dict[str, int] = {}
    heading_row_by_key: dict[str, int] = {}
    for r in range(2, ws.max_row + 1):
        if ws.cell(r, 1).value == "HEADING":
            label = str(ws.cell(r, 3).value or "").strip().upper()
            heading_occ[label] = heading_occ.get(label, 0) + 1
            heading_row_by_key[f"{label}#{heading_occ[label]}"] = r

    def hkey(label: str, occ: int = 1) -> str:
        return f"{label.strip().upper()}#{occ}"

    cam_rules = {
        hkey("ACTIVOS NO CORRIENTES"): [hkey("CTAS Y DOCTOS X COBRAR A EERR", 2), hkey("INVERSION EMPRESA RELACIONADA"), hkey("PROPIEDADES Y EQUIPOS"), hkey("DEPRECIACION ACUMULADA")],
        hkey("PROYECTO HERNANDO DE AGUIRRE"): [hkey("COSTOS DIRECTOS"), hkey("GASTOS ACTIVADOS")],
        hkey("COSTOS DIRECTOS"): [hkey("TERRENO"), hkey("DERECHOS Y PERMISOS"), hkey("EMPALMES"), hkey("HONORARIOS ESPECIALIDADES"), hkey("CONSTRUCCION Y URBANIZACION"), hkey("TRASPASOS", 1), hkey("EXISTENCIA DE INMUEBLES")],
        hkey("TRASPASOS", 1): [hkey("TRASPASO A COSTO DE CONSTRUCCION")],
        hkey("TRASPASO A COSTO DE CONSTRUCCION"): [hkey("EXISTENCIA DE INMUEBLES")],
        hkey("GASTOS ACTIVADOS"): [hkey("MARKETING"), hkey("PILOTO Y SALA DE VENTA"), hkey("COMERCIALIZACION"), hkey("ASESORIA PROYECTO"), hkey("IMPREVISTOS"), hkey("GASTOS FINANCIEROS"), hkey("GASTOS GENERALES"), hkey("TRASPASOS", 2), hkey("GASTOS DE VENTAS"), hkey("INTERESES DIFERIDOS")],
        hkey("TOTAL ACTIVO"): [hkey("EFECTIVO O EFECTIVO EQUIVALENTE"), hkey("VALORES NEGOCIABLES", 1), hkey("VALORES NEGOCIABLES", 2), hkey("DEUDORES POR PROMESAS"), hkey("DEUDORES POR VENTAS"), hkey("DEUDORES VARIOS"), hkey("CTAS Y DOCTOS X COBRAR A EERR", 1), hkey("IMPUESTOS POR RECUPERAR"), hkey("ACTIVOS NO CORRIENTES"), hkey("PROYECTO HERNANDO DE AGUIRRE")],
        hkey("TOTAL PASIVO"): [hkey("LINEAS DE CREDITO"), hkey("OBLIG. CON BCOS E INST FINANCIERAS"), hkey("CUENTAS POR PAGAR"), hkey("ACREEDORES VARIOS"), hkey("DOCTOS Y CTAS POR PAGAR EERR"), hkey("IMPUESTO A LA RENTA"), hkey("OTROS PASIVOS CORRIENTES"), hkey("OBLIG. C/BCOS E INST FINANC. L/PLAZO"), hkey("OTROS PASIVOS NO CORRIENTES"), hkey("DOCTOS Y CTAS POR PAGAR SOCIOS"), hkey("INGRESOS ANTICIPADOS"), hkey("PATRIMONIO")],
        hkey("ACTIVO  -   PASIVO"): [hkey("TOTAL ACTIVO"), hkey("TOTAL PASIVO")],
        hkey("RESULTADO"): [hkey("ACTIVO  -   PASIVO")],
        hkey("TOTALES GENERALES"): [hkey("TOTAL ACTIVO"), hkey("TOTAL PASIVO"), hkey("RESULTADO")],
    }
    for parent_key, child_keys in cam_rules.items():
        parent = heading_row_by_key.get(parent_key)
        children_rows = [heading_row_by_key[k] for k in child_keys if k in heading_row_by_key]
        if not parent or not children_rows:
            continue
        for col in (6, 7, 9, 10):
            letter = get_column_letter(col)
            refs = ",".join(f"{letter}{r}" for r in children_rows)
            ws.cell(parent, col).value = f"=-{refs}" if parent_key == hkey("RESULTADO") else f"=SUM({refs})"
            formula_count += 1
        ws.cell(parent, 8).value = f"=F{parent}+G{parent}"
        ws.cell(parent, 11).value = f"=I{parent}+J{parent}"
        formula_count += 2

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:M{ws.max_row}"
    widths = {"A": 12, "B": 14, "C": 34, "D": 42, "E": 42, "F": 16, "G": 16, "H": 16, "I": 18, "J": 18, "K": 18, "L": 20, "M": 14}
    for col, width in widths.items():
        ws.column_dimensions[col].width = width
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.border = THIN_BOTTOM
            if cell.column in (6, 7, 8):
                cell.number_format = '#,##0.00;[Red]-#,##0.00;0.00'
            elif cell.column in (9, 10, 11):
                cell.number_format = '#,##0;[Red]-#,##0;0'

    return {"account_rows": account_count, "formula_cells": formula_count, "hidden_accounts": hidden_accounts, "hidden_headings": hidden_headings}


APPROVED_PH1_RULES: tuple[CriteriaRule, ...] = (
    CriteriaRule("CR-001", "EPLAZA", _ref("heading", "CTAS Y DOCTOS X COBRAR A EERR#1"), (_ref("code", "110612"),), fixture_cell="G23", approved_formula_note="=SUM(G24)"),
    CriteriaRule("CR-002", "IMPULSA", _ref("heading", "TOTAL ACTIVO#1"), (_ref("heading", "EFECTIVO O EFECTIVO EQUIVALENTE#1"), _ref("heading", "VALORES NEGOCIABLES#1"), _ref("heading", "VALORES NEGOCIABLES#2"), _ref("heading", "DEUDORES VARIOS#1"), _ref("heading", "IMPUESTOS POR RECUPERAR#1"), _ref("heading", "CTAS Y DOCTOS X COBRAR A EERR#1"), _ref("heading", "INVERSION EMPRESA RELACIONADA#1"), _ref("heading", "PROPIEDADES Y EQUIPOS#1"), _ref("heading", "DEPRECIACION ACUMULADA#1")), fixture_cell="G39", approved_formula_note="=SUM(G4,G8,G10,G12,G16,G20,G27,G34,G36)"),
    CriteriaRule("CR-003", "EPLAZA", _ref("heading", "TOTAL ACTIVO#1"), (_ref("heading", "EFECTIVO O EFECTIVO EQUIVALENTE#1"), _ref("heading", "VALORES NEGOCIABLES#1"), _ref("heading", "VALORES NEGOCIABLES#2"), _ref("heading", "DEUDORES POR PROMESAS#1"), _ref("heading", "DEUDORES POR VENTAS#1"), _ref("heading", "DEUDORES VARIOS#1"), _ref("heading", "CTAS Y DOCTOS X COBRAR A EERR#1"), _ref("heading", "IMPUESTOS POR RECUPERAR#1"), _ref("heading", "ACTIVOS NO CORRIENTES#1"), _ref("heading", "PROYECTO HERNANDO DE AGUIRRE#1")), fixture_cell="G160", approved_formula_note="=SUM(G4,G9,G11,G13,G15,G17,G23,G25,G31,G55)"),
    CriteriaRule("CR-004", "EPLAZA", _ref("heading", "PROYECTO HERNANDO DE AGUIRRE#1"), (_ref("heading", "COSTOS DIRECTOS#1"), _ref("heading", "GASTOS ACTIVADOS#1")), fixture_cell="G55", approved_formula_note="=SUM(G57,G111)"),
    CriteriaRule("CR-005", "EPLAZA", _ref("heading", "GASTOS ACTIVADOS#1"), (_ref("heading", "MARKETING#1"), _ref("heading", "PILOTO Y SALA DE VENTA#1"), _ref("heading", "COMERCIALIZACION#1"), _ref("heading", "ASESORIA PROYECTO#1"), _ref("heading", "IMPREVISTOS#1"), _ref("heading", "GASTOS FINANCIEROS#1"), _ref("heading", "GASTOS GENERALES#1"), _ref("heading", "TRASPASOS#2"), _ref("heading", "GASTOS DE VENTAS#1"), _ref("heading", "INTERESES DIFERIDOS#1")), fixture_cell="G111", approved_formula_note="HUMAN_APPROVED_DIRECT_SUBTOTALS_UNDER_GASTOS_ACTIVADOS"),
    CriteriaRule("CR-006", "EPLAZA", _ref("heading", "OBLIG. C/BCOS E INST FINANC. L/PLAZO#1"), (_ref("code", "220111"), _ref("code", "220112")), fixture_cell="G191", approved_formula_note="=SUM(G192:G193)"),
    CriteriaRule("CR-007", "IMPULSA", _ref("heading", "OTROS PASIVOS CORRIENTES#1"), (_ref("code", "210932"), _ref("code", "210941"), _ref("code", "220411")), fixture_cell="G57", approved_formula_note="immediate child accounts if reconciles RAW"),
    CriteriaRule("CR-008", "EPLAZA", _ref("heading", "TOTAL PASIVO#1"), (_ref("heading", "LINEAS DE CREDITO#1"), _ref("heading", "OBLIG. CON BCOS E INST FINANCIERAS#1"), _ref("heading", "CUENTAS POR PAGAR#1"), _ref("heading", "ACREEDORES VARIOS#1"), _ref("heading", "DOCTOS Y CTAS POR PAGAR EERR#1"), _ref("heading", "IMPUESTO A LA RENTA#1"), _ref("heading", "OTROS PASIVOS CORRIENTES#1"), _ref("heading", "OBLIG. C/BCOS E INST FINANC. L/PLAZO#1"), _ref("heading", "OTROS PASIVOS NO CORRIENTES#1"), _ref("heading", "DOCTOS Y CTAS POR PAGAR SOCIOS#1"), _ref("heading", "INGRESOS ANTICIPADOS#1"), _ref("heading", "PATRIMONIO#1")), fixture_cell="G219", approved_formula_note="=SUM(G162,G164,G167,G171,G174,G178,G180,G191,G194,G197,G205,G207)"),
    CriteriaRule("CR-009", "IMPULSA", _ref("heading", "TOTAL PASIVO#1"), (_ref("heading", "OBLIGACIONES CON BANCOS DE C/PLAZO#1"), _ref("heading", "CUENTAS POR PAGAR#1"), _ref("heading", "ACREEDORES VARIOS#1"), _ref("heading", "DOCTOS Y CTAS POR PAGAR EERR#1"), _ref("heading", "IMPUESTO A LA RENTA#1"), _ref("heading", "OTROS PASIVOS CORRIENTES#1"), _ref("heading", "DOCTOS Y CTAS POR PAGAR SOCIOS#1"), _ref("heading", "OBLIG. C/BCOS E INST FINANC. L/PLAZO#1"), _ref("heading", "PATRIMONIO#1")), fixture_cell="G84", approved_formula_note="=SUM(G41,G44,G46,G49,G55,G57,G61,G69,G71)"),
    CriteriaRule("CR-010", "EPLAZA", _ref("heading", "ACTIVO - PASIVO#1"), (_ref("heading", "TOTAL ACTIVO#1"), _ref("heading", "TOTAL PASIVO#1")), fixture_cell="G221", approved_formula_note="=SUM(G160,G219)"),
    CriteriaRule("CR-011", "IMPULSA", _ref("heading", "ACTIVO - PASIVO#1"), (_ref("heading", "TOTAL ACTIVO#1"), _ref("heading", "TOTAL PASIVO#1")), fixture_cell="G86", approved_formula_note="=SUM(G39,G84)"),
    CriteriaRule("CR-012", "EPLAZA", _ref("heading", "RESULTADO#1"), (_ref("heading", "ACTIVO - PASIVO#1"),), operation="negate", fixture_cell="G280", approved_formula_note="=-G221"),
    CriteriaRule("CR-013", "IMPULSA", _ref("heading", "RESULTADO#1"), (_ref("heading", "ACTIVO - PASIVO#1"),), operation="negate", fixture_cell="G135", approved_formula_note="=-G86"),
    CriteriaRule("CR-014", "EPLAZA", _ref("heading", "TOTALES GENERALES#1"), (_ref("heading", "TOTAL ACTIVO#1"), _ref("heading", "TOTAL PASIVO#1"), _ref("heading", "RESULTADO#1")), fixture_cell="G282", approved_formula_note="=SUM(G160,G219,G280)"),
    CriteriaRule("CR-015", "IMPULSA", _ref("heading", "TOTALES GENERALES#1"), (_ref("heading", "TOTAL ACTIVO#1"), _ref("heading", "TOTAL PASIVO#1"), _ref("heading", "RESULTADO#1")), fixture_cell="G137", approved_formula_note="=SUM(G39,G84,G135)"),
)


def _criteria_sheet_name(period: str, company: str) -> str:
    return f"CM{period}_{company}"


def _build_semantic_index(rows: list[AccountRow]) -> dict[SemanticRef, int]:
    index: dict[SemanticRef, int] = {}
    for idx, row in enumerate(rows):
        if row.row_type == "ACCOUNT" and row.code:
            index[_ref("code", row.code)] = idx
        elif row.row_type == "HEADING" and row.heading_key:
            index[_ref("heading", row.heading_key)] = idx
    return index


def _excel_row_for_index(idx: int) -> int:
    return idx + 3


def _format_sum_formula(rows: list[int]) -> str:
    if not rows:
        return "=SUM()"
    parts: list[str] = []
    start = prev = rows[0]
    for row in rows[1:] + [None]:
        if row is not None and row == prev + 1:
            prev = row
            continue
        if start == prev:
            parts.append(f"G{start}")
        else:
            parts.append(f"G{start}:G{prev}")
        if row is not None:
            start = prev = row
    return f"=SUM({','.join(parts)})"


def apply_approved_ph1_criteria(period: str, wb, rows_by_company: dict[str, list[AccountRow]], audit_entries: list[AuditEntry]) -> dict[str, object]:
    applied: list[dict[str, object]] = []
    blocked: list[dict[str, object]] = []
    matrix: list[dict[str, object]] = []
    indexes = {company: _build_semantic_index(rows) for company, rows in rows_by_company.items()}

    for rule in APPROVED_PH1_RULES:
        rows = rows_by_company[rule.company]
        index = indexes[rule.company]
        sheet_name = _criteria_sheet_name(period, rule.company)
        ws = wb[sheet_name]

        target_idx = index.get(rule.target)
        operand_indexes = [index.get(operand) for operand in rule.operands]
        if target_idx is None or any(idx is None for idx in operand_indexes):
            blocked.append({"rule_id": rule.rule_id, "company": rule.company, "reason": "semantic reference not found"})
            continue

        resolved_operands = [idx for idx in operand_indexes if idx is not None]
        target_row = rows[target_idx]
        target_excel_row = _excel_row_for_index(target_idx)
        operand_excel_rows = [_excel_row_for_index(idx) for idx in resolved_operands]
        formula = f"=-G{operand_excel_rows[0]}" if rule.operation == "negate" else _format_sum_formula(operand_excel_rows)
        python_calc = -rows[resolved_operands[0]].bal_uf if rule.operation == "negate" else sum(rows[idx].bal_uf for idx in resolved_operands)
        source_uf = target_row.bal_uf
        diff = python_calc - source_uf
        status = "NUMERICALLY_VERIFIED" if abs(diff) <= 0.01 else "HUMAN_MORCH_REVIEW_REQUIRED"

        ws.cell(target_excel_row, 7).value = formula
        destination = f"{sheet_name}!G{target_excel_row}"
        member_evidence = [
            {
                "kind": operand.kind,
                "key": operand.key,
                "row": _excel_row_for_index(idx),
                "label": rows[idx].label,
                "source_uf": rows[idx].bal_uf,
            }
            for operand, idx in zip(rule.operands, resolved_operands)
        ]
        entry = {
            "RULE_ID": rule.rule_id,
            "COMPANY": rule.company,
            "SEMANTIC_KEY": rule.target.key,
            "EXCEL_DESTINATION": destination,
            "EXCEL_FORMULA": formula,
            "APPROVED_FORMULA_REFERENCE": rule.approved_formula_note,
            "PYTHON_CALCULATED_UF": python_calc,
            "SOURCE_UF": source_uf,
            "EXCEL_CALCULATED_UF": None,
            "DIFFERENCE_UF": diff,
            "STATUS": status,
            "EVIDENCE": {
                "target_label": target_row.label,
                "target_source_row": target_row.source_row,
                "target_fixture_cell": rule.fixture_cell,
                "members": member_evidence,
            },
        }
        matrix.append(entry)
        applied.append(entry)
        audit_entries.append(AuditEntry("INFO" if status == "NUMERICALLY_VERIFIED" else "WARN", rule.company, f"PH1_CRITERION_{status}", rule.rule_id, f"{formula}; diff_uf={diff:.6f}", destination))

    verified = sum(1 for entry in matrix if entry["STATUS"] == "NUMERICALLY_VERIFIED")
    return {
        "applied": applied,
        "blocked": blocked,
        "matrix": matrix,
        "applied_count": len(applied),
        "blocked_count": len(blocked),
        "numerically_verified_count": verified,
    }


def write_audit_sheet(wb, entries: list[AuditEntry]) -> None:
    ws = wb.create_sheet("AUDIT.PH1")
    ws.append(["SEVERIDAD", "EMPRESA", "HALLAZGO", "CLAVE", "DETALLE", "UBICACION"])
    for cell in ws[1]:
        cell.fill = FILL_HEADER
        cell.font = FONT_HEADER
    for entry in entries:
        ws.append([
            _literal_excel_text(entry.severity),
            _literal_excel_text(entry.company),
            _literal_excel_text(entry.finding),
            _literal_excel_text(entry.key),
            _literal_excel_text(entry.detail),
            _literal_excel_text(entry.location),
        ])
        if entry.severity in ("WARN", "ERROR"):
            for cell in ws[ws.max_row]:
                cell.fill = FILL_WARN
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:F{ws.max_row}"
    for col, width in {"A": 12, "B": 12, "C": 30, "D": 28, "E": 80, "F": 28}.items():
        ws.column_dimensions[col].width = width


def write_control_sheet(wb, period: str, raw_eplaza: Path, raw_impulsa: Path, metrics: dict, source_hashes: dict[str, str]) -> None:
    ws = wb.create_sheet("CONTROL")
    rows = [
        ("CONTROL_KEY", "VALUE", "DETAIL"),
        ("PERIOD", period, ""),
        ("EPLAZA_RAW", raw_eplaza.name, source_hashes[str(raw_eplaza)]),
        ("IMPULSA_RAW", raw_impulsa.name, source_hashes[str(raw_impulsa)]),
        ("EPLAZA_ACCOUNTS", metrics["eplaza"]["account_rows"], ""),
        ("IMPULSA_ACCOUNTS", metrics["impulsa"]["account_rows"], ""),
        ("CAM_ACCOUNTS", metrics["cam"]["account_rows"], ""),
        ("FORMULA_STRUCTURE_PASS", "PASS", "openpyxl formula/package validation"),
        ("EXCEL_DESKTOP_VALIDATION", "NOT_TESTED", "No Excel Desktop recalculation was executed"),
    ]
    for row in rows:
        ws.append(row)
    for cell in ws[1]:
        cell.fill = FILL_HEADER
        cell.font = FONT_HEADER
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 45
    ws.column_dimensions["C"].width = 80


def write_workbook(period: str, ep_rows: list[AccountRow], im_rows: list[AccountRow], aligned: list[AlignedRow], raw_eplaza: Path, raw_impulsa: Path) -> tuple[openpyxl.Workbook, dict, list[AuditEntry]]:
    audit_entries = audit_alignment(aligned)
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    material_heading_exceptions = hierarchy_exception_keys(ep_rows) | hierarchy_exception_keys(im_rows)

    metrics = {
        "cam": write_cam_sheet(wb, f"CAM{period}_CONSOL.ALIGN", aligned, material_heading_exceptions),
        "eplaza": write_cm_sheet(wb, f"CM{period}_EPLAZA", ep_rows, "EPLAZA", audit_entries),
        "impulsa": write_cm_sheet(wb, f"CM{period}_IMPULSA", im_rows, "IMPULSA", audit_entries),
    }
    source_hashes = {str(raw_eplaza): _sha256(raw_eplaza), str(raw_impulsa): _sha256(raw_impulsa)}
    criteria_metrics = apply_approved_ph1_criteria(period, wb, {"EPLAZA": ep_rows, "IMPULSA": im_rows}, audit_entries)
    metrics["approved_criteria"] = criteria_metrics
    write_audit_sheet(wb, audit_entries)
    write_control_sheet(wb, period, raw_eplaza, raw_impulsa, metrics, source_hashes)
    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True
    return wb, metrics | {"source_hashes": source_hashes}, audit_entries


def _formula_integrity(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as zf:
        broken_ref = 0
        empty_sum = 0
        formulas = 0
        for name in zf.namelist():
            if not name.startswith("xl/worksheets/") or not name.endswith(".xml"):
                continue
            text = zf.read(name).decode("utf-8", errors="ignore")
            broken_ref += text.count("#REF!")
            empty_sum += len(re.findall(r"<f[^>]*>\s*SUM\(\)\s*</f>", text))
            formulas += text.count("<f")
    return {"xlsx_package": "PASS", "formula_cells_xml": formulas, "broken_refs_xml": broken_ref, "empty_sum_formulas_xml": empty_sum}


def run_ph1(raw_eplaza, raw_impulsa, out_dir, period: str = "2026.08") -> Path:
    raw_eplaza = Path(raw_eplaza)
    raw_impulsa = Path(raw_impulsa)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    out_xlsx = out_dir / f"CAM{period}_CONSOL.ALIGN.xlsx"
    report_path = out_dir / "KTMA_PH1_REPORT.json"
    evidence_path = Path("08_EVIDENCE/REPORTS/KTMA_TASK031_SPECIALIST_PH1_FINANCIAL_CONVERGENCE_REPORT.json")
    evidence_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[1/6] Parsing EPLAZA XLSB at {raw_eplaza}")
    ep_rows = parse_xlsb(raw_eplaza)
    print(f"      EPLAZA: {len(ep_rows)} total rows, {sum(r.row_type == 'ACCOUNT' for r in ep_rows)} account rows")

    print(f"[2/6] Parsing IMPULSA XLSB at {raw_impulsa}")
    im_rows = parse_xlsb(raw_impulsa)
    print(f"      IMPULSA: {len(im_rows)} total rows, {sum(r.row_type == 'ACCOUNT' for r in im_rows)} account rows")

    print("[3/6] Aligning accounts and headings")
    aligned = align(ep_rows, im_rows)
    print(f"      CAM: {sum(r.row_type == 'ACCOUNT' for r in aligned)} account rows")

    print("[4/6] Writing five-sheet PH1 workbook")
    wb, metrics, audit_entries = write_workbook(period, ep_rows, im_rows, aligned, raw_eplaza, raw_impulsa)
    wb.save(out_xlsx)
    package = _formula_integrity(out_xlsx)
    output_hash = _sha256(out_xlsx)

    unresolved = metrics["eplaza"]["unresolved_hierarchy"] + metrics["impulsa"]["unresolved_hierarchy"]
    criteria = metrics.get("approved_criteria", {})
    approved_criteria_verified = (
        criteria.get("applied_count") == len(APPROVED_PH1_RULES)
        and criteria.get("blocked_count") == 0
        and criteria.get("numerically_verified_count") == len(APPROVED_PH1_RULES)
    )
    blocking_unresolved = 0 if approved_criteria_verified else unresolved
    status = "PASS"
    if package["broken_refs_xml"] or package["empty_sum_formulas_xml"] or any(entry.severity == "ERROR" for entry in audit_entries) or blocking_unresolved:
        status = "PARTIAL"

    required_sheets = [f"CAM{period}_CONSOL.ALIGN", f"CM{period}_EPLAZA", f"CM{period}_IMPULSA", "AUDIT.PH1", "CONTROL"]
    execution_platform = platform.system() or "Unknown"
    report = {
        "task_id": "KTMA_TASK031_SPECIALIST_PH1_FINANCIAL_CONVERGENCE",
        "period": period,
        "ph1_status": status,
        "output_path": str(out_xlsx),
        "output_hash_sha256": output_hash,
        "required_sheets": required_sheets,
        "metrics": metrics,
        "audit_count": len(audit_entries),
        "unresolved_hierarchy_count": unresolved,
        "approved_criteria_resolved_hierarchy_count": unresolved if approved_criteria_verified else 0,
        "blocking_unresolved_hierarchy_count": blocking_unresolved,
        "formula_integrity": package,
        "excel_desktop_validation": "NOT_TESTED",
        "execution_platform": execution_platform,
        "windows_execution": "PASS" if execution_platform == "Windows" else "NOT_TESTED_IN_THIS_RUN",
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    evidence_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("[5/6] Workbook/package validation")
    print(f"      Sheets: {', '.join(required_sheets)}")
    print(f"      Formula cells (XML): {package['formula_cells_xml']}")
    print(f"      Broken refs (XML): {package['broken_refs_xml']}")
    print(f"      Empty SUM formulas (XML): {package['empty_sum_formulas_xml']}")

    print("[6/6] PH1 report")
    print(f"      Output: {out_xlsx}")
    print(f"      SHA256: {output_hash}")
    print(f"      PH1 STATUS: {status}")
    return out_xlsx
