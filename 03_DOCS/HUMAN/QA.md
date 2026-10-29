<!-- KT.MovemAcc / HISTORICAL RECONSTRUCTION / REVIEW COPY -->
# QA.md — Registro de preguntas, respuestas, definiciones y asuntos pendientes

**Proyecto:** KT.MovemAcc  
**Corte documental:** 2026-10-21  
**Estado:** `DRAFT_FOR_HUMAN_REVIEW` — no instalado ni oficializado  
**Autoridad:** respuestas explícitas HUMAN > documentación oficialmente adoptada > evidencia financiera verificada > informes de ejecutores > propuestas MORCH.  
**Fundamento metodológico:** `SKILLS.QA.TRANSVERSAL.md` entregada por HUMAN, aplicada como referencia de rigor de evidencia y convergencia, sin sustituir NTV ni una Skill local oficialmente efectiva.  

## 00. Propósito, alcance y leyenda

Este documento reconstruye **las preguntas, respuestas y acuerdos materialmente identificables en la conversación disponible** y en los resultados de RORCH/SPECIALIST compartidos. **No es una transcripción literal exhaustiva de todos los intercambios históricos del proyecto**: cuando no existe respuesta HUMAN explícita se consigna `PENDIENTE`, sin completarla por inferencia. Los hitos reportados por ejecutores son evidencia `REPORTED_ONLY` hasta cotejo independiente. El registro distingue:

- `HUMAN_CONFIRMED`: decisión expresada por HUMAN en esta conversación.
- `HUMAN_APPROVED_DOC`: documento cuya aprobación fue declarada explícitamente por HUMAN; la ejecución de promoción puede estar solo reportada.
- `REPORTED_ONLY`: afirmación de RORCH/DSH/Codex sin comprobación independiente aquí.
- `SPECIALIST_EVIDENCE`: hallazgo documentado por SPECIALIST; no equivale a aprobación HUMAN.
- `MORCH_PROPOSAL`: recomendación aún no adoptada.
- `OPEN`: pregunta sin criterio aprobado.
- `CONFLICT`: dos fuentes no reconciliadas.

Las fechas y los nombres de artefactos de ejecución son referencias de trazabilidad. **No inferir que un archivo ubicado en Downloads esté disponible mañana ni que una ruta Windows reportada exista efectivamente**. Verificar siempre el ROOT, ruta y hash. Los cierres de tareas **no** cierran automáticamente objetivos ni gates.

## 01. Gobierno, roles y metodología

| ID | Pregunta o cuestión | Respuesta / acuerdo comprobable | Estado / evidencia |
|---|---|---|---|
| Q-001 | ¿Quién decide criterios financieros, permisos y aprobación? | HUMAN conserva la autoridad final. MORCH propone y coordina; ningún agente se autoaprueba. | HUMAN_CONFIRMED |
| Q-002 | ¿Qué significa SPECIALIST? | **Codex Desktop + NTV**; no es el propio ChatGPT conversacional. | HUMAN_CONFIRMED; corrección explícita |
| Q-003 | ¿Qué hace RORCH/DSH? | Ejecuta/orquesta tareas y agentes bajo permisos; no debe ser necesario para correr PH1 cada mes. | HUMAN_CONFIRMED para autonomía PH1 |
| Q-004 | ¿Qué papel tiene MORCH? | Metaorquestación, objetivos, DAG, coordinación, evaluación y convergencia NTV. | ACUERDO_OPERATIVO |
| Q-005 | ¿NTV se limita a QA y paralelismo? | **No**. Debe incluir orden, higiene de ROOT, carpetas/subcarpetas, propiedad de artefactos, retención, trazabilidad y verificaciones cruzadas. | HUMAN_CONFIRMED |
| Q-006 | ¿Puede declararse PASS por un mensaje `SUCCESS`? | No: deben distinguirse claim, evidencia, pruebas ejecutadas, resultado y autorización HUMAN. | QA transversal, requisito metodológico |
| Q-007 | ¿Qué configuración se usa en SPECIALIST? | Base histórica informada: Standard mode, Workspace Write y no commands; en SPECIALIST_001 se concedió excepción acotada de comandos para análisis y escritura de evidencias autorizadas. No extrapolar a tareas futuras. | HISTÓRICO / EXCEPCIÓN_LIMITADA |
| Q-008 | ¿Se autorizan commits, push, merge, reset o limpieza Git? | No en los ciclos NTV aquí reportados, salvo autorización HUMAN futura precisa. | RESTRICCIÓN_VIGENTE |
| Q-009 | ¿Puede SPECIALIST usar lecturas Python/PowerShell de Excel/SQLite? | Sí, **solo cuando HUMAN habilita comandos acotados por tarea**; originales financieros sin escritura. | HISTÓRICO AUTORIZADO en SPECIALIST_001/002/003 |
| Q-010 | ¿Cuál es el sentido de las Skills transversales? | Políticas reutilizables; distribución entre ROOTs corresponde al mecanismo/propietario autorizado (SkillsMachine), no a sincronización unilateral por RORCH. | ACUERDO_OPERATIVO |

## 02. Naturaleza de PH1, fuente contable y período

| ID | Pregunta o cuestión | Respuesta / acuerdo comprobable | Estado / evidencia |
|---|---|---|---|
| Q-011 | ¿Qué representan los reportes contables mensuales? | **Movimientos acumulados desde el día 0 del proyecto hasta el último día del período contable a las 23:59 horas**. Agosto 2026 comprende desde el origen hasta **2026-08-31 23:59**. **NO son exclusivamente los movimientos de agosto**. | **HUMAN_CONFIRMED 2026-10-21** |
| Q-012 | ¿Qué base temporal debe utilizarse en PH1→Funding Memo? | La fuente es acumulada hasta la fecha de corte de cada reporte. La selección financiera específica saldo/movimiento, ajustes o reversiones por partida aún debe documentarse; no restar agosto de julio por defecto. | HUMAN_CONFIRMED en temporalidad; criterio por partida OPEN |
| Q-013 | ¿Cuál es el formato de entrada? | Dos mayores originales `.xlsb`, no CSV reconstruido. | Procedimiento PH1 documentado; requiere validación real de nuevos períodos |
| Q-014 | ¿Dónde depositar los mayores de octubre 2026? | `RAW.INPUT/2026.10/` dentro de `C:\01. GitHub\Kumquat.TECH\KT.MovemAcc`. | DISEÑO_OPERACIONAL |
| Q-015 | ¿Cuáles son los nombres esperados en octubre? | `Mayor Inmob. Eplaza 2026 10 V 1.xlsb` y `Mayor Grupo Impulsa 2026 10 V 1.xlsb`; comprobar convención real contra CLI y archivos recibidos. | CONVENCIÓN_PROPUESTA Y DOCUMENTADA |
| Q-016 | ¿Cuál es el período de prueba histórica? | Agosto 2026, código `2026.08`; hojas fuente originales denominadas `CUENTAS DE MAYOR AGOSTO 2026`. | DOCUMENTADO / REPORTED_ONLY |
| Q-017 | ¿Se puede modificar/normalizar silenciosamente el XLSB fuente? | No; entradas privadas originales, hash y linaje preservados. | CONTROL_FINANCIERO |
| Q-018 | ¿Se puede tratar cero como celda vacía? | No. SUBTITLE_1 puede contener cero real; SUBTITLE_2 debe tener celdas numéricas verdaderamente vacías. | HUMAN_APPROVED accounting semantics |
| Q-019 | ¿Cómo se clasifican las filas? | ITEM: cuenta válida; SUBTITLE_1: subtotal sin cuenta con valores numéricos; SUBTITLE_2: agrupador sin importes; TITLE: encabezado autorizado con semántica propia. | HUMAN_APPROVED accounting semantics |
| Q-020 | ¿Puede bastar la glosa para identificar una cuenta? | No: misma glosa puede repetirse en distintas entidades o jerarquías; considerar código, entidad, padre y medida. | DECISIÓN_METODOLÓGICA |
| Q-021 | ¿Qué es `uf_al_bce`? | Parámetro de conversión CLP/UF del Banco Central de Chile, no una cuenta ITEM. | DOCUMENTADO |
| Q-022 | ¿Qué origen/cierre financiero se usa para cada nuevo mes? | Fuente desde día 0 hasta fin de mes a las 23:59; los calendarios de cierre, cortes excepcionales y ajustes posteriores siguen sin política formal aquí. | HUMAN_CONFIRMED + OPEN |

## 03. PH1 autónomo, producto y experiencia de usuario

| ID | Pregunta o cuestión | Respuesta / acuerdo comprobable | Estado / evidencia |
|---|---|---|---|
| Q-023 | ¿Debe HUMAN pedir a RORCH cada ejecución mensual? | **No**. PH1 debe operar sin IA, DSH, ChatGPT ni agentes. | HUMAN_CONFIRMED |
| Q-024 | ¿Qué secuencia de producto está aprobada? | **Fase A: motor PH1 autónomo → Fase B: vaciado Funding Memo → Fase C: `.exe` o Docker**. | HUMAN_CONFIRMED |
| Q-025 | ¿Debe haber GUI o Docker antes de Funding Memo? | No; se desarrollan después. | HUMAN_CONFIRMED |
| Q-026 | ¿PH1 ya requiere Excel COM, WSL o internet? | RORCH reportó `REQUIRES_EXCEL_COM=false`, `REQUIRES_WSL=false`, `REQUIRES_NETWORK=false`, `REQUIRES_PYTHON=true`. | REPORTED_ONLY; Windows nativo no certificado |
| Q-027 | ¿Cuál es el comando CLI comunicado? | `python -m kt_movemacc.cli ph1 --period YYYY.MM --out-dir PATH`. Otro documento HO.1 presenta `python -m kt_movemacc ph1 ...`; resolver entrypoint efectivo en Windows antes de publicar instrucciones nuevas. | CONFLICTO_DOCUMENTAL / VALIDACIÓN_PENDIENTE |
| Q-028 | ¿Dónde debería encontrarse el Excel generado de octubre? | Convención objetivo: `OUTPUT/2026.10/CAM2026.10_CONSOL.ALIGN.xlsx`; staging y validación previos, sin sobrescribir salidas aceptadas. | DESTINO_ESPERADO; no ejecución real octubre |
| Q-029 | ¿Se probó octubre con XLSB contables reales? | No; `OCTOBER_REAL_DATA_VALIDATION=PENDING`. Prueba sintética reportada. | REPORTED_ONLY |
| Q-030 | ¿Está documentado el uso básico? | HUMAN aprobó `USECASE_PHASE1.md`; RORCH informó instalación byte-identical en `03_DOCS/HUMAN/UseCase_PHASE1.md` con SHA-256 `589e7dff...18334`. | HUMAN_APPROVED_DOC; instalación REPORTED_ONLY |
| Q-031 | ¿Se sincronizaron README, Roadmap y HO.1? | NTV009B listó solamente el Use Case entre documentos modificados; sincronización integral no demostrada. | OPEN |
| Q-032 | ¿La ejecución nativa Windows fue probada? | `WINDOWS_NATIVE_TEST_EXECUTED=false`, pendiente. | OPEN |

## 04. PH1/PH1.5, reconciliación y artefactos

| ID | Pregunta o cuestión | Respuesta / acuerdo comprobable | Estado / evidencia |
|---|---|---|---|
| Q-033 | ¿Qué es PH1.5? | SQLite local para consulta y trazabilidad, sin sustituir al workbook PH1. | DOCUMENTADO |
| Q-034 | ¿Se autoriza modificar SQLite durante auditorías? | No; usar `mode=ro`/lectura inmutable; importaciones por período solo con autorización. | CONTROL |
| Q-035 | ¿Se aceptó el hash histórico PH1? | Histórico comunicado: SHA-256 `38a3ffe730a2d1faa1da63fdd085d4ef4d1330ff73fa25622a73fa50fbbfcfd3`; SPECIALIST indicó que esos bytes originales no están disponibles actualmente. | HISTÓRICO / OPEN autoridad de bytes |
| Q-036 | ¿Por qué cambia el hash de un `.xlsx`? | Abrir y guardar con Excel puede cambiar metadatos aunque los valores sigan iguales; la regeneración por tests es distinta y debe estar autorizada. Abrir sin guardar no prueba cambio del original. | EXPLICACIÓN_TÉCNICA |
| Q-037 | ¿Las pruebas pueden regenerar outputs financieros canónicos? | No; `ensure_output` se aisló tras regeneraciones observadas. Hash estable antes/después es condición de control, pero no valida por sí mismo contenido financiero. | REPORTED_ONLY / CONTROL |
| Q-038 | ¿Cuál es el hash actual informado del PH1 divergente? | `5acba7c7c09b743f53b7d5734a9042712d8116a1aaab9df0d54349218dbce5ec`. No promover ni revertir automáticamente. | REPORTED_ONLY |
| Q-039 | ¿Qué pasó con 32 fallas de conciliación? | SPECIALIST_002 rastreó 32/32 como `SOURCE_SEMANTIC_MISMATCH`, relacionadas con cuentas Impulsa `120411`, `120511`, `220411` y padres; **siguen FAIL** hasta decisión y revalidación. | SPECIALIST_EVIDENCE / OPEN |
| Q-040 | ¿Implica esto diferencias monetarias reales? | SPECIALIST no identificó discrepancias financieras reales en estos casos; tampoco demostró identidad integral con los bytes aceptados históricos. | SPECIALIST_EVIDENCE, NO_APROBACIÓN |
| Q-041 | ¿Se cierran RM-GATE-003 y RM-GATE-004 automáticamente? | No, permanecen **OPEN**. | HUMAN_GOVERNANCE |
| Q-042 | ¿La integración QA es global en DSH? | No; RORCH reportó wrapper **LEVEL_2 PROJECT_LOCAL**, 62/62 tests y anti-bypass locales; sin hook global. | REPORTED_ONLY |

## 05. Funding Memo: fuente, estructura, mapeos y decisiones

| ID | Pregunta o cuestión | Respuesta / acuerdo comprobable | Estado / evidencia |
|---|---|---|---|
| Q-043 | ¿Es `FM2026.08_VALIDATION.xlsx` el FM de producción aprobado? | No. SPECIALIST lo clasifica como `VALIDATION_CANDIDATE / PROTOTIPO_NO_VALIDADO`; sin autorización de población. | SPECIALIST_EVIDENCE |
| Q-044 | ¿Debe protegerse la columna C? | Análisis preliminar: columna C refleja V0/históricos; no ejecutar escritura nueva allí hasta validación de autoridad y criterio. | MORCH_PROPOSAL, NO HUMAN_APPROVED |
| Q-045 | ¿Qué funciones tienen D, E y F? | Análisis preliminar: D total y E/F entidades; hay fórmulas como D8=E8+F8. No suponer patrón uniforme en todas las filas. | EVIDENCIA_REVISIÓN, no regla global aprobada |
| Q-046 | ¿Son válidas las diez propuestas `FM!C8...C27` del NTV010? | No aprobadas; no cuentan con fuente contable suficiente y arriesgan afectar V0. | SPECIALIST/MORCH review, OPEN |
| Q-047 | ¿Cuántos destinos examinó SPECIALIST_002? | 72: 38 ACCOUNTING_INPUT, 20 MANUAL_HARDNUMBER, 6 FORMULA, 4 DERIVED_RESULT y 4 HUMAN_DECISION_REQUIRED, **según versión _002**. | SPECIALIST_EVIDENCE histórico |
| Q-048 | ¿Cambió la clasificación en SPECIALIST_003? | Sí: 42 candidatos contables, 15 `VERIFIED_TECHNICAL`, 18 ambiguos, 9 unmapped; 30 no contables (20 fuente externa, 8 desconocidos, 2 derivados propuestos). | SPECIALIST_EVIDENCE versión _003 |
| Q-049 | ¿Cuántas correspondencias financieras aprobadas? | **Cero**. `VERIFIED_TECHNICAL` no significa `HUMAN_APPROVED`. | SPECIALIST_EVIDENCE |
| Q-050 | ¿Qué ocurrió con E41, E49, E52, E54? | SPECIALIST_003 informa E49, E52 y E54 verificadas técnicamente; E41 sigue ambigua. E52 observó cero real, no un valor por defecto. | SPECIALIST_EVIDENCE |
| Q-051 | ¿Puede utilizarse una cuenta de Impulsa por similitud con Eplaza? | No; requiere evidencia de asignación económica al proyecto y entidad; glosa genérica no es suficiente. | MORCH_PROPOSAL, decisión D02 OPEN |
| Q-052 | ¿Cuál es el criterio definitivo de construcción E38? | Residual excluyente de E37/E39/E40/E41 por evaluar; no aprobado. | OPEN D03 |
| Q-053 | ¿Cuál es el criterio definitivo del costo financiero E53? | Residual y exclusiones de financiamiento de terreno y pólizas de ventas verdes por evaluar; no aprobado. | OPEN D04 |
| Q-054 | ¿Qué usar en ventas y capital preferente (filas 8–19 y 76)? | Buscar fuente de negocio, fecha de reconocimiento, bruto/neto y asignación por entidad; no inventar hardnumbers. | OPEN D06 |
| Q-055 | ¿Se pueden copiar valores en E/F61, 65 y 69 como fórmulas existentes? | No: SPECIALIST_003 señala que esas celdas están vacías, sin fórmulas; definir IVA, fee y costo capital preferente antes de escribir. | OPEN D07 |
| Q-056 | ¿Qué fórmula de retorno está documentada en V0? | C77=C70/C75; no implica criterio aprobado para E/F75–77. | SPECIALIST_EVIDENCE / OPEN D08 |
| Q-057 | ¿Qué fórmulas sí existen en E/F? | Ejemplos reportados: E63=E22-E59, E67=E63-E65, E70=E67-E69, E73=E63/E59 y equivalentes F. | SPECIALIST_EVIDENCE |
| Q-058 | ¿Quién debe aprobar las reglas fuente→destino? | HUMAN; SPECIALIST construye evidencia y MORCH converge. | HUMAN_GOVERNANCE |
| Q-059 | ¿Se puede poblar el Funding Memo ahora? | No; falta aprobación de reglas, autoridad del archivo y QA final. | OPEN / NO AUTORIZADO |

## 06. Ocho principios financieros abiertos desde SPECIALIST_003

| ID | Principio | Estado y detalle |
|---|---|---|
| D01 | Reconocimiento temporal | **Parcialmente resuelto:** HUMAN confirma acumulación desde día 0 a fin de período 23:59. Sigue por resolver la política contable específica por destino: saldo vs movimiento acumulado, costos activados vs resultados, ajustes. |
| D02 | Asignación de entidad | OPEN: distinguir proyecto/EPLAZA/IMPULSA con evidencia, evitar replicación automática. |
| D03 | Partición construcción | OPEN: E38 residual mutuamente excluyente y tratamiento E37/E39/E40/E41. |
| D04 | Partición financiera | OPEN: E53 residual; exclusiones financiamiento terreno y pólizas. |
| D05 | Cuatro casos Eplaza | PARCIAL: E49/E52/E54 verificación técnica; E41 ambiguo. Adopción financiera pendiente. |
| D06 | Supuestos comerciales | OPEN: fuentes, bruto/neto, corte, asignación y financiamiento. |
| D07 | IVA, fee, capital preferente | OPEN: bases, tasas, devengo, tiempo, impuestos, redondeos y capitalización. |
| D08 | Capital y retorno | OPEN: capital requerido, numerador, denominador y fecha de corte. |

## 07. Organización de carpetas, documentos y Skills

| ID | Pregunta o cuestión | Respuesta / acuerdo comprobable | Estado |
|---|---|---|---|
| Q-060 | ¿Dónde deben quedar entregables descartables? | Directorio **real** `C:\Users\aazcl\Downloads`, borrado regularmente (24 h). No debe conservar evidencia única. | HUMAN_CONFIRMED |
| Q-061 | ¿Qué problema de ruta persiste? | Árbol incorrecto dentro del repo: `C:\01. GitHub\Kumquat.TECH\KT.MovemAcc\C\Users\aazcl\Downloads`. NTV010B fue propuesto y **no ejecutado**. | HUMAN_REPORTED / OPEN |
| Q-062 | ¿Se autorizó borrar el árbol malformado? | HUMAN expresó intención de eliminarlo por descartable, pero los ciclos de ejecución posteriores reservaron eliminación para inventario y autorización exacta. **No hay constancia de limpieza ejecutada**. | OPEN_QUIEN/ALCANCE |
| Q-063 | ¿Pueden guardarse tests desechables en `08_EVIDENCE/BACKUPS`? | Debe corregirse: backups no es temp. SPECIALIST_003 reportó seis archivos de prueba retenidos; sin eliminación autorizada. | OPEN HIGIENE |
| Q-064 | ¿Qué hacer con bloqueo `~$...` de Excel? | No borrarlo mientras esté activo; solo confirmar cierre/inactividad antes de operar. | CONTROL |
| Q-065 | ¿Las dos Skills QA están aprobadas? | Sí, HUMAN aprobó contenidos exactos; RORCH reportó instalaciones en `02_SKILLS/TRANSVERSAL/SKILLS.QA.TRANSVERSAL.md` y `02_SKILLS/INTERNAL/SKILLS.QA.KT.MovemAcc.md`. | HUMAN_APPROVED; runtime discovery en Codex CONFLICT |
| Q-066 | ¿SPECIALIST confirmó carga efectiva de Skills? | No; reportó documentos candidatos internamente / discovery no probada, pese a instalación informada por RORCH. Resolver metadata/status y mecanismo de carga, no repetir aprobación HUMAN. | CONFLICT |
| Q-067 | ¿Debe NTV inventariar carpetas y limpieza antes de crear outputs? | Sí, con owner, clasificación, retención, side-effect allowlist, ubicación real, inventario residual, rollback y autorizaciones. | HUMAN_CONFIRMED |
| Q-068 | ¿Es válido guardar scripts Python permanentes entre informes? | Deben clasificarse y ubicarse según política del ROOT; SPECIALIST_002 usó `07_TOOLS`, mientras analizadores previos quedaron en REPORTS; no mover sin autorización. | OPEN HIGIENE |

## 08. Hitos y discrepancias de informes (no equivalen a preguntas contestadas)

| Ciclo | Hecho reportado | Precaución |
|---|---|---|
| NTV004–005A | Tests regeneraron workbook PH1 y JSON canónicos. | La integridad de escritura falló aunque tests PASS. |
| NTV005B | 52 tests, hashes protegidos estables en esa ejecución. | No demuestra identidad con hash histórico PH1. |
| NTV006 | 58 tests, wrapper L2 local. | No enforcement global DSH. |
| NTV007 | 62 tests; 14/14 bypass bloqueados según RORCH. | Evidencia de alcance local, no todos los caminos futuros. |
| NTV008 | Skills QA reportadas instaladas, hashes coincidentes. | Especialista posteriormente disputa estatus en runtime. |
| NTV009A | CLI independiente de IA, 62 tests. | Prueba Windows nativa pendiente. |
| NTV009B | USECASE aprobado reportado como oficial y byte-identical. | Sin sincronización integral de otros documentos demostrada. |
| NTV010 | Matriz inicial de 10 destinos en columna C. | Propuesta incompleta, sin aprobación. |
| SPECIALIST_001 | 6.922 celdas, 498 fórmulas, 32 FAIL, 72 destinos pendientes. | Evidencia sin aprobación de mapping. |
| SPECIALIST_002 | 32 casos clasificados, 72 destinos categorizados. | FAIL semánticos permanecen. |
| SPECIALIST_003 | 15 mapeos verificables técnicamente, 18 ambiguos, 9 sin mapping. | 0 `HUMAN_APPROVED`; QA I2 interno. |

## 09. Contradicciones y preguntas abiertas prioritarias

1. **Temporalidad:** regla acumulativa aprobada; precisar medida/atribución para cada partida y tratamiento de ajustes.
2. **32 FAIL:** autoridad semántica para filas padre/repetición y verificación PH1/PH1.5 sin fabricar PASS.
3. **15+18+9 mapeos contables:** autorizar decisiones de fuente, entidad, composición, signo y período bajo D01–D05.
4. **30 destinos no contables:** confirmar autoridades de supuestos, cálculo de impuestos/fees y capital/retorno bajo D06–D08.
5. **Modelo canónico:** `FM2026.08_VALIDATION.xlsx` no está aprobado para producción; identificar template/modelo final.
6. **PH1 original:** bytes del hash aceptado `38a3ff...` no encontrados, no reconciliados con la copia actual divergente.
7. **Rutas:** erradicar escritura a árbol Windows malformado; inventariar/quarantinar antes de borrar.
8. **Skills QA:** HUMAN aprobó; completar reconciliación de metadata y carga real en Codex.
9. **PH1 Windows:** verificar comando PowerShell nativo, sin depender de WSL/DSH.
10. **Documentación:** sincronizar Roadmap/README/HO.1 por referencias, sin alterar Use Case aprobado silenciosamente.

## 10. Fuentes y política de actualización

**Fuentes directas:** intercambios HUMAN de esta conversación, `SKILLS.QA.TRANSVERSAL.md` adjunta, informe SPECIALIST_002 citado por HUMAN, brief `KTMA_SPECIALIST_003_FINANCIAL_RULE_DECISION_BRIEF.md` transcrito por HUMAN, reportes terminales NTV004–010A y SPECIALIST_001–003 compartidos. Referencias canónicas indicadas por los ejecutores solo se aceptan tras comprobación de existencia/ruta/hash.  
**Actualización:** añadir una nueva fila Q-ID por respuesta o pregunta material; nunca sobrescribir respuestas previas: actualizar `current_status` y vincular supersesión. Toda decisión HUMAN nueva debe reflejarse simultáneamente en `QA_Resume.md`, con source/autoridad/impactos. Los puntos sin respuesta permanecen `OPEN`.
