from __future__ import annotations

import csv
import hashlib
import json
import shutil
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterable

import openpyxl
from openpyxl.utils.cell import coordinate_to_tuple

from .engine import parse_xlsb


MAPPING_VERSION = "1.0.0"
DECISION_ID = "KTMA-FM-DEC-20261029-001"
MISSING = "SIN_DATO_ENTIDAD"
UF_SCALE = Decimal("0.01")
FM_TARGET_CELL_INVENTORY = tuple(
    f"FM!{entity}{row}"
    for row in (8, 9, 10, 12, 13, 14, 17, 18, 19, 27, 28, 29, 30, 31, 32, 36, 37, 38, 39, 40, 41, 42, 48, 49, 50, 51, 52, 53, 54, 55, 61, 65, 69, 75, 76, 77)
    for entity in ("E", "F")
)


@dataclass(frozen=True)
class Target:
    target_id: str
    document_alias: str
    name: str
    sheet: str
    cell_eplaza: str
    cell_impulsa: str
    cell_total: str


@dataclass(frozen=True)
class MappingRule:
    mapping_id: str
    account_id: str
    account_description: str
    fm_target_id: str
    fm_target_name: str
    fm_sheet: str
    fm_cell_eplaza: str
    fm_cell_impulsa: str
    fm_cell_total: str
    coefficient: int
    status: str
    justification: str
    valid_from: str
    valid_to: str | None
    decision_id: str
    version: str


@dataclass(frozen=True)
class AccountValue:
    entity: str
    account_id: str
    description: str
    value_uf: Decimal
    source_sheet: str
    source_row: int
    source_sha256: str


@dataclass(frozen=True)
class Contribution:
    mapping_id: str
    account_id: str
    entity: str
    source_value_uf: Decimal | None
    coefficient: int
    contribution_uf: Decimal | None
    status: str


@dataclass(frozen=True)
class TargetResult:
    target_id: str
    target_name: str
    eplaza_uf: Decimal | None
    impulsa_uf: Decimal | None
    total_uf: Decimal | None
    status: str


TARGETS = (
    Target("FM-T027", "FM-M01", "Terreno Neto", "FM", "E27", "F27", "D27"),
    Target("FM-T028", "FM-M02", "Comisión terreno", "FM", "E28", "F28", "D28"),
    Target("FM-T031", "FM-M03", "Estructuración", "FM", "E31", "F31", "D31"),
    Target("FM-T048", "FM-M04", "Gastos Comunes, mantención y Contribuciones", "FM", "E48", "F48", "D48"),
    Target("FM-T032", "FM-M05", "Otros Terreno", "FM", "E32", "F32", "D32"),
    Target("FM-T036", "FM-M06", "Derechos", "FM", "E36", "F36", "D36"),
    Target("FM-T041", "FM-M07", "Empalmes", "FM", "E41", "F41", "D41"),
    Target("FM-T042", "FM-M08", "Honorario Especialistas", "FM", "E42", "F42", "D42"),
    Target("FM-T038", "FM-M09", "Construcción (Incl. IVB)", "FM", "E38", "F38", "D38"),
    Target("FM-T039", "FM-M10", "Crédito especial IVA", "FM", "E39", "F39", "D39"),
    Target("FM-T037", "FM-M11", "Demolición y Obras exteriores", "FM", "E37", "F37", "D37"),
    Target("FM-T049", "FM-M12", "Marketing", "FM", "E49", "F49", "D49"),
    Target("FM-T050", "FM-M13", "Comercialización", "FM", "E50", "F50", "D50"),
    Target("FM-T053", "FM-M14", "Gasto Financiero", "FM", "E53", "F53", "D53"),
    Target("FM-T055", "FM-M15", "Pólizas de venta en verde", "FM", "E55", "F55", "D55"),
    Target("FM-T040", "FM-M16", "Honorarios Post venta y Plan OK", "FM", "E40", "F40", "D40"),
)


GROUPS: dict[str, tuple[tuple[str, str], ...]] = {
    "FM-T027": (("120911", "Terreno"),),
    "FM-T028": (("120912", "Costo Comision Terreno"),),
    "FM-T031": (("120913", "Estructuracion"),),
    "FM-T048": (("120914", "Contribuciones Bs Rs"),),
    "FM-T032": (("120915", "Otros Terrenos"),),
    "FM-T036": (("120921", "Dºs Municipales"), ("120922", "Arquitecto Revisor"), ("120923", "Otros Derechos")),
    "FM-T041": (("120931", "Empalme Electrico"), ("120932", "Empalme Agua Potable"), ("120980", "Adicional Empalmes")),
    "FM-T042": (
        ("120941", "Arquitectura"), ("120942", "Calculo"), ("120943", "Electricidad"),
        ("120944", "Alcantarillado"), ("120945", "A/C y/o Calefaccion"),
        ("120946", "Mecanica de Suelos"), ("120947", "Extraccion de Basura"),
        ("120948", "Analisis Vial Basico"), ("120949", "Topografia"),
        ("120950", "Proyectista Serviu"), ("120951", "Corrientes Debiles"),
        ("120952", "Legales"), ("120953", "Insp. Tecnica de Obras (ITO)"),
        ("120954", "Legales"), ("120955", "Paisajismo"), ("120956", "Fotocopia Planos"),
        ("120957", "Seguridad"), ("120958", "Instalaciones Sanitarias"),
        ("120959", "Otros Honorarios Profesionales"), ("120960", "Calculista Revisor"),
        ("120961", "Building Information Modeling (BIM)"), ("121041", "Asesoria Proyecto"),
        ("121073", "Asesoria Contable y Tributaria"), ("410451", "Asesoria Financiera"),
        ("410452", "Asesoria Legal"), ("410455", "Auditorias y Contabilidad"),
    ),
    "FM-T038": (("120971", "Contrato Suma Alzada"), ("120973", "Otros Const. y Urbanizacion")),
    "FM-T039": (("120972", "Credito Especial"),),
    "FM-T037": (("120981", "Demolicion y Obras Exteriores"),),
    "FM-T049": (
        ("121011", "Publicidad en Medios"), ("121012", "Honorarios Publicista"),
        ("121013", "Material de Distribucion"), ("121015", "Señalética"),
        ("121016", "Estudio de Mercado"), ("121017", "Otras Asesorías"),
        ("121021", "Construccion Sala de Ventas"), ("121022", "Construccion Piloto"),
        ("121023", "Decoracion Piloto"), ("121025", "Equipamiento Computacional"),
        ("121026", "Mobiliario Sala de Ventas"), ("121027", "Gastos Generales Sala de Ventas"),
        ("121028", "Sistema Cotizacion Sala de Ventas"), ("121029", "Soporte y Mantencion Informatica"),
    ),
    "FM-T050": (("121031", "Costo Corretaje"),),
    "FM-T053": (
        ("121061", "Gastos Bancarios"), ("121062", "Impto Timbre Prestamos"),
        ("121063", "Otros Gastos Bancarios"), ("121065", "Intereses Pagados"),
        ("121067", "Intereses Credito Terreno"), ("121068", "Intereses Credito Construccion"),
        ("121071", "Gastos Generales"), ("121072", "Gtos Generales Legales Sociedad"),
    ),
    "FM-T055": (("121064", "Prima Seguro Venta en Verde"),),
    "FM-T040": (("410457", "Software"),),
}


def mapping_rules() -> tuple[MappingRule, ...]:
    targets = {target.target_id: target for target in TARGETS}
    rules: list[MappingRule] = []
    for target_id, accounts in GROUPS.items():
        target = targets[target_id]
        for account_id, description in accounts:
            rules.append(
                MappingRule(
                    mapping_id=f"KTMA-FM-{account_id}-V100",
                    account_id=account_id,
                    account_description=description,
                    fm_target_id=target.target_id,
                    fm_target_name=target.name,
                    fm_sheet=target.sheet,
                    fm_cell_eplaza=target.cell_eplaza,
                    fm_cell_impulsa=target.cell_impulsa,
                    fm_cell_total=target.cell_total,
                    coefficient=1,
                    status="IMPLEMENTED",
                    justification="Asignación HUMAN evidenciada por mapeo1.xlsx y V02 conceptual",
                    valid_from="2026.09",
                    valid_to=None,
                    decision_id=DECISION_ID,
                    version=MAPPING_VERSION,
                )
            )
    validate_rules(rules)
    return tuple(rules)


def validate_rules(rules: Iterable[MappingRule]) -> None:
    seen: dict[str, str] = {}
    target_ids = {target.target_id for target in TARGETS}
    for rule in rules:
        if rule.coefficient not in (-1, 1):
            raise ValueError(f"COEFFICIENT_INVALID:{rule.mapping_id}")
        if rule.fm_target_id not in target_ids:
            raise ValueError(f"FM_TARGET_UNKNOWN:{rule.fm_target_id}")
        prior = seen.setdefault(rule.account_id, rule.fm_target_id)
        if prior != rule.fm_target_id:
            raise ValueError(f"ACCOUNT_MULTIPLE_TARGETS:{rule.account_id}:{prior}:{rule.fm_target_id}")


def effective_rules_for_period(rules: Iterable[MappingRule], period: str) -> tuple[MappingRule, ...]:
    return tuple(
        rule for rule in rules
        if rule.valid_from <= period and (rule.valid_to is None or period <= rule.valid_to)
        and rule.status in {"IMPLEMENTED", "SUPERSEDED"}
    )


def apply_mapping_change(
    rules: Iterable[MappingRule], decision: dict[str, object], *, new_version: str,
    retroactive_authorized: bool = False,
) -> tuple[MappingRule, ...]:
    rules = tuple(rules)
    required = {
        "DECISION_ID", "ACCOUNT_ID", "PREVIOUS_FM_TARGET", "NEW_FM_TARGET",
        "PREVIOUS_COEFFICIENT", "NEW_COEFFICIENT", "EFFECTIVE_PERIOD", "STATUS",
    }
    missing = sorted(required - set(decision))
    if missing:
        raise ValueError(f"DECISION_FIELDS_MISSING:{','.join(missing)}")
    if decision["STATUS"] not in {"APPROVED", "IMPLEMENTED"}:
        return rules
    if not decision["EFFECTIVE_PERIOD"]:
        return rules
    account_id = str(decision["ACCOUNT_ID"])
    current = next((rule for rule in rules if rule.account_id == account_id and rule.valid_to is None), None)
    if current is None:
        raise ValueError(f"ACCOUNT_MAPPING_NOT_FOUND:{account_id}")
    if current.fm_target_id != decision["PREVIOUS_FM_TARGET"]:
        raise ValueError("PREVIOUS_FM_TARGET_MISMATCH")
    if current.coefficient != int(decision["PREVIOUS_COEFFICIENT"]):
        raise ValueError("PREVIOUS_COEFFICIENT_MISMATCH")
    effective_period = str(decision["EFFECTIVE_PERIOD"])
    if effective_period < current.valid_from and not retroactive_authorized:
        raise ValueError("RETROACTIVE_AUTHORIZATION_REQUIRED")
    target = next((item for item in TARGETS if item.target_id == decision["NEW_FM_TARGET"]), None)
    if target is None:
        raise ValueError("NEW_FM_TARGET_UNKNOWN")
    year, month = map(int, effective_period.split("."))
    previous_period = f"{year - 1}.12" if month == 1 else f"{year}.{month - 1:02d}"
    closed = replace(current, valid_to=previous_period, status="SUPERSEDED")
    changed = replace(
        current,
        mapping_id=f"KTMA-FM-{account_id}-V{new_version.replace('.', '')}",
        fm_target_id=target.target_id,
        fm_target_name=target.name,
        fm_sheet=target.sheet,
        fm_cell_eplaza=target.cell_eplaza,
        fm_cell_impulsa=target.cell_impulsa,
        fm_cell_total=target.cell_total,
        coefficient=int(decision["NEW_COEFFICIENT"]),
        status="IMPLEMENTED",
        valid_from=effective_period,
        valid_to=None,
        decision_id=str(decision["DECISION_ID"]),
        version=new_version,
    )
    updated = tuple(rule for rule in rules if rule is not current) + (closed, changed)
    validate_rules(effective_rules_for_period(updated, effective_period))
    return updated


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_entity_values(path: Path, entity: str) -> dict[str, AccountValue]:
    source_hash = _sha256(path)
    result: dict[str, AccountValue] = {}
    for row in parse_xlsb(path):
        if not row.code:
            continue
        result[row.code] = AccountValue(
            entity=entity,
            account_id=row.code,
            description=row.description or row.heading or "",
            value_uf=Decimal(str(row.bal_uf)),
            source_sheet=row.source_sheet,
            source_row=row.source_row,
            source_sha256=source_hash,
        )
    return result


def load_consolidated_values(path: Path) -> dict[str, dict[str, AccountValue]]:
    """Load the real CAM contract without treating a missing formula cache as zero."""
    source_hash = _sha256(path)
    wb = openpyxl.load_workbook(path, read_only=True, data_only=False)
    sheet_name = next(name for name in wb.sheetnames if "CONSOL.ALIGN" in name)
    ws = wb[sheet_name]
    header_row = None
    headers: dict[str, int] = {}
    for row_number in range(1, min(ws.max_row, 10) + 1):
        candidate = {str(ws.cell(row_number, col).value or "").strip(): col for col in range(1, ws.max_column + 1)}
        if "ACCOUNT_CODE" in candidate and "TOTAL.VALORES_UF" in candidate:
            header_row, headers = row_number, candidate
            break
    if header_row is None:
        raise ValueError("CONSOLIDATED_HEADER_NOT_FOUND")
    required = {"ACCOUNT_CODE", "EPLAZA.DESCRIPTION", "IMPULSA.DESCRIPTION", "EPLAZA.VALORES_UF", "IMPULSA.VALORES_UF", "TOTAL.VALORES_UF"}
    if not required <= set(headers):
        raise ValueError(f"CONSOLIDATED_COLUMNS_MISSING:{sorted(required - set(headers))}")
    values: dict[str, dict[str, AccountValue]] = {"EPLAZA": {}, "IMPULSA": {}}
    for row_number in range(header_row + 1, ws.max_row + 1):
        account = ws.cell(row_number, headers["ACCOUNT_CODE"]).value
        if account in (None, ""):
            continue
        account_id = str(account).strip()
        e_value = ws.cell(row_number, headers["EPLAZA.VALORES_UF"]).value
        i_value = ws.cell(row_number, headers["IMPULSA.VALORES_UF"]).value
        total_formula = ws.cell(row_number, headers["TOTAL.VALORES_UF"]).value
        if e_value is None or i_value is None:
            raise ValueError(f"CONSOLIDATED_ENTITY_VALUE_MISSING:{account_id}")
        if not isinstance(total_formula, str) or not total_formula.startswith("="):
            raise ValueError(f"TOTAL_VALORES_UF_FORMULA_MISSING:{account_id}")
        for entity, raw_value, description_key in (
            ("EPLAZA", e_value, "EPLAZA.DESCRIPTION"),
            ("IMPULSA", i_value, "IMPULSA.DESCRIPTION"),
        ):
            values[entity][account_id] = AccountValue(
                entity=entity,
                account_id=account_id,
                description=str(ws.cell(row_number, headers[description_key]).value or ""),
                value_uf=Decimal(str(raw_value)).quantize(UF_SCALE),
                source_sheet=sheet_name,
                source_row=row_number,
                source_sha256=source_hash,
            )
    return values


def calculate(
    rules: Iterable[MappingRule],
    values_by_entity: dict[str, dict[str, AccountValue]],
) -> tuple[list[Contribution], list[TargetResult], list[dict[str, str]]]:
    rules = tuple(rules)
    validate_rules(rules)
    contributions: list[Contribution] = []
    assigned = {rule.account_id for rule in rules}
    unassigned: list[dict[str, str]] = []
    for entity, values in values_by_entity.items():
        for account_id, account in sorted(values.items()):
            if account_id not in assigned:
                unassigned.append({
                    "ENTITY": entity,
                    "ACCOUNT_ID": account_id,
                    "ACCOUNT_DESCRIPTION": account.description,
                    "VALUE_UF": str(account.value_uf),
                    "STATUS": "SIN_ASIGNACION_FM",
                    "SOURCE_SHEET": account.source_sheet,
                    "SOURCE_ROW": str(account.source_row),
                })
    by_target: dict[str, list[MappingRule]] = {}
    for rule in rules:
        by_target.setdefault(rule.fm_target_id, []).append(rule)
        for entity in ("EPLAZA", "IMPULSA"):
            account = values_by_entity.get(entity, {}).get(rule.account_id)
            value = account.value_uf if account else None
            contribution = value * rule.coefficient if value is not None else None
            contributions.append(Contribution(
                mapping_id=rule.mapping_id,
                account_id=rule.account_id,
                entity=entity,
                source_value_uf=value,
                coefficient=rule.coefficient,
                contribution_uf=contribution,
                status="APPLIED" if value is not None else MISSING,
            ))
    target_lookup = {target.target_id: target for target in TARGETS}
    results: list[TargetResult] = []
    for target_id, target_rules in by_target.items():
        entity_values: dict[str, Decimal | None] = {}
        for entity in ("EPLAZA", "IMPULSA"):
            present = [
                c.contribution_uf for c in contributions
                if c.entity == entity and c.mapping_id in {r.mapping_id for r in target_rules}
                and c.contribution_uf is not None
            ]
            entity_values[entity] = sum(present, Decimal("0")) if present else None
        eplaza = entity_values["EPLAZA"]
        impulsa = entity_values["IMPULSA"]
        total = eplaza + impulsa if eplaza is not None and impulsa is not None else None
        status = "CALCULATED" if total is not None else "PARTIAL_MISSING_ENTITY_DATA"
        results.append(TargetResult(target_id, target_lookup[target_id].name, eplaza, impulsa, total, status))
    return contributions, results, unassigned


def _write_table(ws, headers: list[str], rows: list[list[object]]) -> None:
    ws.append(headers)
    for row in rows:
        ws.append(row)
    for cell in ws[1]:
        cell.font = openpyxl.styles.Font(bold=True, color="FFFFFF")
        cell.fill = openpyxl.styles.PatternFill("solid", fgColor="234A69")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for column in ws.columns:
        width = min(60, max(10, max(len(str(cell.value or "")) for cell in column) + 2))
        ws.column_dimensions[column[0].column_letter].width = width


def write_master_mapping(path: Path, rules: Iterable[MappingRule]) -> None:
    fields = [field.upper() for field in MappingRule.__dataclass_fields__]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for rule in rules:
            writer.writerow({key.upper(): value for key, value in asdict(rule).items()})


def write_target_inventory(path: Path, workbook_path: Path) -> None:
    wb = openpyxl.load_workbook(workbook_path, read_only=True, data_only=False)
    ws = wb["FM"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["FM_TARGET_CELL", "FM_TARGET_NAME", "ENTITY", "STATUS"])
        writer.writeheader()
        for locator in FM_TARGET_CELL_INVENTORY:
            _, cell = locator.split("!")
            row_number, _ = coordinate_to_tuple(cell)
            writer.writerow({
                "FM_TARGET_CELL": locator,
                "FM_TARGET_NAME": ws[f"B{row_number}"].value,
                "ENTITY": "EPLAZA" if cell.startswith("E") else "IMPULSA",
                "STATUS": "VERIFIED_PHYSICAL_TARGET",
            })


def render_conceptual_markdown(path: Path, rules: Iterable[MappingRule]) -> None:
    grouped: dict[str, list[MappingRule]] = {}
    for rule in rules:
        grouped.setdefault(rule.fm_target_id, []).append(rule)
    target_lookup = {target.target_id: target for target in TARGETS}
    lines = [
        "# KT.MovemAcc — Mapeo contable a Funding Memo",
        "",
        f"Versión de mapping: `{MAPPING_VERSION}`. Sin montos mensuales.",
        "",
        "Cada flecha representa una cuenta asignada. El signo se conserva y luego se aplica el coeficiente.",
        "",
    ]
    for target_id, target_rules in grouped.items():
        target = target_lookup[target_id]
        lines.extend((
            f"## {target.target_id} — {target.name}", "", "```mermaid", "flowchart LR",
        ))
        for rule in target_rules:
            op = "+" if rule.coefficient == 1 else "-"
            lines.append(
                f'  A{rule.account_id}["{rule.account_id} — {rule.account_description}"] -->|{op}1| T["{target.target_id} — {target.name}<br/>{target.sheet}!{target.cell_eplaza}/{target.cell_impulsa}/{target.cell_total}"]'
            )
        lines.extend(("```", ""))
    path.write_text("\n".join(lines), encoding="utf-8")


def build_funding_memo(
    *, template: Path, output: Path, period: str, consolidated: Path, raw_eplaza: Path, raw_impulsa: Path,
    mapping_csv: Path, results_json: Path, unassigned_csv: Path, conceptual_md: Path,
    decision_record: dict[str, object],
) -> dict[str, object]:
    rules = mapping_rules()
    values = load_consolidated_values(consolidated)
    contributions, results, unassigned = calculate(rules, values)
    target_inventory_csv = mapping_csv.with_name("KTMA_FM_TARGET_INVENTORY_72_V1.csv")
    for path in (output, mapping_csv, target_inventory_csv, results_json, unassigned_csv, conceptual_md):
        path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template, output)
    wb = openpyxl.load_workbook(output)
    fm = wb["FM"]
    fm.column_dimensions["B"].width = max(fm.column_dimensions["B"].width or 0, 65)
    for column in ("D", "E", "F"):
        fm.column_dimensions[column].width = max(fm.column_dimensions[column].width or 0, 16)
    target_lookup = {target.target_id: target for target in TARGETS}
    for result in results:
        target = target_lookup[result.target_id]
        fm[target.cell_eplaza] = float(result.eplaza_uf) if result.eplaza_uf is not None else None
        fm[target.cell_impulsa] = float(result.impulsa_uf) if result.impulsa_uf is not None else None
        fm[target.cell_total] = (
            f'=IF(COUNT({target.cell_eplaza}:{target.cell_impulsa})=2,{target.cell_eplaza}+{target.cell_impulsa},NA())'
        )
        for address in (target.cell_total, target.cell_eplaza, target.cell_impulsa):
            fm[address].number_format = '#,##0.00;[Red](#,##0.00);-'
    for name in ("KTMA_MAPPING", "KTMA_RESULTS", "KTMA_DECISIONS", "KTMA_UNASSIGNED"):
        if name in wb.sheetnames:
            del wb[name]
    _write_table(wb.create_sheet("KTMA_MAPPING"), list(MappingRule.__dataclass_fields__), [list(asdict(r).values()) for r in rules])
    _write_table(wb.create_sheet("KTMA_RESULTS"), list(TargetResult.__dataclass_fields__), [list(asdict(r).values()) for r in results])
    _write_table(wb.create_sheet("KTMA_DECISIONS"), list(decision_record), [list(decision_record.values())])
    _write_table(wb.create_sheet("KTMA_UNASSIGNED"), list(unassigned[0]) if unassigned else ["STATUS"], [list(r.values()) for r in unassigned] if unassigned else [["NONE"]])
    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True
    wb.save(output)
    write_master_mapping(mapping_csv, rules)
    write_target_inventory(target_inventory_csv, output)
    with unassigned_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = list(unassigned[0]) if unassigned else ["STATUS"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        if unassigned:
            writer.writerows(unassigned)
    render_conceptual_markdown(conceptual_md, rules)
    payload = {
        "period": period,
        "mapping_version": MAPPING_VERSION,
        "decision_id": DECISION_ID,
        "source_hashes": {"template": _sha256(template), "consolidated": _sha256(consolidated), "raw_eplaza": _sha256(raw_eplaza), "raw_impulsa": _sha256(raw_impulsa)},
        "output_sha256_before_excel_com": _sha256(output),
        "map_total_accounts": len(values["EPLAZA"]),
        "mapped_accounts": len(rules),
        "targets_implemented": len(results),
        "fm_targets_verified": len(FM_TARGET_CELL_INVENTORY),
        "contributions": [{k: str(v) if isinstance(v, Decimal) else v for k, v in asdict(c).items()} for c in contributions],
        "results": [{k: str(v) if isinstance(v, Decimal) else v for k, v in asdict(r).items()} for r in results],
        "unassigned_account_ids": len({row["ACCOUNT_ID"] for row in unassigned}),
        "unassigned_entity_records": len(unassigned),
        "generated_at": datetime.now().astimezone().isoformat(),
    }
    results_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
