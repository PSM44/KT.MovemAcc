# USECASE_PHASE1 — Ejecución mensual de PH1 sin IA (Windows)

**Proyecto:** KT.MovemAcc  
**Versión:** 0.10 — procedimiento Windows corregido y convergente con el CLI protegido  
**Fecha:** 2026-10-28  
**Estado:** borrador operativo; entorno Windows verificado para importación, ejecución financiera bloqueada hasta disponer de un grant autorizado.  
**Destinatario:** una persona sin experiencia en Python, Git, RORCH ni contabilidad programática.

## 1. Qué vamos a conseguir

PH1 lee los dos archivos de mayores contables del mes (Eplaza e Impulsa), genera un libro de Excel consolidado y produce información de control. **La ejecución de PH1 no necesita ChatGPT, RORCH, DSH ni internet**, según el resultado informado para NTV009A. **En la fase actual sí requiere Python correctamente instalado y el proyecto local preparado.** Todavía no existe un `.exe` de usuario certificado.

Este instructivo usa **PowerShell de Windows**. No requiere VS Code, Git ni WSL durante la operación ordinaria. Windows y PowerShell se consideran disponibles; **Python y sus dependencias deben estar instalados y configurados correctamente**. El usuario no tiene que reinstalarlos cada mes.

> **Distinción de evidencia:** la ejecución independiente de IA y la prueba de regresión agosto fueron reportadas por RORCH en NTV009A; el comando histórico de HO.1 se probó en entorno WSL/Linux. La ejecución nativa con PowerShell y el paquete Python Windows **aún requieren una prueba real de aceptación**. Los comandos de este documento son el procedimiento candidato y contienen comprobaciones explícitas para evitar un éxito aparente.

## 2. Aplicaciones y componentes requeridos

| Componente | ¿Necesario? | Qué debe estar preparado |
|---|---|---|
| Windows | Sí | Windows operativo, acceso de lectura/escritura a las carpetas de trabajo. |
| PowerShell | Sí | Viene integrado en Windows; utilícelo para ejecutar los pasos. |
| Python | Sí, en Fase A | Instalación de Windows operativa, accesible mediante `py` o `python`, con las dependencias del proyecto instaladas. No basta con una instalación de Python vacía. |
| KT.MovemAcc | Sí | Código del proyecto en `C:\01. GitHub\Kumquat.TECH\KT.MovemAcc` y `src\kt_movemacc` accesible. |
| Microsoft Excel | Recomendado para revisar el resultado | No se requiere Excel COM para ejecutar el motor, según NTV009A. Para abrir y revisar `.xlsx` sí conviene Excel. |
| VS Code | No | Puede utilizarse si se desea ver archivos, pero no es necesario. |
| Git, WSL, Docker, DSH, RORCH, ChatGPT | No para operar PH1 | No se ejecutan durante el uso mensual normal. |

**Nota de soporte:** el entorno `90_RUNTIME/venv_clean/bin/python` utilizado por HO.1 es de Linux/WSL y **no debe escribirse como un ejecutable de Windows**. Si se ha provisionado un entorno virtual Windows, su ejecutable estará normalmente en `...\Scripts\python.exe`. RORCH debe confirmar el intérprete oficial de Windows durante la certificación inicial.

## 3. Ejemplo: preparar septiembre de 2026

### Paso 1 — Abrir la carpeta del proyecto

Abra el Explorador de archivos, copie esta ruta en la barra de direcciones y presione Enter:

`C:\01. GitHub\Kumquat.TECH\KT.MovemAcc`

Compruebe que existen las carpetas `RAW.INPUT`, `src` y `OUTPUT` (esta última puede ser creada mediante el procedimiento autorizado si falta). Si no están, deténgase: posiblemente abrió una copia equivocada del proyecto.

### Paso 2 — Guardar los dos originales de septiembre

Dentro de `RAW.INPUT`, prepare la carpeta `2026.09` y coloque **copias** de los libros originales:

```text
C:\01. GitHub\Kumquat.TECH\KT.MovemAcc\
  RAW.INPUT\
    2026.09\
      Mayor Inmob. Eplaza 2026 09 V 1.xlsb
      Mayor Grupo Impulsa 2026 09 V 1.xlsb
```

El formato requerido por el proceso documentado es `.xlsb` (libro binario de Excel). No los convierta a `.xlsx`, CSV ni PDF y no cambie su contenido. Estos son los **nombres convencionales previstos**; si los archivos recibidos tienen otra versión (por ejemplo, `V 2`), no les cambie simplemente el nombre: debe validarse la selección correcta de fuente. Confirme que ambos corresponden a septiembre de 2026 y a sus respectivas sociedades.

Para meses futuros cambian el año y mes de la carpeta y de los nombres. No mezcle el período indicado al CLI, el nombre del destino y el período de los XLSB.

### Paso 3 — Abrir PowerShell dentro del proyecto

En el Explorador, mientras visualiza la carpeta del proyecto, haga clic en la barra de direcciones, escriba `powershell` y presione Enter. Se abrirá una ventana de PowerShell en esa ubicación.

Si lo abrió desde el menú Inicio, ejecute este comando (copiar y pegar completo):

```powershell
Set-Location -LiteralPath 'C:\01. GitHub\Kumquat.TECH\KT.MovemAcc'
```

Confirme la carpeta actual:

```powershell
Get-Location
```

### Paso 4 — Comprobar que existen las entradas

Pegue estas dos instrucciones; ambas deben responder `True`:

```powershell
Test-Path -LiteralPath '.\RAW.INPUT\2026.09\Mayor Inmob. Eplaza 2026 09 V 1.xlsb'
Test-Path -LiteralPath '.\RAW.INPUT\2026.09\Mayor Grupo Impulsa 2026 09 V 1.xlsb'
```

Si alguna responde `False`, deténgase y corrija la ubicación o solicite el archivo faltante. No genere información de un mes con archivos de otro.

### Paso 5 — Confirmar la disponibilidad de Python y del motor

Use el **Python Windows preparado para KT.MovemAcc**. No use `py` para ejecutar PH1: actualmente `py` puede seleccionar Python 3.15 global, que no contiene las dependencias financieras del proyecto.

```powershell
$pythonKTMA = '.\90_RUNTIME\venv_win\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonKTMA -PathType Leaf)) {
    throw "No existe el intérprete Windows preparado: $pythonKTMA"
}
& $pythonKTMA --version
```

Que `py --version` o `python --version` muestre una versión no garantiza que sea el entorno de KT.MovemAcc. En la instalación observada el entorno preparado usa Python 3.12 y se encuentra en `90_RUNTIME\venv_win`.

Compruebe que el paquete del proyecto es importable; abra PowerShell en la raíz y ejecute:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location).Path 'src')
$env:PYTHONDONTWRITEBYTECODE = '1'
& $pythonKTMA -B -c "import openpyxl, pyxlsb, pandas; import kt_movemacc.cli; print('Motor PH1 encontrado'); print('openpyxl', openpyxl.__version__)"
```

El resultado observado esperado es `Motor PH1 encontrado` y una versión de `openpyxl`. **Si falla la importación o falta una dependencia, no cambie el comando a `py` ni instale paquetes al azar**: el entorno Windows preparado tiene una incidencia de soporte.

### Paso 6 — Ejecutar una revisión LAB_ONLY sin sobrescribir resultados

Para una prueba técnica se utiliza `--lab-review`. Este modo no requiere un grant productivo, pero solo permite crear tres salidas PH1 nuevas bajo `90_RUNTIME\PH1_REVIEW\<período>\RUN_NNN`. Rechaza `OUTPUT`, `DATA`, rutas externas, destinos existentes y nombres que no sigan esa estructura. El resultado es un candidato de revisión, no una publicación ni aceptación financiera.

Primero confirme la interfaz instalada:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location).Path 'src')
& $pythonKTMA -B -m kt_movemacc.cli ph1 --help
```

Prepare las variables y compruebe que el destino todavía no existe:

```powershell
$periodo = '2026.09'
$rawEplaza = Join-Path (Get-Location).Path 'RAW.INPUT\2026.09\Mayor Inmob. Eplaza 2026 09 V 1.xlsb'
$rawImpulsa = Join-Path (Get-Location).Path 'RAW.INPUT\2026.09\Mayor Grupo Impulsa 2026 09 V 1.xlsb'
$destino = Join-Path (Get-Location).Path '90_RUNTIME\PH1_REVIEW\2026.09\RUN_001'

if (-not (Test-Path -LiteralPath $rawEplaza -PathType Leaf)) { throw "Falta EPLAZA: $rawEplaza" }
if (-not (Test-Path -LiteralPath $rawImpulsa -PathType Leaf)) { throw "Falta IMPULSA: $rawImpulsa" }
if (Test-Path -LiteralPath $destino) { throw "El destino ya existe; no se sobrescribirá: $destino" }
```

Ejecute la prueba:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location).Path 'src')
& $pythonKTMA -B -m kt_movemacc.cli ph1 `
    --period $periodo `
    --raw-eplaza $rawEplaza `
    --raw-impulsa $rawImpulsa `
    --out-dir $destino `
    --lab-review

Write-Host "Código de salida PH1: $LASTEXITCODE"
Write-Host "Revise la carpeta: $destino"
```

**Atención:** no sustituya `$pythonKTMA` por `py`; eso vuelve a seleccionar Python 3.15 global y reproduce `ModuleNotFoundError: No module named 'openpyxl'`. No agregue `--grant-file` ni `--authorization-file` al modo LAB_ONLY.

El parámetro `--out-dir` indica **dónde guardar los resultados**. Para esta prueba debe permanecer bajo `90_RUNTIME\PH1_REVIEW`. No cambie el destino a una carpeta canónica y no reutilice un `RUN_NNN` existente. Una ejecución productiva sigue requiriendo un grant externo verificable y no está habilitada por `--lab-review`.

### Paso 7 — Encontrar y revisar el resultado

Después de un código de salida `0`, abra la carpeta indicada en `Revise la carpeta`. Busque un libro consolidado `.xlsx` y los reportes que realmente haya generado la versión instalada del motor.

**Nombre esperado por convención:** `CAM2026.09_CONSOL.ALIGN.xlsx`. La generación real y el lugar exacto dentro de `--out-dir` deben confirmarse en la ejecución autorizada. No confunda que exista un archivo con que su contenido esté contablemente aprobado.

Compruebe que el archivo abre en Excel, corresponde a septiembre, contiene las sociedades esperadas, presenta los totales y no informa incidencias materiales. Evite guardar el libro únicamente para inspeccionarlo, ya que Excel puede alterar metadatos y el SHA-256.

### Paso 8 — Interpretar el resultado

- **Éxito técnico:** el proceso termina con código `0` y existen salidas legibles en el directorio seleccionado. Esto no equivale por sí solo a aprobación financiera.
- **Revisión requerida:** hay advertencias, discrepancias, fuentes ambiguas o datos estructurales inesperados. No publique como aceptado.
- **Fallo:** el proceso termina con código distinto de `0`, no genera el consolidado o presenta un error. No reutilice salidas parciales como definitivas.

Guarde el mensaje de error y el nombre de los originales. No edite los XLSB para forzar que el proceso termine.

### Paso 9 — Publicación definitiva del mes

**Todavía no debe hacerse automáticamente por esta guía.** El destino final previsto es:

`C:\01. GitHub\Kumquat.TECH\KT.MovemAcc\OUTPUT\2026.09\CAM2026.09_CONSOL.ALIGN.xlsx`

Debe existir una política implementada y probada que valide los resultados, compruebe colisiones y publique con control de versiones, sin sobrescribir una salida aceptada. Hasta que la ejecución nativa y el mecanismo de publicación estén certificados, conserve el resultado como **versión de revisión** en el directorio aislado y solicite la decisión de aceptación correspondiente.

### Paso 10 — ¿Cuándo terminó PH1?

Para considerar PH1 completada para el mes, deben cumplirse todas estas condiciones:

1. Los dos libros XLSB correctos se identificaron y preservaron sin modificaciones.
2. El motor reconoció el mes, las entidades y las hojas contables.
3. La ejecución terminó sin errores bloqueantes.
4. El Excel consolidado existe y puede abrirse.
5. Los controles contables y de integridad se aprobaron, con evidencias vinculadas al período.
6. No hay discrepancias materiales sin resolver.
7. El resultado final fue publicado mediante el procedimiento autorizado, con identificación del período y trazabilidad de fuentes.

Un mensaje `SUCCESS` de un ejecutor externo no reemplaza estas comprobaciones. La ausencia de autorización para publicación significa que se completó **la generación de revisión**, no la emisión oficial.

## 4. Problemas frecuentes y solución segura

| Problema | Qué hacer |
|---|---|
| `py` usa Python 3.15 y falta `openpyxl` | No use `py`; ejecute `& '.\90_RUNTIME\venv_win\Scripts\python.exe' -B ...`. |
| `No module named kt_movemacc` | Confirmar que está en la raíz y que estableció `PYTHONPATH` como en el paso 5. |
| Falta una biblioteca Python | Detenerse; el entorno debe repararlo soporte o el instalador previsto para Fase C. |
| `--grant-file is required` | Se omitió `--lab-review` o se intentó una ejecución productiva. Para una prueba aislada use el comando LAB_ONLY del paso 6. |
| `PRODUCTIVE_TRUST_UNAVAILABLE` | El verificador falla cerrado porque todavía no existe emisor/custodia productiva. Requiere una decisión e implementación separadas. |
| Archivo XLSB no encontrado | Revisar nombres, extensiones y carpeta `RAW.INPUT\2026.09`. |
| Período incorrecto | Confirmar `--period 2026.09` y revisar que los dos XLSB realmente correspondan al mes. |
| Hoja o columna inesperada | No modificar el libro; reportar cambio de estructura de origen. |
| Ya existe destino | No sobrescribirlo; crear otro directorio de revisión. |
| Resultado con diferencias contables | No aprobar ni publicar; solicitar evaluación de la incidencia. |
| Excel cambia el hash tras guardar | Comparar contenido financiero por separado; no atribuir el cambio automáticamente a una falla contable. |
| Aparece una carpeta `C\Users\...` dentro del repositorio | Detener la ejecución y reportar la ruta: una ruta Windows se interpretó incorrectamente como relativa. No borrar sin inventariar. |

## 5. Lo que PH1 no hace todavía

- No transfiere datos al **Funding Memo** (Fase B).
- No ofrece todavía un `.exe` ni una interfaz para usuarios básicos (Fase C).
- No implica importación PH1.5 a SQLite; eso es otro proceso, con autorización separada.
- No exige ejecutar ni iniciar RORCH/DSH para producir el consolidado una vez preparado correctamente el entorno.
- No declara aceptado un mes nuevo por haber generado un Excel.

## 6. Verificación inicial obligatoria por el equipo de desarrollo

Antes de entregar esta guía como manual oficial para usuarios Windows, RORCH debe ejecutar y documentar **una prueba nativa con PowerShell** que confirme:

- Intérprete Python Windows real, versión y dependencias.
- Comando `py`/`python` exacto y sus parámetros efectivos.
- Descubrimiento automático de XLSB desde `RAW.INPUT\YYYY.MM` o, si falla, interfaz explícita para seleccionar ambas rutas.
- Carga de los archivos de agosto con un `--out-dir` aislado y código de salida verificable.
- Detección de directorio de salida y nombre exacto del Excel.
- Validación financiera independiente sobre el resultado.
- Protección de archivos canónicos y manejo de errores.
- Procedimiento seguro de publicación mensual y política ante salida existente.

**Si alguno de estos puntos falla, esta guía permanece en estado `DRAFT / WINDOWS_NATIVE_NOT_VERIFIED`.** Corregir el motor y actualizar la documentación; no convertir supuestos en instrucciones oficiales.

## 7. Referencias internas de continuidad

- `HO1_CANONICAL_OPERATIONAL_CONTINUITY.md`: entradas, nombres XLSB, operación PH1 y PH1.5, preservación de fuentes.
- `HO1_RUNBOOK.md`: comando PH1 verificado históricamente en WSL, controles y errores.
- Resultado reportado `KTMA_NTV009A`: autonomía de IA, CLI con período y `--out-dir`, regresión agosto, octubre real pendiente.
- `02_SKILLS/TRANSVERSAL/SKILLS.QA.TRANSVERSAL.md` y `02_SKILLS/INTERNAL/SKILLS.QA.KT.MovemAcc.md`: QA normativo autorizado.

**Autoridad:** aprobar o publicar nuevos resultados contables es independiente de la corrección técnica del CLI. `RM-GATE-003` y `RM-GATE-004` permanecen bajo decisión HUMAN.
