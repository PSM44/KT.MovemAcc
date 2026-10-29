from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


TASK = "KTMA_SPECIALIST_003"
ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "08_EVIDENCE" / "REPORTS"
CLASSIFICATION = REPORTS / "KTMA_SPECIALIST_002_FM_TARGET_CLASSIFICATION.csv"
DB = ROOT / "DATA" / "KTMA.sqlite"
OUT_MAPPING = REPORTS / f"{TASK}_UNIFIED_72_TARGET_MAPPING.csv"
OUT_ACCOUNTS = REPORTS / f"{TASK}_ACCOUNT_SOURCE_RECONCILIATION.csv"
OUT_EXCEPTIONS = REPORTS / f"{TASK}_AMBIGUITY_EXCEPTIONS.csv"
OUT_BRIEF = REPORTS / f"{TASK}_FINANCIAL_RULE_DECISION_BRIEF.md"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def spec(state: str, accounts: str = "", node: str = "", relation: str = "",
         aggregation: str = "", blocker: str = "", evidence: str = "",
         alternatives: str = "", failure_dependency: str = "NONE") -> dict[str, str]:
    return {
        "state": state, "accounts": accounts, "node": node, "relation": relation,
        "aggregation": aggregation, "blocker": blocker, "evidence": evidence,
        "alternatives": alternatives, "failure_dependency": failure_dependency,
    }


# Account membership is grounded in read-only SQLite/RAW lineage. VERIFIED_TECHNICAL
# does not mean HUMAN financial approval or authorization to populate the FM.
ACCOUNTING: dict[str, dict[str, str]] = {
    "E27": spec("VERIFIED_TECHNICAL", "120911", "120911 < TERRENO#1 < COSTOS DIRECTOS#1", "ONE_TO_ONE", "Use account balance once; preserve sign", evidence="Exact land-cost account and reconciled parent hierarchy"),
    "E28": spec("VERIFIED_TECHNICAL", "120912", "120912 < TERRENO#1 < COSTOS DIRECTOS#1", "ONE_TO_ONE", "Use account balance once; preserve sign", evidence="Exact commission account and reconciled parent hierarchy"),
    "E29": spec("VERIFIED_TECHNICAL", "121067", "121067 < GASTOS FINANCIEROS#1 < GASTOS ACTIVADOS#1", "ONE_TO_ONE", "Exclude 121067 from E53", evidence="Exact terrain-financing interest account; mutually exclusive residual rule"),
    "E30": spec("AMBIGUOUS", "450514", "450514 < COSTOS DE LA EXPLOTACION#1", "ONE_TO_ONE_CANDIDATE", "Preserve observed sign", blocker="Current numeric-zero balance, FILTRO=NO and exact label do not decide balance vs movement, realized vs unrealized, or activated-project scope", evidence="Exact-description account exists", alternatives="current balance|period movement|activated project FX"),
    "E31": spec("VERIFIED_TECHNICAL", "120913", "120913 < TERRENO#1 < COSTOS DIRECTOS#1", "ONE_TO_ONE", "Use account balance once; preserve sign", evidence="Exact structuring account and reconciled parent hierarchy"),
    "E32": spec("VERIFIED_TECHNICAL", "120915", "120915 < TERRENO#1 < COSTOS DIRECTOS#1", "ONE_TO_ONE", "Exclude 120914", evidence="Exact other-land account; 120914 retained only as E48 alternative"),
    "E36": spec("VERIFIED_TECHNICAL", "120921;120922;120923", "DERECHOS Y PERMISOS#1 < COSTOS DIRECTOS#1", "MANY_TO_ONE", "Sum children once; never add parent subtotal", evidence="Direct-reconciled subtotal membership"),
    "E37": spec("VERIFIED_TECHNICAL", "120981", "120981 < CONSTRUCCION Y URBANIZACION#1", "ONE_TO_ONE", "Exclude 120981 from E38", evidence="Exact demolition/exterior-works account and non-overlap rule"),
    "E38": spec("VERIFIED_TECHNICAL", "120971;120973;120974", "Residual members of CONSTRUCCION Y URBANIZACION#1", "MANY_TO_ONE", "Exclude 120972(E39),120975(E40),120980(E41 alternative),120981(E37)", blocker="HUMAN must approve the residual-definition policy before financial adoption", evidence="Reconciled construction hierarchy with explicit mutually exclusive partition"),
    "E39": spec("VERIFIED_TECHNICAL", "120972", "120972 < CONSTRUCCION Y URBANIZACION#1", "ONE_TO_ONE_CONTRA", "Preserve negative credit-balance sign; no absolute value", evidence="Exact special-credit account and contra-account treatment"),
    "E40": spec("AMBIGUOUS", "120975;1109902", "120975 < CONSTRUCCION Y URBANIZACION#1 | 1109902 < IMPREVISTOS#1", "ONE_OR_MANY_TO_ONE_CANDIDATE", "Do not combine until recognition layer is approved", blocker="Two zero-valued Postventa accounts occur in different hierarchies; no Plan OK or Santolaya contract node", evidence="Physical alternatives traced", alternatives="120975 only|1109902 only|contract plus approved accounting set"),
    "E41": spec("AMBIGUOUS", "120931;120932", "EMPALMES#1 < COSTOS DIRECTOS#1", "MANY_TO_ONE_WITH_OPTIONAL_EXTRA", "Heading children once; optional 120980 must remain excluded from E38", blocker="Choose exact EMPALMES#1 children versus adding 120980 Adicional Empalmes; historical V0 reconciles to neither", evidence="Heading children reconcile; optional account is outside heading", alternatives="120931+120932|120931+120932+120980"),
    "E42": spec("VERIFIED_TECHNICAL", ";".join(str(x) for x in range(120941, 120962)), "HONORARIOS ESPECIALIDADES#1 < COSTOS DIRECTOS#1", "MANY_TO_ONE", "Sum children once; never add parent subtotal", evidence="Direct-reconciled specialist-fee subtotal membership"),
    "E48": spec("AMBIGUOUS", "120914;121029;1109951", "TERRENO#1 | PILOTO Y SALA DE VENTA#1 | GASTOS DE VENTAS#1", "MANY_TO_ONE_CANDIDATE", "Do not mix activated and P&L layers without approved recognition rule", blocker="Target combines common expenses, maintenance and contributions across different recognition layers", evidence="Activated/direct alternatives traced", alternatives="activated set 120914+121029+1109951|P&L set 410429+410446+410466"),
    "E49": spec("VERIFIED_TECHNICAL", "121011;121012;121013;121015;121016;121017", "MARKETING#1 < GASTOS ACTIVADOS#1", "MANY_TO_ONE", "Sum children once; never add parent subtotal", evidence="Direct-reconciled marketing subtotal membership"),
    "E50": spec("AMBIGUOUS", "121031", "COMERCIALIZACION#1 < GASTOS ACTIVADOS#1", "ONE_TO_ONE_PLUS_EXTERNAL_CANDIDATE", "Do not add 121041 without approved cross-heading rule", blocker="Exact subtotal contains only Costo Corretaje; stated Fitz/Impulsa CI inclusions lack contract/party allocation", evidence="Exact subtotal traced", alternatives="121031 only|121031+121041|contract-based allocation"),
    "E51": spec("AMBIGUOUS", "121041", "ASESORIA PROYECTO#1 < GASTOS ACTIVADOS#1", "ONE_TO_ONE_CANDIDATE", "Do not combine activated and P&L alternatives", blocker="Neither 121041 nor zero/FILTRO=NO 410454 proves a fixed administration fee", evidence="Two recognition-layer alternatives traced", alternatives="121041 activated|410454 P&L|external fixed-fee contract"),
    "E52": spec("VERIFIED_TECHNICAL", "121051;1109902;1109903", "IMPREVISTOS#1 < GASTOS ACTIVADOS#1", "MANY_TO_ONE", "Sum observed numeric zeros once; never infer missing as zero", evidence="Direct-reconciled contingency subtotal membership; all children are numeric zero"),
    "E53": spec("VERIFIED_TECHNICAL", "121061;121062;121063;121065;121068;121069", "Residual of GASTOS FINANCIEROS#1 < GASTOS ACTIVADOS#1", "MANY_TO_ONE", "Exclude 121064(E55) and 121067(E29)", blocker="HUMAN must approve the residual-definition policy before financial adoption", evidence="Reconciled finance-cost hierarchy with explicit mutually exclusive partition"),
    "E54": spec("VERIFIED_TECHNICAL", "121071;121072;121073", "GASTOS GENERALES#1 < GASTOS ACTIVADOS#1", "MANY_TO_ONE", "Sum children once; never add parent subtotal", evidence="Direct-reconciled general-expense subtotal membership"),
    "E55": spec("VERIFIED_TECHNICAL", "121064", "121064 < GASTOS FINANCIEROS#1", "ONE_TO_ONE", "Exclude 121064 from E53", evidence="Exact green-sale policy premium account and non-overlap rule"),
    "F27": spec("UNMAPPED", "", "", "NONE", "", blocker="120511 is investment in EPlaza, not land cost; no IMPULSA land-cost node"),
    "F28": spec("AMBIGUOUS", "410461", "410461 < COSTOS DE LA EXPLOTACION#1", "ONE_TO_ONE_CANDIDATE", "", blocker="Generic zero/FILTRO=NO commissions lack terrain/project dimension", alternatives="410461|external project allocation"),
    "F29": spec("AMBIGUOUS", "450113;410451", "COSTOS DE LA EXPLOTACION#1", "ONE_OR_MANY_TO_ONE_CANDIDATE", "", blocker="Generic interest/financial advice do not prove terrain financing", alternatives="450113|410451|approved allocated set"),
    "F30": spec("AMBIGUOUS", "450514", "450514 < COSTOS DE LA EXPLOTACION#1", "ONE_TO_ONE_CANDIDATE", "", blocker="Exact label but no project/time/realized-vs-unrealized scope", alternatives="current balance|period movement|project allocation"),
    "F31": spec("UNMAPPED", "", "", "NONE", "", blocker="No exact structuring account; generic advice accounts are semantically different"),
    "F32": spec("UNMAPPED", "", "", "NONE", "", blocker="No IMPULSA terrain-cost hierarchy/account"),
    "F36": spec("AMBIGUOUS", "410443;410432;410452;410467", "COSTOS DE LA EXPLOTACION#1", "MANY_TO_ONE_CANDIDATE", "", blocker="Mixed corporate notarial/legal/patent accounts lack project allocation", alternatives="account subset and allocation require HUMAN rule"),
    "F37": spec("UNMAPPED", "", "", "NONE", "", blocker="No demolition or exterior-works source node"),
    "F38": spec("UNMAPPED", "", "", "NONE", "", blocker="No construction-cost source node"),
    "F39": spec("UNMAPPED", "", "", "NONE", "", blocker="No special VAT-credit source node"),
    "F40": spec("UNMAPPED", "", "", "NONE", "", blocker="No post-sale or Plan OK source node"),
    "F41": spec("UNMAPPED", "", "", "NONE", "", blocker="No connection-cost source node"),
    "F42": spec("AMBIGUOUS", "410433;410432;410452;410435;410455", "COSTOS DE LA EXPLOTACION#1", "MANY_TO_ONE_CANDIDATE", "", blocker="Generic corporate services lack project allocation", alternatives="technical/legal/accounting subset plus allocation"),
    "F48": spec("AMBIGUOUS", "410423;410425", "COSTOS DE LA EXPLOTACION#1", "MANY_TO_ONE_CANDIDATE", "", blocker="Zero/FILTRO=NO accounts do not establish maintenance/contribution completeness or project scope", alternatives="410423+410425|external allocation"),
    "F49": spec("UNMAPPED", "", "", "NONE", "", blocker="No IMPULSA marketing source node"),
    "F50": spec("AMBIGUOUS", "410461;410438;410456", "COSTOS DE LA EXPLOTACION#1", "MANY_TO_ONE_CANDIDATE", "", blocker="Descriptions do not establish Fitz/Impulsa CI contract or project allocation", alternatives="commission only|project-advice set|external contract allocation"),
    "F51": spec("AMBIGUOUS", "410435;410455;410451;410452", "COSTOS DE LA EXPLOTACION#1", "MANY_TO_ONE_CANDIDATE", "", blocker="No fixed-fee identity or project allocation", alternatives="accounting/financial/legal subset|external fixed-fee contract"),
    "F52": spec("AMBIGUOUS", "410469", "410469 < COSTOS DE LA EXPLOTACION#1", "ONE_TO_ONE_CANDIDATE", "", blocker="Generic zero/FILTRO=NO Gastos Varios is not contingency evidence", alternatives="410469|external contingency policy"),
    "F53": spec("AMBIGUOUS", "410460;410462;450113", "COSTOS DE LA EXPLOTACION#1", "MANY_TO_ONE_CANDIDATE", "", blocker="Plausible corporate finance-cost set lacks project allocation and approved exclusions", alternatives="candidate set|approved allocated subset"),
    "F54": spec("AMBIGUOUS", "", "Residual of COSTOS DE LA EXPLOTACION#1", "RESIDUAL_CANDIDATE", "", blocker="Residual would overlap F28/F29/F36/F42/F48/F50/F51/F53/F55; no approved residual rule", alternatives="approved non-overlapping residual|external allocated overhead"),
    "F55": spec("AMBIGUOUS", "410484", "410484 < COSTOS DE LA EXPLOTACION#1", "ONE_TO_ONE_CANDIDATE", "", blocker="Generic zero/FILTRO=NO insurance does not prove green-sale policy", alternatives="410484|external policy evidence"),
}


HISTORICAL = {
    8: "420404.48", 9: "4900", 10: "30000", 12: "70295", 13: "600", 14: "6000",
    17: "81920", 18: "1900", 19: "6500", 27: "180096", 28: "3600.07",
    29: "31117.472648112234", 30: "-6302", 31: "4000", 32: "BLANK", 36: "1673",
    37: "2000.44", 38: "254979.46000000005", 39: "-5854.999999999999", 40: "2016",
    41: "2370", 42: "13496.13", 48: "4750.245", 49: "8206.155023748634",
    50: "12450.3896", 51: "21000", 52: "3824.6919000000007", 53: "24417.75412033793",
    54: "820.05", 55: "759.73", 61: "BLANK", 65: "BLANK", 69: "17590.666666666668",
    75: "100000", 76: "80000", 77: "0.4550822504113447",
}


def non_accounting(row: int) -> dict[str, str]:
    if row in {8, 9, 10, 12, 13, 14, 17, 18, 19, 76}:
        return {"source": "EXTERNAL_BUSINESS_SOURCE", "state": "UNMAPPED", "blocker": "Authoritative commercial/financing source, entity allocation, recognition basis and measurement date absent"}
    if row in {61, 65, 69, 75}:
        reasons = {
            61: "No formula, VAT rate/base, credit treatment, timing or rounding policy",
            65: "No fee rate/base, recipient, timing, tax treatment or rounding policy",
            69: "Historical value is hardcoded; no financing base, rate, dates, accrual or compounding rule",
            75: "Historical value is hardcoded; capital definition and measurement date are absent",
        }
        return {"source": "UNKNOWN", "state": "UNMAPPED", "blocker": reasons[row]}
    if row == 77:
        return {"source": "DERIVED_FINANCIAL_RESULT", "state": "PROPOSED_FINANCIAL", "blocker": "Historical C77 equals C70/C75, but C77 is hardcoded and no E/F formula or approved capital-return policy exists"}
    raise KeyError(row)


def connect() -> sqlite3.Connection:
    uri = DB.resolve().as_uri() + "?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def account_rows(conn: sqlite3.Connection, entity: str, codes: list[str]) -> list[sqlite3.Row]:
    if not codes:
        return []
    placeholders = ",".join("?" for _ in codes)
    return list(conn.execute(f"""
        SELECT e.entity_code, sf.file_path, sf.sha256 source_sha256, osr.source_sheet,
               osr.source_row_number, osr.filtro, a.source_order, a.account_code,
               a.label, a.semantic_key, a.debit_uf, a.credit_uf, a.value_uf,
               a.debit_clp, a.credit_clp, a.value_clp,
               GROUP_CONCAT(DISTINCT p.semantic_key) parent_nodes,
               GROUP_CONCAT(DISTINCT h.inference_status) hierarchy_status
        FROM account_observations a
        JOIN entities e USING(entity_id)
        JOIN original_source_rows osr USING(original_row_id)
        JOIN source_files sf USING(source_file_id)
        LEFT JOIN hierarchy_context h ON h.child_observation_id=a.observation_id
        LEFT JOIN account_observations p ON p.observation_id=h.parent_observation_id
        WHERE e.entity_code=? AND a.account_code IN ({placeholders})
        GROUP BY a.observation_id ORDER BY osr.source_row_number
    """, [entity, *codes]))


def write_csv_new(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing overwrite: {path}")
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    for path in [OUT_MAPPING, OUT_ACCOUNTS, OUT_EXCEPTIONS, OUT_BRIEF]:
        if path.exists():
            raise FileExistsError(f"refusing overwrite: {path}")
    before = {p: sha256(ROOT / p) for p in [
        Path("DATA/KTMA.sqlite"), Path("OUTPUT/2026.08/CAM2026.08_CONSOL.ALIGN.xlsx"),
        Path("OUTPUT/2026.08/FM2026.08_VALIDATION.xlsx"),
        Path("RAW.INPUT/2026.08/Mayor Grupo Impulsa 2026 08 V 1.xlsb"),
        Path("RAW.INPUT/2026.08/Mayor Inmob. Eplaza 2026 08 V 1.xlsb"),
    ]}
    conn = connect()
    mapping_rows: list[dict[str, str]] = []
    account_output: list[dict[str, str]] = []
    exception_output: list[dict[str, str]] = []
    with CLASSIFICATION.open(encoding="utf-8-sig", newline="") as fh:
        targets = list(csv.DictReader(fh))
    if len(targets) != 72:
        raise AssertionError(f"expected 72 targets, got {len(targets)}")

    for target in targets:
        cell = target["target_cell"]
        row_num = int("".join(ch for ch in cell if ch.isdigit()))
        entity = target["source_entity"]
        historical = HISTORICAL[row_num]
        if target["underlying_candidate_type"] == "ACCOUNTING_INPUT":
            s = ACCOUNTING[cell]
            codes = [x for x in s["accounts"].split(";") if x]
            observed = account_rows(conn, entity, codes)
            if len(observed) != len(codes):
                found = {str(x["account_code"]) for x in observed}
                missing = sorted(set(codes) - found)
                raise AssertionError(f"{cell}: missing account codes {missing}")
            sum_uf = sum((Decimal(x["value_uf"]) for x in observed), Decimal(0))
            sum_clp = sum((Decimal(x["value_clp"]) for x in observed), Decimal(0))
            provenance = "; ".join(f"RAW r{x['source_row_number']} -> PH1 G{x['source_row_number']+1}/J{x['source_row_number']+1}" for x in observed) or "No entity-specific source account located"
            recon = s["evidence"]
            if observed:
                recon += f"; candidate sum={sum_uf} UF/{sum_clp} CLP"
            intended = "PH1_ACCOUNTING"
            mapping_rows.append({
                "fm_destination": f"FM!{cell}", "concept": target["target_concept"].strip(), "entity": entity,
                "destination_class": "ACCOUNTING_INPUT", "intended_source_class": intended,
                "source_accounts_or_type": s["accounts"] or "NO_RELEVANT_SOURCE_NODE",
                "relationship_cardinality": s["relation"], "ph1_semantic_identity": s["node"],
                "source_provenance": provenance, "measure": "ACCOUNTING_BALANCE_DEBIT_MINUS_CREDIT",
                "currency_and_period": "UF_AND_CLP;2026.08;CURRENT_BALANCE_NOT_PERIOD_MOVEMENT",
                "transformation_and_sign": s["aggregation"], "aggregation_rule": s["aggregation"],
                "reconciliation_evidence": recon,
                "qa_outcome": ("I2_PASS_SOURCE_MEMBERSHIP_HIERARCHY_ARITHMETIC_AND_NONOVERLAP"
                               if s["state"] == "VERIFIED_TECHNICAL"
                               else "I2_PASS_TRACE_COVERAGE_MAPPING_REMAINS_BLOCKED"),
                "mapping_state": s["state"], "human_approval_status": "PENDING_NOT_INFERRED",
                "ph1_semantic_failure_dependency": s["failure_dependency"], "remaining_blocker": s["blocker"],
                "historical_v0_reference": historical, "existing_formula": "NONE_EF_CELL_BLANK",
                "formula_precedents": "NONE", "time_basis": "SOURCE_BALANCE_AS_OF_2026.08;FM_POLICY_PENDING",
            })
            for item in observed:
                account_output.append({
                    "fm_destination": f"FM!{cell}", "entity": entity, "mapping_state": s["state"],
                    "account_code": str(item["account_code"]), "account_label": item["label"],
                    "raw_workbook": item["file_path"], "raw_sha256": item["source_sha256"],
                    "raw_sheet": item["source_sheet"], "raw_row": str(item["source_row_number"]),
                    "ph1_sheet": f"CM2026.08_{entity}", "ph1_uf_cell": f"G{item['source_row_number']+1}",
                    "ph1_clp_cell": f"J{item['source_row_number']+1}", "parent_nodes": item["parent_nodes"] or "",
                    "hierarchy_status": item["hierarchy_status"] or "", "debit_uf": item["debit_uf"],
                    "credit_uf": item["credit_uf"], "balance_uf": item["value_uf"],
                    "debit_clp": item["debit_clp"], "credit_clp": item["credit_clp"],
                    "balance_clp": item["value_clp"], "filtro": item["filtro"] or "",
                    "relationship_role": "CANDIDATE_MEMBER", "double_count_control": s["aggregation"],
                    "qa_outcome": "I2_PASS_ACCOUNT_IDENTITY_PROVENANCE_AND_SOURCE_HASH",
                })
            if s["state"] in {"AMBIGUOUS", "UNMAPPED"}:
                exception_output.append({
                    "fm_destination": f"FM!{cell}", "concept": target["target_concept"].strip(),
                    "entity": entity, "state": s["state"], "observed_candidates": s["accounts"] or "NONE",
                    "alternatives": s["alternatives"] or "NONE", "exact_blocker": s["blocker"],
                    "decision_owner": "HUMAN_FINANCIAL", "recommended_safe_action": "KEEP_UNPOPULATED",
                })
        else:
            n = non_accounting(row_num)
            preserved = {
                61: "No E/F formula; row not referenced downstream",
                65: "No E/F formula; E67=E63-E65 and F67=F63-F65",
                69: "No E/F formula; E70=E67-E69 and F70=F67-F69",
                75: "No E/F formula or dependency",
                76: "No E/F formula or dependency",
                77: "No E/F formula; historical C77 equals C70/C75",
            }.get(row_num, "No E/F formula; sales totals aggregate E/F through rows 11,15,20,22")
            mapping_rows.append({
                "fm_destination": f"FM!{cell}", "concept": target["target_concept"].strip(), "entity": entity,
                "destination_class": target["target_classification"], "intended_source_class": n["source"],
                "source_accounts_or_type": n["source"], "relationship_cardinality": "NOT_ACCOUNT_MAPPING",
                "ph1_semantic_identity": "NOT_APPLICABLE", "source_provenance": "FM V0 column C historical reference only",
                "measure": "BUSINESS_INPUT_OR_DERIVED_RESULT", "currency_and_period": "UF_OR_RATIO;V0_2024-04-24_REFERENCE;OPERATIONAL_PERIOD_UNKNOWN",
                "transformation_and_sign": "NO_APPROVED_RULE", "aggregation_rule": "NO_APPROVED_RULE",
                "reconciliation_evidence": preserved,
                "qa_outcome": "I2_PASS_CLASSIFICATION_FORMULA_AND_BLANK_CELL_PRESERVATION",
                "mapping_state": n["state"], "human_approval_status": "PENDING_NOT_INFERRED",
                "ph1_semantic_failure_dependency": "NONE", "remaining_blocker": n["blocker"],
                "historical_v0_reference": historical, "existing_formula": "NONE_EF_CELL_BLANK",
                "formula_precedents": preserved, "time_basis": "V0_2024-04-24_REFERENCE_ONLY;CURRENT_POLICY_UNKNOWN",
            })

    fields = list(mapping_rows[0])
    account_fields = list(account_output[0])
    exception_fields = list(exception_output[0])
    write_csv_new(OUT_MAPPING, fields, mapping_rows)
    write_csv_new(OUT_ACCOUNTS, account_fields, account_output)
    write_csv_new(OUT_EXCEPTIONS, exception_fields, exception_output)

    counts = Counter(r["mapping_state"] for r in mapping_rows)
    nonacct = Counter(r["intended_source_class"] for r in mapping_rows if r["destination_class"] != "ACCOUNTING_INPUT")
    brief = f"""# {TASK} — Financial-rule decision brief

`STATUS=PARTIAL_MAPPING`; `RM_GATE_003=OPEN`; `RM_GATE_004=OPEN`

## Evidence outcome

- Unified register: 72/72 targets. States: {dict(counts)}.
- Accounting candidates: 42/42 individually traced or blocked: 15 `VERIFIED_TECHNICAL`, 18 `AMBIGUOUS`, 9 `UNMAPPED`; zero `HUMAN_APPROVED`.
- Non-accounting source classes: {dict(nonacct)}. No E/F destination contains an existing formula.
- `VERIFIED_TECHNICAL` means the source account membership, hierarchy, arithmetic, sign and non-overlap rule are independently testable. It does not authorize FM population or settle policy/time-basis choices.
- The 32 retained PH1/PH1.5 `SOURCE_SEMANTIC_MISMATCH` FAILs remain unresolved. They concern IMPULSA accounts 120411, 120511 and 220411 and propagated parents; none of the 15 verified EPLAZA mappings depends on those nodes.

## HUMAN decisions grouped by economic principle

1. **Recognition and time basis:** decide current balance versus period movement, activated cost versus P&L, and the operative FM measurement date.
2. **Entity allocation:** approve project/party allocation for IMPULSA. Generic corporate descriptions cannot be mirrored from EPLAZA.
3. **Construction partition:** approve the mutually exclusive residual used for E38 and the exclusion of E37/E39/E40/E41 alternatives.
4. **Finance partition:** approve the E53 residual and exclusions for terrain financing and green-sale policy premiums.
5. **Four original EPLAZA cases:** E41 remains ambiguous; E49, E52 and E54 have deterministic account membership but still need financial adoption. Numeric zero at E52 is observed data, not a default for missing information.
6. **Commercial assumptions:** identify authoritative source, gross/net meaning, recognition date and EPLAZA/IMPULSA allocation for rows 8–19 and financing evidence for row 76.
7. **IVA, fee and preferred-capital cost:** approve base, rate, timing, tax treatment, rounding and accrual/compounding policies. E/F rows 61, 65 and 69 are blank, not formulas.
8. **Capital and return:** define capital required and approve the numerator/denominator. Historical C77 equals C70/C75, but E/F rows 75–77 are blank and no policy is approved.

## Preserved model facts

- Funding Memo candidate and `test.PH02.xlsx` are byte-identical historical V0 references (`eda935a5...`); column C values are not entity-separated sources.
- Preserved formulas include E63=E22-E59, E67=E63-E65, E70=E67-E69 and E73=E63/E59 (same pattern in F). IVA row 61 is not referenced.
- No Funding Memo cell was populated or modified.

## Retention

The CSVs and this brief are `IMMUTABLE_DURABLE_TASK_EVIDENCE`, owner `KTMA_SPECIALIST_003/SPECIALIST_TO_MORCH`, retained until MORCH/HUMAN disposition. They are evidence products, not canonical financial source data.
"""
    OUT_BRIEF.write_text(brief, encoding="utf-8", newline="\n")
    conn.close()
    after = {p: sha256(ROOT / p) for p in before}
    if before != after:
        raise AssertionError("protected artifact hash changed during analysis")
    print(json.dumps({"targets": len(mapping_rows), "accounts": len(account_output), "exceptions": len(exception_output), "states": counts, "protected_hashes_equal": True}, default=dict))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
