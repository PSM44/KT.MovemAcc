# Caso De Uso PH1.5: Base Financiera SQLite

## Objetivo

PH1.5 crea una base local SQLite para consultar, reconciliar y rastrear la informacion contable proveniente de los archivos RAW XLSB de EPLAZA e IMPULSA.

PH1.5 no reemplaza el workbook PH1 aceptado. Es una capa intermedia para auditoria, trazabilidad y preparacion de reportes futuros.

## Ruta De La Base

Por defecto:

```text
DATA/KTMA.sqlite
```

Esta base contiene informacion financiera local. No debe publicarse en GitHub ni en paquetes publicos.

## Entradas

Los archivos RAW se leen desde:

```text
RAW.INPUT/<AAAA.MM>/
```

Para agosto 2026:

```text
RAW.INPUT/2026.08/Mayor Inmob. Eplaza 2026 08 V 1.xlsb
RAW.INPUT/2026.08/Mayor Grupo Impulsa 2026 08 V 1.xlsb
```

Los archivos RAW no se modifican.

## Como Ejecutar En Windows

Desde la raiz del proyecto en PowerShell:

```powershell
.\90_RUNTIME\venv_win\Scripts\python.exe -m kt_movemacc ph15-db --period 2026.08
```

O con el comando instalado:

```powershell
.\90_RUNTIME\venv_win\Scripts\kt_movemacc.exe ph15-db --period 2026.08
```

Para ver el ejemplo de trazabilidad:

```powershell
.\90_RUNTIME\venv_win\Scripts\python.exe -m kt_movemacc ph15-db --period 2026.08 --print-lineage
```

## Como Ejecutar En WSL

Desde la raiz del proyecto:

```bash
PYTHONPATH=src 90_RUNTIME/venv_clean/bin/python -m kt_movemacc ph15-db --period 2026.08
```

O:

```bash
PYTHONPATH=src 90_RUNTIME/venv_clean/bin/kt_movemacc ph15-db --period 2026.08
```

## Que Hace La Importacion

La importacion:

- identifica el periodo contable
- calcula SHA-256 de cada RAW XLSB
- conserva las filas originales y su numero de fila
- normaliza cuentas, titulos y valores financieros
- registra contexto jerarquico
- calcula saldos consolidados EPLAZA + IMPULSA
- guarda linaje de reglas aprobadas PH1
- genera checks de reconciliacion

Si ocurre un error, la transaccion se revierte.

## Duplicados

Si se ejecuta otra vez con los mismos archivos, PH1.5 no duplica filas fuente ni observaciones. Si detecta que un archivo fuente para el mismo periodo y entidad cambio de hash, detiene la importacion salvo que se use una opcion explicita para experimentos controlados.

Politica vigente: `REJECT`. Un archivo fuente cambiado para el mismo periodo y entidad se rechaza. PH1.5 no reemplaza ni sobrescribe historia financiera aceptada.

## Ejemplo Validado

PH1.5 valida:

```text
PROYECTO HERNANDO DE AGUIRRE
EPLAZA = 550120.960000 UF
IMPULSA = 0.000000 UF
CONSOLIDADO = 550120.960000 UF
```

La trazabilidad muestra:

- archivo fuente EPLAZA
- hoja `CUENTAS DE MAYOR AGOSTO 2026`
- fila fuente 54
- regla `CR-004`
- formula aprobada `=SUM(G57,G111)`
- diferencia UF `0.000000`

## Limitaciones Operativas

- PH2 no esta implementado en esta tarea.
- La base SQLite es local, no un servidor.
- La validacion Excel Desktop pertenece al flujo PH1; PH1.5 guarda evidencia Python/SQL.
- La revision visual y de usabilidad humana sigue siendo una compuerta separada.
- La consulta ordinaria debe hacerse con `ph15-query`; SQL libre queda reservado para revision tecnica controlada.

## Consultas De Solo Lectura

Ejemplos:

```powershell
.\90_RUNTIME\venv_win\Scripts\python.exe -m kt_movemacc ph15-query periods
.\90_RUNTIME\venv_win\Scripts\python.exe -m kt_movemacc ph15-query account --period 2026.08 --account-code 121011
.\90_RUNTIME\venv_win\Scripts\python.exe -m kt_movemacc ph15-query consolidated --period 2026.08 --semantic-key "PROYECTO HERNANDO DE AGUIRRE#1"
.\90_RUNTIME\venv_win\Scripts\python.exe -m kt_movemacc ph15-query discrepancies --period 2026.08
```

## Respaldo Y Recuperacion

Para respaldar la base, cierre procesos que la esten usando y copie:

```text
DATA/KTMA.sqlite
```

Si existen archivos `DATA/KTMA.sqlite-wal` o `DATA/KTMA.sqlite-shm`, copie esos archivos junto con la base o ejecute una importacion limpia en una nueva copia del repositorio.
