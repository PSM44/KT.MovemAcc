"""
Non-Degradation Acceptance Contract for KT.MovemAcc Financial Workbook.

This module defines the executable contract that ensures generated workbooks
preserve all PH1 reference capabilities while allowing justified additive changes.

Contract covers:
- Accounting data integrity (UF/CLP values, debit/credit)
- Formula preservation (structural formulas, cross-sheet references)
- Hierarchy preservation (account codes, headings, semantic keys)
- Column schema compliance (required columns present and correctly typed)
- Unit integrity (UF and CLP columns with correct precision)
- Subtotal/hierarchy rollups (heading rows, account groupings)
- Audit trail (evidence JSON, source row linkages)
- Formats/navigation (structured tables, auto-filters, styles)
- References/traceability (cross-sheet provenance, JSON evidence)

Additive/equivalent changes ALLOWED:
- Additional sheets (FM Mapping, Audit, Query Table, FM Targets Summary)
- Extended columns with new metadata (Semantic Key, Source File, Evidence JSON)
- Excel 365 structured tables with filters
- Enhanced audit controls
- Funding Memo v1.0.1 compliance mappings
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ============================================================
# CONTRACT SPECIFICATION
# ============================================================

@dataclass(frozen=True)
class SheetContract:
    """Defines required structure for a worksheet."""
    name: str
    required_columns: list[str]  # Column headers that MUST exist
    required_column_types: dict[str, str]  # column -> expected type (string, number, formula, json)
    min_rows: int = 1  # Minimum data rows (excluding header)
    must_have_table: bool = True
    must_have_autofilter: bool = True
    description: str = ""
    additive_columns_allowed: list[str] = field(default_factory=list)  # Extra columns that are OK


@dataclass(frozen=True)
class CrossSheetContract:
    """Defines cross-sheet relationships that must be preserved."""
    source_sheet: str
    source_column: str
    target_sheet: str
    target_column: str
    relationship_type: str  # "provenance", "formula", "lookup"
    description: str = ""


@dataclass(frozen=True)
class NonDegradationContract:
    """Complete non-degradation contract for the workbook."""
    # Required sheets (PH1 baseline)
    required_sheets: tuple[SheetContract, ...]
    
    # Additive sheets (allowed additions)
    additive_sheets: tuple[SheetContract, ...]
    
    # Cross-sheet relationships that must be preserved
    cross_sheet_relationships: tuple[CrossSheetContract, ...]
    
    # Accounting invariants
    accounting_invariants: tuple[str, ...]  # e.g., "D = E + F", "Value = Debit - Credit"
    
    # Precision requirements
    uf_precision: int = 2  # Decimal places for UF
    clp_precision: int = 0  # Integer for CLP
    
    # Global requirements
    all_sheets_must_have_tables: bool = True
    all_tables_must_have_autofilters: bool = True
    evidence_json_column_required: bool = True


# ============================================================
# PH1 BASELINE CONTRACT DEFINITION
# ============================================================

PH1_CONTRACT = NonDegradationContract(
    required_sheets=(
        SheetContract(
            name="01_Sources_Eplaza",
            required_columns=[
                "Account Code", "Semantic Key", "Heading", "Description",
                "Debit UF", "Credit UF", "Value UF",
                "Debit CLP", "Credit CLP", "Value CLP",
                "Row Type", "Filtro", "Source Row", "Source File", "Evidence JSON"
            ],
            required_column_types={
                "Account Code": "string",
                "Semantic Key": "string",
                "Heading": "string",
                "Description": "string",
                "Debit UF": "number",
                "Credit UF": "number",
                "Value UF": "number",
                "Debit CLP": "number",
                "Credit CLP": "number",
                "Value CLP": "number",
                "Row Type": "string",
                "Filtro": "string",
                "Source Row": "number",
                "Source File": "string",
                "Evidence JSON": "string",
            },
            min_rows=280,  # ~288 rows in PH1
            must_have_table=True,
            must_have_autofilter=True,
            description="Eplaza source ledger for 2026.08",
        ),
        SheetContract(
            name="02_Sources_Impulsa",
            required_columns=[
                "Account Code", "Semantic Key", "Heading", "Description",
                "Debit UF", "Credit UF", "Value UF",
                "Debit CLP", "Credit CLP", "Value CLP",
                "Row Type", "Filtro", "Source Row", "Source File", "Evidence JSON"
            ],
            required_column_types={
                "Account Code": "string",
                "Semantic Key": "string",
                "Heading": "string",
                "Description": "string",
                "Debit UF": "number",
                "Credit UF": "number",
                "Value UF": "number",
                "Debit CLP": "number",
                "Credit CLP": "number",
                "Value CLP": "number",
                "Row Type": "string",
                "Filtro": "string",
                "Source Row": "number",
                "Source File": "string",
                "Evidence JSON": "string",
            },
            min_rows=140,  # ~143 rows in PH1
            must_have_table=True,
            must_have_autofilter=True,
            description="Impulsa source ledger for 2026.08",
        ),
        SheetContract(
            name="03_Consolidated_PH1",
            required_columns=[
                "Account Code", "Semantic Key", "Heading",
                "Eplaza Description", "Impulsa Description",
                "Eplaza Value UF", "Impulsa Value UF", "Total Value UF",
                "Eplaza Value CLP", "Impulsa Value CLP", "Total Value CLP",
                "Eplaza Source Row", "Impulsa Source Row", "Evidence JSON"
            ],
            required_column_types={
                "Account Code": "string",
                "Semantic Key": "string",
                "Heading": "string",
                "Eplaza Description": "string",
                "Impulsa Description": "string",
                "Eplaza Value UF": "number",
                "Impulsa Value UF": "number",
                "Total Value UF": "number",
                "Eplaza Value CLP": "number",
                "Impulsa Value CLP": "number",
                "Total Value CLP": "number",
                "Eplaza Source Row": "number",
                "Impulsa Source Row": "number",
                "Evidence JSON": "string",
            },
            min_rows=1500,  # Consolidated PH1 rows
            must_have_table=True,
            must_have_autofilter=True,
            description="Consolidated PH1 financial statement combining Eplaza & Impulsa",
        ),
    ),
    additive_sheets=(
        SheetContract(
            name="04_FM_Mapping",
            required_columns=[
                "Mapping ID", "Account ID", "Account Description", "Entity",
                "FM Target ID", "FM Target Name", "FM Sheet", "FM Cell Eplaza",
                "FM Cell Impulsa", "FM Cell Total", "Coefficient",
                "Eplaza Value UF", "Impulsa Value UF", "Assigned UF",
                "Eplaza Value CLP", "Impulsa Value CLP", "Assigned CLP",
                "Status", "Valid From", "Valid To", "Decision ID", "Version", "Justification"
            ],
            required_column_types={
                "Mapping ID": "string",
                "Account ID": "string",
                "Account Description": "string",
                "Entity": "string",
                "FM Target ID": "string",
                "FM Target Name": "string",
                "FM Sheet": "string",
                "FM Cell Eplaza": "string",
                "FM Cell Impulsa": "string",
                "FM Cell Total": "string",
                "Coefficient": "number",
                "Eplaza Value UF": "number",
                "Impulsa Value UF": "number",
                "Assigned UF": "number",
                "Eplaza Value CLP": "number",
                "Impulsa Value CLP": "number",
                "Assigned CLP": "number",
                "Status": "string",
                "Valid From": "string",
                "Valid To": "string",
                "Decision ID": "string",
                "Version": "string",
                "Justification": "string",
            },
            min_rows=100,
            must_have_table=True,
            must_have_autofilter=True,
            description="Funding Memo v1.0.1 account allocation mapping",
        ),
        SheetContract(
            name="05_Audit",
            required_columns=[
                "Audit Control Item", "Category", "Status", "Details", "Evidence", "Severity"
            ],
            required_column_types={
                "Audit Control Item": "string",
                "Category": "string",
                "Status": "string",
                "Details": "string",
                "Evidence": "json",
                "Severity": "string",
            },
            min_rows=10,
            must_have_table=True,
            must_have_autofilter=True,
            description="Functional audit and control verification items",
        ),
        SheetContract(
            name="06_Query_Table",
            required_columns=[
                "ID", "Entity", "Account Code", "Semantic Key", "Heading", "Description",
                "Value UF", "Value CLP", "FM Target ID", "FM Target Name", "FM Status", "Mapping Status"
            ],
            required_column_types={
                "ID": "number",
                "Entity": "string",
                "Account Code": "string",
                "Semantic Key": "string",
                "Heading": "string",
                "Description": "string",
                "Value UF": "number",
                "Value CLP": "number",
                "FM Target ID": "string",
                "FM Target Name": "string",
                "FM Status": "string",
                "Mapping Status": "string",
            },
            min_rows=1000,
            must_have_table=True,
            must_have_autofilter=True,
            description="Queryable Excel table for analytical reporting",
        ),
        SheetContract(
            name="07_FM_Targets_Summary",
            required_columns=[
                "FM Target ID", "FM Target Name", "FM Sheet", "FM Cell Eplaza",
                "FM Cell Impulsa", "FM Cell Total",
                "Eplaza Total UF", "Impulsa Total UF", "Combined Total UF",
                "Eplaza Total CLP", "Impulsa Total CLP", "Combined Total CLP",
                "Account Count", "Status"
            ],
            required_column_types={
                "FM Target ID": "string",
                "FM Target Name": "string",
                "FM Sheet": "string",
                "FM Cell Eplaza": "string",
                "FM Cell Impulsa": "string",
                "FM Cell Total": "string",
                "Eplaza Total UF": "number",
                "Impulsa Total UF": "number",
                "Combined Total UF": "number",
                "Eplaza Total CLP": "number",
                "Impulsa Total CLP": "number",
                "Combined Total CLP": "number",
                "Account Count": "number",
                "Status": "string",
            },
            min_rows=15,
            must_have_table=True,
            must_have_autofilter=True,
            description="High-level Funding Memo targets summary",
        ),
    ),
    cross_sheet_relationships=(
        CrossSheetContract(
            source_sheet="01_Eplaza_Source",
            source_column="Source Row",
            target_sheet="03_Consolidated_PH1",
            target_column="Eplaza Source Row",
            relationship_type="provenance",
            description="Eplaza source row linkage for audit traceability"
        ),
        CrossSheetContract(
            source_sheet="02_Impulsa_Source",
            source_column="Source Row",
            target_sheet="03_Consolidated_PH1",
            target_column="Impulsa Source Row",
            relationship_type="provenance",
            description="Impulsa source row linkage for audit traceability"
        ),
        CrossSheetContract(
            source_sheet="03_Consolidated_PH1",
            source_column="Account Code",
            target_sheet="04_FM_Mapping",
            target_column="Account ID",
            relationship_type="lookup",
            description="Consolidated accounts mapped to FM targets"
        ),
        CrossSheetContract(
            source_sheet="03_Consolidated_PH1",
            source_column="Account Code",
            target_sheet="06_Query_Table",
            target_column="Account Code",
            relationship_type="lookup",
            description="Consolidated accounts available in query table"
        ),
    ),
    accounting_invariants=(
        "Total Value UF = Eplaza Value UF + Impulsa Value UF",
        "Total Value CLP = Eplaza Value CLP + Impulsa Value CLP",
        "Value UF = Debit UF - Credit UF (per source row)",
        "Value CLP = Debit CLP - Credit CLP (per source row)",
        "FM Target Total = Eplaza Assigned + Impulsa Assigned (D = E + F)",
    ),
    uf_precision=2,
    clp_precision=0,
    all_sheets_must_have_tables=True,
    all_tables_must_have_autofilters=True,
    evidence_json_column_required=True,
)


def get_contract() -> NonDegradationContract:
    """Return the PH1 baseline non-degradation contract."""
    return PH1_CONTRACT


def serialize_contract(contract: NonDegradationContract, output_path: Path) -> None:
    """Serialize contract to JSON for documentation/versioning."""
    data = {
        "required_sheets": [
            {
                "name": s.name,
                "required_columns": s.required_columns,
                "required_column_types": s.required_column_types,
                "min_rows": s.min_rows,
                "must_have_table": s.must_have_table,
                "must_have_autofilter": s.must_have_autofilter,
                "description": s.description,
                "additive_columns_allowed": s.additive_columns_allowed,
            }
            for s in contract.required_sheets
        ],
        "additive_sheets": [
            {
                "name": s.name,
                "required_columns": s.required_columns,
                "required_column_types": s.required_column_types,
                "min_rows": s.min_rows,
                "must_have_table": s.must_have_table,
                "must_have_autofilter": s.must_have_autofilter,
                "description": s.description,
                "additive_columns_allowed": s.additive_columns_allowed,
            }
            for s in contract.additive_sheets
        ],
        "cross_sheet_relationships": [
            {
                "source_sheet": r.source_sheet,
                "source_column": r.source_column,
                "target_sheet": r.target_sheet,
                "target_column": r.target_column,
                "relationship_type": r.relationship_type,
                "description": r.description,
            }
            for r in contract.cross_sheet_relationships
        ],
        "accounting_invariants": list(contract.accounting_invariants),
        "uf_precision": contract.uf_precision,
        "clp_precision": contract.clp_precision,
        "all_sheets_must_have_tables": contract.all_sheets_must_have_tables,
        "all_tables_must_have_autofilters": contract.all_tables_must_have_autofilters,
        "evidence_json_column_required": contract.evidence_json_column_required,
    }
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    # Generate contract documentation
    serialize_contract(PH1_CONTRACT, Path("09_REVIEW/KTMA_WORKBOOK_001/non_degradation_contract.json"))
    print("Non-degradation contract serialized to non_degradation_contract.json")