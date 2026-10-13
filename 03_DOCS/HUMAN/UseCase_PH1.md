# KT.MovemAcc — Caso de uso PH1: consolidación y alineación contable

**Documento:** `UseCase_PH1.md`
**Idioma:** Español
**Estado:** PH1 aceptada funcionalmente por HUMAN tras TASK033R; publicación GitHub pendiente.
**Caso de referencia:** agosto de 2026 (`2026.08`).
**Ámbito:** solo Phase 1 (PH1). La elaboración y el mapeo del Funding Memo (PH2) no forman parte de este procedimiento.

## 1. Objetivo

Generar, desde los mayores contables mensuales originales de **Inmobiliaria Eplaza** y **Grupo Impulsa**, un libro Excel que conserve las cuentas de cada entidad, las alinee y consolide en una vista común y deje trazabilidad de las reglas, fórmulas y excepciones. El sistema está concebido para tolerar variaciones mensuales en la cantidad y posición de filas: las reglas de negocio deben basarse en códigos de cuenta y contexto jerárquico, no en números de fila fijos.

**Resultado de PH1:** `OUTPUT/<AAAA.MM>/CAM<AAAA.MM>_CONSOL.ALIGN.xlsx`. Para agosto de 2026: `OUTPUT/2026.08/CAM2026.08_CONSOL.ALIGN.xlsx`.

## 2. Requisitos previos

1. Equipo Windows con **Microsoft Excel Desktop** para inspección y recálculo final y **VS Code** (terminal PowerShell).
2. Repositorio local de KT.MovemAcc y entorno Python instalado y configurado según `03_DOCS/HUMAN/PH1_USER_GUIDE.md`.
3. Los dos archivos originales XLSB del período, sin modificaciones manuales.
4. Acceso de lectura a la ruta de los RAW configurada en el proyecto y permiso de escritura para la carpeta de salida.
5. Excel **cerrado** sobre el archivo de salida antes de ejecutar o regenerar PH1; en caso contrario, puede ocurrir `PermissionError` por bloqueo de Windows.

**Ruta local utilizada durante el desarrollo:** `C:\01. GitHub\Kumquat.TECH\KT.MovemAcc`. Si el repositorio está en otro directorio, sustituirla por la ruta real.

> **Contrato de rutas verificado en el motor:** el CLI resuelve entradas desde `RAW.INPUT/<AAAA.MM>/` dentro de la raíz del proyecto, salvo que el usuario entregue rutas explícitas con `--raw-eplaza` y `--raw-impulsa`. El resultado se escribe en `OUTPUT/<AAAA.MM>/` salvo uso explícito de `--out-dir`.

## 3. Dónde colocar los archivos originales (RAW.INPUT)

**Convención operativa verificada para PH1:** guardar **dos archivos `.xlsb`**, uno por empresa, en una carpeta de entrada por período bajo la raíz del proyecto:

```text
C:\01. GitHub\Kumquat.TECH\KT.MovemAcc\
├── RAW.INPUT\
│   └── 2026.08\
│       ├── Mayor Inmob. Eplaza 2026 08 V 1.xlsb
│       └── Mayor Grupo Impulsa 2026 08 V 1.xlsb
└── OUTPUT\
    └── 2026.08\
        └── CAM2026.08_CONSOL.ALIGN.xlsx
```

| Empresa | Nombre original exacto para el ejemplo validado `2026.08` |
| --- | --- |
| EPLAZA | `Mayor Inmob. Eplaza 2026 08 V 1.xlsb` |
| IMPULSA | `Mayor Grupo Impulsa 2026 08 V 1.xlsb` |

**Secuencia para el usuario:**

1. Identificar el mes contable en formato `AAAA.MM`; por ejemplo, agosto de 2026 = `2026.08`.
2. Crear, si no existe, `RAW.INPUT\2026.08` dentro de la raíz del proyecto.
3. Copiar allí los **dos originales XLSB**, manteniendo intactos sus contenidos, hojas, códigos contables y nombres de archivo recibidos. No editar los archivos fuente.
4. Comprobar que no falte una empresa ni se mezclen meses. En el ejemplo de agosto, verificar que los nombres coincidan exactamente con la tabla.
5. Ejecutar PH1 con `--period 2026.08`. El CLI busca exactamente los dos nombres indicados para agosto en `RAW.INPUT\2026.08`.
6. Buscar el resultado en `OUTPUT\2026.08\CAM2026.08_CONSOL.ALIGN.xlsx` dentro de la misma raíz. La carpeta de salida se crea o utiliza según la implementación confirmada; puede sobrescribir el Excel previo del período si se regenera.

**Meses posteriores:** conservar como regla general la carpeta `RAW.INPUT\<AAAA.MM>`. En la versión actual, el resolvedor estándar construye nombres exactos con `V 1` a partir del período (`Mayor Inmob. Eplaza AAAA MM V 1.xlsb` y `Mayor Grupo Impulsa AAAA MM V 1.xlsb`). No selecciona automáticamente `V 2` ni otras variantes; si hay varias versiones, debe elegirse explícitamente la correcta mediante `--raw-eplaza` y `--raw-impulsa`, o detenerse y pedir selección humana. Una duplicación adicional no bloquea la ejecución si los dos nombres exactos esperados existen.

**Privacidad:** estos archivos contienen información contable. No se incluyen automáticamente en el próximo commit público. `RAW.INPUT` debe mantenerse excluido de la publicación salvo autorización expresa; lo mismo aplica a los libros finales con datos financieros.

## 4. Procedimiento paso a paso

### Paso 1 — Abrir el proyecto

En VS Code Windows, abrir `C:\01. GitHub\Kumquat.TECH\KT.MovemAcc` (o la ubicación local equivalente) y abrir un terminal **PowerShell** en la raíz del repositorio.

### Paso 2 — Comprobar datos y período

Confirmar que los dos RAW están en `RAW.INPUT\2026.08`, corresponden al **mismo mes**, son los originales recibidos y que sus nombres coinciden exactamente con los esperados para agosto. Para agosto de 2026, usar período `2026.08` (formato `AAAA.MM`).

### Paso 3 — Cerrar el archivo Excel anterior

Si existe una salida del mismo período y está abierta en Excel, cerrar el libro y guardar previamente cualquier anotación manual que se desee conservar fuera de la salida regenerable. No borrar archivos `~$` mientras haya una sesión activa de Excel. **Regenerar PH1 puede sobrescribir el XLSX del período.**

### Paso 4 — Ejecutar PH1

Desde PowerShell en la raíz:

```powershell
.\90_RUNTIME\venv_win\Scripts\python.exe -m kt_movemacc ph1 --period 2026.08
```

Este es el comando Windows verificado para el entorno del proyecto. Si el entorno virtual no existe en otro equipo, completar primero la instalación conforme al manual; no inventar ni ejecutar una ruta alternativa sin comprobarla.

**Criterio de éxito:** el comando termina con código de salida `0`, sin error de lectura, escritura o bloqueo. No equiparar una ejecución sin errores con la aprobación contable o visual; son controles posteriores.

### Paso 5 — Abrir el resultado

Para agosto:

`OUTPUT\2026.08\CAM2026.08_CONSOL.ALIGN.xlsx`

Abrirlo mediante Microsoft Excel Desktop. Comprobar que no aparezcan mensajes de reparación, corrupción o referencias inválidas. De ser necesario, permitir el recálculo de fórmulas. **No volver a ejecutar PH1 mientras este libro esté abierto.**

## 5. Estructura obligatoria del resultado

El libro contiene **exactamente cinco hojas**:

| Hoja (agosto de 2026) | Función |
| --- | --- |
| `CAM2026.08_CONSOL.ALIGN` | Vista consolidada y alineada EPLAZA + IMPULSA, incluidas cuentas y subtotales jerárquicos. |
| `CM2026.08_EPLAZA` | Mayor de EPLAZA, con cuentas y subtotales verticales respaldados por su jerarquía. |
| `CM2026.08_IMPULSA` | Mayor de IMPULSA, con la misma estructura de comprobación. |
| `AUDIT.PH1` | Auditoría, conciliaciones, discrepancias y trazabilidad. |
| `CONTROL` | Metadatos de entradas, período y generación. |

En las hojas CM, la **columna G** es `VALORES UF`, la **columna J** es `VALORES $$` y la **columna K** es `VISIBILIDAD_UF`. La columna M de CAM es `VISIBILIDAD`. Las posiciones específicas de otras columnas deben comprobarse contra la hoja generada y la especificación técnica de la versión instalada.

## 6. Cómo usar las hojas CM (EPLAZA e IMPULSA)

1. Revisar que las cuentas y códigos correspondan a la entidad y período.
2. Revisar los títulos, subtítulos y subtotales de la columna **G — VALORES UF**.
3. Para ocultar cuentas y grupos sin movimiento neto UF, abrir el filtro de **K — VISIBILIDAD_UF** y seleccionar `MOSTRAR`. Esto cambia **solo la presentación**: no borra registros, no sustituye el libro original y no modifica el cálculo.
4. Si es necesario inspeccionar ceros o investigar un grupo, restablecer el filtro para volver a ver todas las filas.
5. Conservar los signos contables originales. En títulos que representan subtotales, las fórmulas deben sumar los **hijos directos** o los subtotales aprobados, nunca subtotales y sus descendientes simultáneamente.

**Ejemplos ya validados, exclusivos de agosto de 2026:**

- EPLAZA `G160` — `TOTAL ACTIVO`: **749.974,00 UF**.
- EPLAZA `G219` — `TOTAL PASIVO`: **−748.528,19 UF**.
- IMPULSA `G39` — `TOTAL ACTIVO`: **164.824,68 UF**.
- IMPULSA `G84` — `TOTAL PASIVO`: **−166.848,08 UF**.

Estas celdas son **ejemplos de verificación**, no referencias que deban codificarse para todos los meses.

## 7. Cómo usar CAM (consolidación)

1. Revisar las cuentas alineadas por **código contable**; cuando no exista código, utilizar el título/descripción y su contexto, según los criterios vigentes.
2. Verificar las columnas de EPLAZA, IMPULSA y totales consolidados, tanto para UF como para CLP.
3. Revisar que los **títulos y subtítulos también tengan importes** cuando corresponde: son filas de consolidación jerárquica, no encabezados decorativos.
4. Usar el filtro **M — VISIBILIDAD** para visualizar las filas con valores. Restablecerlo si se necesita ver todos los grupos y cuentas.
5. Comprobar que una agrupación no incluya dos veces una cuenta por sumar un subtotal y sus propios descendientes.

**Caso de aceptación de agosto — PROYECTO HERNANDO DE AGUIRRE (fila 51 de CAM):**

| Celda | Contenido | Resultado verificado |
| --- | --- | ---: |
| `F51` | EPLAZA VALORES UF | **550.120,96 UF** |
| `G51` | IMPULSA VALORES UF | **0,00 UF** |
| `H51` | TOTAL VALORES UF | **550.120,96 UF** |

Fórmulas emitidas en esa versión: `F51=SUM(F52,F105)`, `G51=SUM(G52,G105)` y `H51=F51+G51`. TASK033R validó **54 títulos CAM** con fórmulas y conciliación. No reutilizar estas referencias como posiciones fijas en otro mes.

## 8. Auditoría y tratamiento de diferencias

En `AUDIT.PH1`, revisar las incidencias detectadas y la justificación de las sumas. Regla aprobada por HUMAN:

- La conciliación principal de subtotales CM se realiza en **G — VALORES UF**, respetando signos y membresía jerárquica.
- Si el valor calculado **no coincide** con el importe original, **conservar el valor fuente, registrar la diferencia y revisarla conjuntamente HUMAN–MORCH antes de formalizar un ajuste o una nueva regla**.
- No inventar contrapartidas ni ajustar silenciosamente.
- Para `TOTALES GENERALES`, se aprobó una tolerancia específica de conciliación de **0,01 UF**; no aplicar esa tolerancia indiscriminadamente a otras cuentas.
- Diferencias en columnas de débitos/créditos deben quedar trazadas, sin confundirlas automáticamente con una diferencia de `VALORES UF`.

El detalle completo de reglas aprobadas está en `04_CONFIG/CRITERIA/PH1_CRITERIA_REGISTER.json` y `03_DOCS/HUMAN/PH1_APPROVED_CRITERIA.md`.

## 9. Checklist de aceptación del usuario

- [ ] Las dos fuentes RAW son las correctas y corresponden al período.
- [ ] El comando PH1 termina satisfactoriamente.
- [ ] Excel abre el resultado sin mensajes de reparación.
- [ ] Existen las cinco hojas esperadas.
- [ ] EPLAZA presenta subtotales y totales correctos.
- [ ] IMPULSA presenta subtotales y totales correctos.
- [ ] CAM muestra importes en títulos y subtítulos, incluida la conciliación UF entre empresas.
- [ ] `VISIBILIDAD_UF` funciona en ambas CM, sin borrar registros.
- [ ] `VISIBILIDAD` funciona en CAM, conservando grupos y cuentas relevantes.
- [ ] `AUDIT.PH1` y `CONTROL` son legibles y no contienen diferencias inexplicadas.
- [ ] El usuario considera satisfactoria la presentación y confirma la aceptación funcional.

**Registro histórico:** el usuario aprobó funcionalmente PH1 después de TASK033R, con 15 criterios conciliados, 14 excepciones históricas resueltas, 54 encabezados CAM verificados y 16 pruebas automatizadas PASS. Este registro es evidencia del caso de referencia, **no certificación automática de ejecuciones futuras**.

## 10. Problemas frecuentes

| Síntoma | Qué revisar |
| --- | --- |
| `PermissionError` al generar XLSX | Cerrar el libro en Excel; revisar bloqueo activo antes de reintentar. No forzar procesos ni borrar locks activos. |
| No se encuentra uno de los RAW | Confirmar período, nombre, extensión `.xlsb` y ruta de entrada configurada. |
| Un subtotal aparece vacío | Revisar columna financiera, fórmula y vinculación del grupo; comparar con CM y RAW. Reportar hoja/celda/cuenta. |
| Una fila desaparece al filtrar | Restablecer `VISIBILIDAD` o `VISIBILIDAD_UF`; filtrar no equivale a borrar. |
| Aparece una diferencia de UF | Conservar fuente, documentar en `AUDIT.PH1` y solicitar revisión HUMAN–MORCH. |
| Fórmulas sin resultado visible | Comprobar recálculo en Excel Desktop; distinguir fórmula emitida de valor efectivamente calculado. |
| Un archivo cambia de SHA-256 | Investigar si hubo regeneración, cambios del contenedor XLSX o diferencias semánticas. No asumir equivalencia solo por pasar tests. |

## 11. Límites y continuidad

- **PH1** finaliza con el Excel consolidado, las dos hojas CM, auditoría, control y aceptación del usuario.
- **PH2** corresponde al traslado/mapeo hacia el Funding Memo y se trabaja separadamente.
- Cambios contables requieren criterios formalizados, versionados y autorizados; la IA puede sugerir, pero no ejecutar reglas contables no aprobadas.
- La aceptación funcional **no autoriza por sí misma** publicar archivos financieros en un repositorio GitHub público.
- El paquete de publicación Git se gestiona mediante allowlist y autorización HUMAN explícita; no ejecutar `git add`, `commit` o `push` por el mero hecho de completar este caso de uso.

## 12. Documentación relacionada

- `03_DOCS/HUMAN/PH1_USER_GUIDE.md` — guía de usuario e instalación/ejecución.
- `03_DOCS/HUMAN/PH1_APPROVED_CRITERIA.md` — criterios aprobados.
- `04_CONFIG/CRITERIA/PH1_CRITERIA_REGISTER.json` — registro estructurado de reglas.
- `03_DOCS/MACHINE/PH1_TECHNICAL_SPEC.md` — contrato técnico y columnas.
- `03_DOCS/ARCHITECTURE/PH1_DATA_FLOW.md` — flujo de datos y dependencias.
- `08_EVIDENCE/REPORTS/KTMA_TASK033R_CAM_RECON_MATRIX.json` — evidencia de conciliación de títulos CAM.

**Mantenimiento del documento:** actualizar este caso de uso cuando cambie la interfaz de ejecución, contrato de hojas, nombres de filtros, criterios autorizados o proceso de aceptación. Revalidar cada cambio contra el motor real antes de darlo por implementado.
