# Motor de mapeo contable a Funding Memo

El comando crea un directorio nuevo y no sobrescribe el Funding Memo fuente ni `RAW.INPUT`.

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONPATH = 'src'
& '90_RUNTIME\venv_win\Scripts\python.exe' -B -m kt_movemacc.cli funding-memo `
  --period 2026.09 `
  --root . `
  --template 'OUTPUT\2026.08\FM2026.08_VALIDATION.xlsx' `
  --consolidated '90_RUNTIME\PH1_REVIEW\2026.09\RUN_002\CAM2026.09_CONSOL.ALIGN.xlsx' `
  --raw-eplaza 'RAW.INPUT\2026.09\Mayor Inmob. Eplaza 2026 09 V 1.xlsb' `
  --raw-impulsa 'RAW.INPUT\2026.09\Mayor Grupo Impulsa 2026 09 V 1.xlsb' `
  --out-dir 'OUTPUT\2026.09\KTMA_FM_MAPPING_V1\RUN_NNN'
```

Después de generar, ejecutar el recálculo nativo y la QA:

```powershell
& '07_TOOLS\Invoke-KtmaFundingMemoExcelValidation.ps1' `
  -WorkbookPath 'OUTPUT\2026.09\KTMA_FM_MAPPING_V1\RUN_NNN\FM2026.09_ACCOUNTING_MAPPING_V1.xlsx' `
  -ReceiptPath 'OUTPUT\2026.09\KTMA_FM_MAPPING_V1\RUN_NNN\KTMA_FM_EXCEL_COM_RECEIPT.json'

$env:PYTHONPATH = 'src;90_RUNTIME\venv_win\Lib\site-packages'
& '90_RUNTIME\venv_win\Scripts\python.exe' -B '07_TOOLS\ktma_funding_memo_verify.py' `
  --root . --run-dir 'OUTPUT\2026.09\KTMA_FM_MAPPING_V1\RUN_NNN'
```

El registro inicial contiene 66 cuentas, 16 filas físicas y 32 de las 72 celdas entidad-destino históricas. Los restantes 187 códigos conservan el estado `SIN_ASIGNACION_FM`.

## Historial y cambios posteriores

La versión `1.0.1` reconstruye la matriz efectiva desde
`04_CONFIG/FUNDING_MEMO/KTMA_FM_DECISIONS.jsonl`. La fila histórica original se conserva,
pero quedó supersedida porque contenía horas y vigencia no sustentadas. La comunicación y
vigencia desconocidas se registran como `null`; no se aplica retroactividad implícita.

Para registrar una decisión futura, preparar un JSON con todos los campos de gobernanza y
agregarlo de forma append-only:

```powershell
$env:PYTHONPATH = 'src'
& '90_RUNTIME\venv_win\Scripts\python.exe' -B -m kt_movemacc.cli funding-memo-decision `
  --root . --event 'RUTA\decision.json'
```

Los estados `PROPOSED`, `REJECTED` y `SUPERSEDED` quedan auditables pero no alteran el
cálculo. Un evento `IMPLEMENTED` requiere período y versión; las decisiones futuras
preservan los períodos anteriores. Las instrucciones atribuidas a gerencia o Directorio
deben usar `MANAGEMENT_REPORTED_BY_HUMAN` o `BOARD_REPORTED_BY_HUMAN` y
`REPORTED_BY=HUMAN`.

Prueba focalizada reproducible:

```powershell
$env:PYTHONPATH = 'src;90_RUNTIME\venv_win\Lib\site-packages'
py -3.11 -m pytest -q -p no:cacheprovider 06_TESTS/test_funding_memo.py
```
