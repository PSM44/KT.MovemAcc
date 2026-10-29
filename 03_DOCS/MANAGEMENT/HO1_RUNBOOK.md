# HO.1 — Runbook Operacional

## 1. Antes de operar

Validar que se está en la raíz del proyecto:

```bash
pwd
```

Validar Git sin modificarlo:

```bash
git fetch origin
git symbolic-ref --short HEAD
git rev-parse HEAD
git rev-parse origin/main
git rev-list --left-right --count HEAD...origin/main
git status --short
```

Resultado canónico esperado al cierre HO.1:

- Rama: `main`.
- Local y remoto: `e948336cd790d998e4af6243d00246989404897e`.
- Ahead/behind: `0/0`.
- Pueden existir archivos locales no publicados; no limpiar sin autorización.

## 2. Verificación de entorno Python

```bash
PYTHONPATH=src 90_RUNTIME/venv_clean/bin/python - <<'PY'
import sys
import kt_movemacc.cli
import kt_movemacc.ph15_database
print(sys.executable)
print(sys.version)
print('imports_ok')
PY
```

Si falla por dependencias, no instalar automáticamente sin decisión operacional. Registrar el error y solicitar autorización.

## 3. Verificación read-only de SQLite

```bash
PYTHONPATH=src 90_RUNTIME/venv_clean/bin/python - <<'PY'
import sqlite3, hashlib
from pathlib import Path
DB = Path('DATA/KTMA.sqlite')
print(hashlib.sha256(DB.read_bytes()).hexdigest())
con = sqlite3.connect(f'file:{DB.resolve().as_posix()}?mode=ro', uri=True)
print(con.execute('PRAGMA integrity_check').fetchone()[0])
print(con.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0])
print(con.execute('SELECT group_concat(period_code) FROM accounting_periods').fetchone()[0])
PY
```

Esperado para base local actual:

- SHA256 `b5f6b6eae6dcb2f1273f8e5d1706b6db30e52d9250ad148b68e88881ffac60d0`.
- Integridad `ok`.
- Esquema `1`.
- Periodo `2026.08`.

## 4. PH1 — operación controlada

Sólo ejecutar PH1 si la tarea lo autoriza. Para pruebas, usar salida desechable:

```bash
PYTHONPATH=src 90_RUNTIME/venv_clean/bin/python -m kt_movemacc ph1 --period 2026.08 --out-dir 90_RUNTIME/ho1_ph1_probe
```

Prohibido en operación normal HO.1:

- Sobrescribir `OUTPUT/2026.08/CAM2026.08_CONSOL.ALIGN.xlsx`.
- Modificar criterios contables.
- Publicar workbooks financieros.

## 5. PH1.5 — consultas seguras

Las siguientes consultas no modifican la base:

```bash
PYTHONPATH=src 90_RUNTIME/venv_clean/bin/python -m kt_movemacc ph15-query periods
PYTHONPATH=src 90_RUNTIME/venv_clean/bin/python -m kt_movemacc ph15-query entities
PYTHONPATH=src 90_RUNTIME/venv_clean/bin/python -m kt_movemacc ph15-query source-files --period 2026.08
PYTHONPATH=src 90_RUNTIME/venv_clean/bin/python -m kt_movemacc ph15-query runs --period 2026.08
PYTHONPATH=src 90_RUNTIME/venv_clean/bin/python -m kt_movemacc ph15-query account --period 2026.08 --account-code 121011
PYTHONPATH=src 90_RUNTIME/venv_clean/bin/python -m kt_movemacc ph15-query consolidated --period 2026.08 --semantic-key 'PROYECTO HERNANDO DE AGUIRRE#1'
PYTHONPATH=src 90_RUNTIME/venv_clean/bin/python -m kt_movemacc ph15-query discrepancies --period 2026.08
PYTHONPATH=src 90_RUNTIME/venv_clean/bin/python -m kt_movemacc ph15-query hernando --period 2026.08
```

## 6. PH1.5 — importación controlada

La importación escribe SQLite. No ejecutarla durante revisión documental salvo autorización específica para el periodo. Windows es el único escritor autorizado de la base canónica; WSL2 queda limitado a `ph15-query`/apertura read-only o debe delegar la escritura a Windows.

```powershell
.\90_RUNTIME\venv_win\Scripts\python.exe -m kt_movemacc ph15-db --period 2026.08
```

Si WSL/Linux intenta escribir `DATA/KTMA.sqlite`, el guard debe detener la operación antes de cualquier escritura o migración. Las bases desechables fuera de la ruta canónica pueden usarse para validación aislada. Si aparece `Source hash changed`, detenerse. No usar reemplazo manual ni editar SQLite. La política vigente es `REJECT`.

La aceptación del workbook PH1 se verifica contra el manifiesto privado autorizado (ruta, SHA-256, tamaño y cinco hojas), no contra el blob histórico de `HEAD` como única fuente de verdad.

## 7. Procedimiento de respaldo

Opción segura con Python:

```bash
PYTHONPATH=src 90_RUNTIME/venv_clean/bin/python - <<'PY'
from pathlib import Path
from kt_movemacc.ph15_database import backup_database, integrity_report
src = Path('DATA/KTMA.sqlite')
dst = Path('90_RUNTIME/backups/KTMA.manual.sqlite')
backup_database(src, dst)
print(integrity_report(dst))
PY
```

La ruta de backup debe ser local/privada y no publicada. Si el destino fuera la ruta canónica, la misma política Windows-only aplica.

## 8. Manejo de errores comunes

| Síntoma | Acción |
| --- | --- |
| Falta RAW | Solicitar archivos privados al usuario; no simular datos reales. |
| Hash RAW cambiado | Detenerse; abrir decisión HUMAN sobre fuente corregida. |
| SQLite locked | Cerrar procesos; usar backup API; no borrar sidecars a ciegas. |
| Dependencia Python faltante | Registrar entorno; no instalar sin autorización. |
| Discrepancias no vacías | Detener PH2; documentar evidencia y pedir revisión contable. |
| Working tree sucio | No limpiar; reportar exactamente. |

## 9. Cierre de operación mensual

- Guardar logs o evidencia no pública.
- Confirmar que no hay RAW/SQLite/OUTPUT en staging.
- Confirmar que PH2 sigue no autorizado salvo instrucción explícita.
- Preparar resumen para HUMAN con valores esperados y discrepancias.
