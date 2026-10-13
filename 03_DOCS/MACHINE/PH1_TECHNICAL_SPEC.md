# PH1 Technical Specification

## Scope
PH1 ingests the EPLAZA and IMPULSA August 2026 XLSB CUENTAS DE MAYOR sheets and produces one XLSX workbook at `OUTPUT/<period>/CAM<period>_CONSOL.ALIGN.xlsx`.

PH1 does not create PH2 criteria sheets, Funding Memo sheets, macros, external links, or Excel Desktop recalculation evidence.

## Source Contract
The engine reads the first sheet whose name matches `CUENTAS DE MAYOR`. The canonical physical columns are:

| Column | Field |
| --- | --- |
| A | FILTRO |
| B | ACCOUNT_CODE |
| C | HEADING / TITLE |
| D | ACCOUNT_DESCRIPTION |
| E | DEBITOS_UF |
| F | CREDITOS_UF |
| G | VALORES UF |
| H | DEBITOS_CLP |
| I | CREDITOS_CLP |
| J | VALORES $$ |

Account codes must be 5 to 8 digit strings. Code-less rows are preserved as headings/titles. Zero-value accounts are retained.

## Output Contract
The workbook must contain exactly:

1. `CAM<period>_CONSOL.ALIGN`
2. `CM<period>_EPLAZA`
3. `CM<period>_IMPULSA`
4. `AUDIT.PH1`
5. `CONTROL`

CM sheets preserve the financial A:J layout and add K `VISIBILIDAD_UF` for UF-only presentation filtering. `MOSTRAR` is applied to nonzero UF account/group rows and auditable ambiguous hierarchy rows; `OCULTAR` is presentation-only and never deletes records. CAM exposes these canonical business fields:

- `EPLAZA.VALORES_UF`
- `IMPULSA.VALORES_UF`
- `TOTAL.VALORES_UF`
- `EPLAZA.VALORES_CLP`
- `IMPULSA.VALORES_CLP`
- `TOTAL.VALORES_CLP`

CAM does not expose `BALANCE_UF` or `BALANCE_CLP`.

## Alignment
Leaf accounts align by stable account code. If both companies have the same code but different descriptions, the account is aligned financially and the description conflict is recorded in `AUDIT.PH1`.

Code-less headings are keyed by normalized heading text plus occurrence count. This prevents repeated labels such as `VALORES NEGOCIABLES` from being merged solely by text.

## Formula Generation
CM subtotal formulas are generated only when source-derived leaf account membership reconciles to the source heading values within tolerance:

- UF tolerance: `0.05`
- CLP tolerance: `1`

The engine first tests the immediate account block after a heading. If needed, it scans forward for the smallest leaf-account range that reconciles to the source heading. If no source-backed membership is found, the source heading values are preserved and an `AMBIGUOUS_HIERARCHY` or `SOURCE_SUBTOTAL_DIFF` audit row is written.

CAM horizontal totals are formulas (`EPLAZA + IMPULSA`). CAM account rows compute horizontal totals directly. CAM heading/title rows use hierarchical subtotal formulas over direct child headings/accounts to avoid double counting; the HUMAN-accepted August baseline has 54 CAM headings with formulas.

## Reconciliation And Provenance
The engine records:

- Source row counts and account counts.
- Zero-account counts.
- Subtotal formula count.
- Unresolved hierarchy count.
- Source SHA-256 hashes.
- XLSX package/formula integrity.
- Excel Desktop validation status.

Current observed August 2026 metrics:

- EPLAZA accounts: `214`
- IMPULSA accounts: `100`
- CAM accounts: `253`
- XML formula cells: `1205`
- XML broken references: `0`
- Empty `SUM()`: `0`
- Approved criteria: `15/15` verified for August 2026.
- Historical hierarchy exceptions: `14/14` resolved for August 2026.
- CAM headings with hierarchical formulas: `54/54`.
- Regression tests: `16` passing.
- Excel Desktop COM recalculation: PASS in TASK033R evidence.

Current PH1 status for the August 2026 HUMAN-accepted baseline is technically verified and functionally accepted by HUMAN. Future periods still require their own reconciliation and acceptance; this document does not certify future accounting periods automatically.

## Approved PH1 Criteria

HUMAN–MORCH approved CR-001 through CR-015 are stored in `04_CONFIG/CRITERIA/PH1_CRITERIA_REGISTER.json`. Historical cell addresses are evidence; runtime matching must use stable account codes and hierarchy-aware identifiers where implemented. PH2/Funding Memo criteria remain out of scope.
