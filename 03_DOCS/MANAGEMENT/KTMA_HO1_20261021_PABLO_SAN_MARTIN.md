# KT.MovemAcc — HO.1 | Continuidad operativa y reanudación segura

**Autor:** Pablo San Martín  
**Fecha de actualización:** 21 de octubre de 2026  
**Versión:** 2026-10-21 — propuesta para aprobación humana  
**Estado:** BORRADOR PARA REVISIÓN; sin instalación en la raíz local  
**Documento estratégico asociado:** `KTMA_HOJA_DE_RUTA_20261021_PABLO_SAN_MARTIN.md` — aprobado por HUMAN.

## 1. Para qué sirve

HO.1 responde a una necesidad práctica: **que una persona o un agente pueda retomar KT.MovemAcc sin reconstruir el contexto completo ni poner en riesgo los archivos financieros**. Contiene identidad del proyecto, qué está aprobado, situación real reportada, dónde buscar información, comprobaciones previas, secuencia para continuar y qué hacer ante un bloqueo.

No es la hoja de ruta ni un nuevo registro de criterios financieros. El estado detallado de frentes corresponde a MR0 y las respuestas aprobadas corresponden a QA.

## 2. Identificación inmediata

| Campo | Referencia |
|---|---|
| Responsable de las decisiones | Pablo San Martín (HUMAN) |
| Proyecto | KT.MovemAcc |
| Raíz de Windows esperada | `C:\01. GitHub\Kumquat.TECH\KT.MovemAcc` |
| Raíz de WSL esperada | `/mnt/c/01. GitHub/Kumquat.TECH/KT.MovemAcc` |
| Rama de experimentación reportada | `experiment/ktma-qa-harness-004` |
| Último identificador de Git informado | `e948336cd790d998e4af6243d00246989404897e` |
| Fase contable | Fase 1: consolidación; fase 1.5: normalización/trazabilidad |
| Informe financiero | Funding Memo, fase 2 |
| Autorización de fase 1 | `RM-GATE-003=ABIERTO` |
| Autorización de Funding Memo | `RM-GATE-004=ABIERTO` |
| Ambiente de desarrollo | Ejecución local Windows/WSL; disponibilidad concreta por comprobar |

**Regla de seguridad:** las rutas son las *esperadas*. Antes de operar, comprobar el directorio físico, la rama y los archivos; no crear carpetas nuevas para compensar una ruta inexistente.

## 3. Resumen de continuidad en menos de cinco minutos

**Primer minuto — Identidad.** Comprobar la raíz física real, el estado de Git y que no se trabaja sobre una ruta Windows malformada dentro del repositorio.

**Segundo minuto — Autoridad.** Leer hoja de ruta aprobada, MR0, `QA_Resume.md` y las normas NTV/Skills efectivamente cargadas. Confirmar que los puntos de aprobación financiera siguen abiertos.

**Tercer minuto — Integridad.** Identificar entradas y salidas financieras protegidas, hashes conocidos, candados activos y archivos nuevos no clasificados. No abrir ni guardar Excel si existe riesgo de modificar libros.

**Cuarto minuto — Situación.** Consultar los informes `KTMA_SPECIALIST_003`, `KTMA_SPECIALIST_002` y `KTMA_NTV_011`; distinguir sus afirmaciones de verificaciones actuales.

**Quinto minuto — Próxima acción.** Continuar con inventario independiente, documentación y análisis de solo lectura. No poblar Funding Memo ni limpiar archivos por intuición.

## 4. Autoridad y reglas ya confirmadas

**Aprobado por HUMAN:** hoja de ruta del 21-10-2026, tres documentos QA aprobados y la definición del período acumulado.

Los reportes contables contienen movimientos acumulados desde el día 0 del proyecto hasta las **23:59** del cierre del último día de cada período. Ejemplo: agosto de 2026 termina el **31-08-2026 a las 23:59**. Esto **no equivale automáticamente** a utilizar cualquier saldo deudor, acreedor o neto: la medida elegida debe justificarse por cada destino del Funding Memo.

**Pendiente:** criterios económicos D01–D08, relaciones contables aprobadas, 32 discrepancias semánticas, disposición de versión histórica fase 1 y limpieza de archivos.

## 5. Dónde está cada cosa

| Recurso | Ubicación o condición |
|---|---|
| `QA.md` | `03_DOCS/HUMAN/QA.md`, según promoción NTV011 |
| `QA_Resume.md` | `03_DOCS/HUMAN/QA_Resume.md`, según promoción NTV011 |
| `QA_SKILLS.MovemACC_QA.md` | `02_SKILLS/INTERNAL/QA_SKILLS.MovemACC_QA.md`, según promoción NTV011 |
| Hoja de ruta vigente | Archivo aprobado en la conversación; ubicación canónica local **por verificar** |
| MR0 | Documento de ejecución; ubicación canónica **por verificar antes de instalar** |
| HO.1 | Documento de continuidad; ubicación canónica **por verificar antes de instalar** |
| Informes SPECIALIST | `08_EVIDENCE/REPORTS/KTMA_SPECIALIST_00*` según reportes |
| Analizadores | `07_TOOLS/` y algunos analizadores históricos dentro de informes, sujeto a inventario |
| Entradas de ejemplo de agosto | `RAW.INPUT/2026.08/` o ubicaciones verificadas del proyecto, **no asumir ruta concreta sin inspección** |
| Salida consolidada de agosto | `OUTPUT/2026.08/CAM2026.08_CONSOL.ALIGN.xlsx` según antecedentes |
| Candidato de Funding Memo | `OUTPUT/2026.08/FM2026.08_VALIDATION.xlsx`, no aprobado para producción |
| Documento de vaciado | `ACC_FM_Sync.md` **previsto, aún no creado ni aprobado** |
| Carpeta Descargas | `C:\Users\aazcl\Downloads`, temporal y no canónica |

## 6. Estado informado que no debe perderse

### Consolidación contable

Motor de fase 1 autónomo informado. La operación nativa en Windows y el procesamiento real de octubre deben comprobarse. El archivo histórico aceptado de agosto cuyo hash comenzaba por `38a3f` no está actualmente disponible según SPECIALIST; no restaurar ni reemplazar nada sin autorización.

### Diferencias de jerarquía

32 comparaciones de fase 1 frente a fase 1.5 conservan `FAIL`. SPECIALIST atribuye la causa a diferencias semánticas de jerarquía de Impulsa. No reetiquetar esos resultados como correctos por el hecho de compartir causa.

### Funding Memo

De los 72 destinos: 15 están técnicamente verificados, 18 ambiguos, 37 sin correspondencia y 2 propuestos. Ninguno tiene aprobación económica HUMAN. Las celdas E49, E52 y E54 de Eplaza son técnicamente verificables; E41 permanece ambigua. No escribir el candidato.

### Integridad del proyecto

RORCH (NTV011) informó **cero** rutas malformadas. SPECIALIST (003) informó **32** archivos con rutas malformadas y **seis** archivos de prueba en `BACKUPS`. Son resultados contradictorios y requieren verificación de las mismas rutas, mismo alcance y mismo instante. No considerar limpio el repositorio de forma global.

## 7. Reanudación técnica segura

1. Comprobar manualmente en el entorno autorizado el directorio real, la rama y el identificador Git. **No cambiar de rama**.
2. Revisar `git status` y registrar archivos modificados o sin seguimiento. No ejecutar `git clean`, `reset`, `commit`, `push` ni herramientas que alteren índices.
3. Comprobar existencia y hashes de libros financieros protegidos. Utilizar lectura que no reescriba el libro. Respetar archivos de bloqueo activos.
4. Leer la hoja de ruta aprobada, MR0 y QA vigente. Comprobar que la Skill interna se descubre y ejecuta efectivamente.
5. Verificar la clasificación de cada artefacto relevante: **canónico, evidencia inmutable, derivado reproducible, descartable o retenido hasta clasificar**.
6. Ejecutar solo diagnósticos de lectura y generar nueva evidencia en ubicaciones previamente autorizadas.
7. Antes de modificar, declarar alcance, pruebas positivas y negativas, exclusiones, rutas protegidas, autorizaciones, recuperación y verificación independiente.
8. Concluir con un resumen breve de diferencias respecto del estado anterior y el siguiente paso ejecutable.

### Comandos de consulta — ejemplos, no ejecución autorizada automáticamente

Desde **PowerShell en Windows**, posicionarse en la raíz esperada solo después de verificar la ruta:

```powershell
Set-Location -LiteralPath 'C:\01. GitHub\Kumquat.TECH\KT.MovemAcc'
git status --short
git branch --show-current
git rev-parse HEAD
```

Desde **bash en WSL**:

```bash
cd '/mnt/c/01. GitHub/Kumquat.TECH/KT.MovemAcc'
git status --short
git branch --show-current
git rev-parse HEAD
```

Estas comprobaciones no aprueban por sí solas futuras operaciones. No asumir que la sintaxis y los ejecutables disponibles en un equipo son universales.

## 8. Flujo de trabajo contable conocido — no reejecutar sin preflight

En antecedentes operativos se registró un modo WSL antiguo de fase 1:

```bash
PYTHONPATH=src 90_RUNTIME/venv_clean/bin/python -m kt_movemacc ph1 --period 2026.08 --out-dir 90_RUNTIME/ho1_ph1_probe
```

También se informó una interfaz de comandos independiente:

```text
python -m kt_movemacc.cli ph1 --period AAAA.MM --out-dir RUTA_DE_SALIDA
```

**Son interfaces informadas de momentos distintos; no asumir equivalencia ni vigencia sin verificar `--help`, entorno y código actual.** No dirigir la salida al archivo aceptado ni regenerar libros protegidos como parte de una prueba rutinaria.

La fase 2 de Funding Memo **no está autorizada para poblamiento**; `ACC_FM_Sync.md` será la futura especificación de esa operación.

## 9. Qué hacer ante situaciones anómalas

| Situación | Acción segura |
|---|---|
| Ruta de Windows aparece concatenada dentro de WSL | Detener escritura, validar traducción de ruta y límites de directorio |
| Aparece una carpeta `C` bajo la raíz | Clasificar como desconocido retenido; levantar inventario exacto |
| Archivo de bloqueo `~$` de Excel visible | Suponer uso activo hasta demostrar lo contrario; no eliminar |
| Diferencia de hash en un financiero | Detener operaciones con el archivo, preservar evidencia y solicitar disposición |
| Una prueba modifica una salida de agosto | Detener y documentar; no restaurar silenciosamente |
| Resultado anunciado como `PASS` sin comprobación | Clasificar como información no verificada |
| Falta autorización HUMAN | Continuar solo con frentes independientes de lectura |
| Desaparece material de Descargas | Consultar custodia duradera; no crear sustitutos ficticios |
| Dos políticas o documentos se contradicen | Registrar conflicto y autoridad; no elegir arbitrariamente |

## 10. Operaciones expresamente prohibidas sin autorización

No sobrescribir RAW, libros consolidados, Funding Memo, SQLite ni evidencias históricas. No regenerar una salida protegida mediante pruebas de rutina. No borrar o mover artefactos retenidos hasta clasificar. No agregar rutas ajenas a la raíz bajo nombres malformados. No instalar ni actualizar paquetes globalmente. No efectuar acciones Git con efectos de escritura. No proclamar cerrados `RM-GATE-003` o `RM-GATE-004`.

## 11. Entrega de un turno a otro

El responsable saliente debe registrar, de forma breve pero comprobable:

| Campo | Contenido necesario |
|---|---|
| Estado de ejecución | Qué se ejecutó realmente y qué quedó pendiente |
| Ruta y versión | Raíz, rama, HEAD, entradas/salidas y huellas pertinentes |
| Documentos | Hoja de ruta, MR0, HO.1, QA y Skill efectiva |
| Evidencia | Ubicación durable y método de verificación |
| Cambios | Todos los archivos creados, modificados, trasladados o eliminados |
| Fallos | Fallos aún abiertos y alcance |
| Autorizaciones | Decisiones HUMAN exactas vigentes y las que faltan |
| Siguiente paso | Una acción concreta segura con responsable y prerrequisitos |

## 12. Próximo punto de reanudación recomendado

**Prioridad inmediata:** conciliar la realidad del sistema de archivos con un inventario reproducible y consolidar la hoja de ruta aprobada, MR0 y HO.1 sin sobrescritura de versiones previas.

**En paralelo:** continuar la investigación de los criterios financieros por SPECIALIST en modo de solo lectura, preparar `ACC_FM_Sync.md` como borrador y organizar preguntas económicas para Pablo.

**No hacer aún:** limpieza destructiva, modificación del Funding Memo, reclasificación de los 32 fallos o cierre de puntos de aprobación.

## 13. Control de cambios y custodia

Versión propuesta generada a partir de la hoja de ruta aprobada y los estados reportados. Antes de convertirla en documento oficial, RORCH debe **confrontar el HO.1 existente y su posible manual operativo**, conservar instrucciones locales vigentes que no se contradigan y presentar diferencias verificables. Este borrador no reemplaza automáticamente ninguna fuente canónica.
