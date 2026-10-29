# MR.0 — Integrated Management Review | KT.MovemAcc

**Revisión:** RECONCILED-TASK060 · **Fecha:** 2026-10-19 · **Estado:** CURRENT_STATE_RECONCILED_HUMAN_GATES_PENDING · **Fuente:** TASK047–TASK060, documentos MR.0 originales, Skill `MR0_Skiils.md`.

## 1. Executive status
**STATUS=NOT_READY_FINANCIAL_DIFFERENCES.** PH1 y PH1.5 fueron aceptados por HUMAN y publicados. Los documentos TASK047–049 fueron rechazados históricamente; TASK054 preparó reemplazos candidatos, TASK055 los adoptó localmente sin publicación Git, TASK058 cerró `RM-GATE-002` sólo para infraestructura y TASK060 reconcilió el estado actual. La matriz TASK060 preserva 32 diferencias Excel↔SQLite y 354 controles `NOT_TESTABLE`; `RM-GATE-003/004/005` siguen abiertos y PH2 no está autorizado.

## 2. Scope and authority
Alcance: producto, contabilidad, arquitectura, calidad, seguridad, operaciones, datos y continuidad. Modelo de autoridad: HUMAN > MORCH (Meta-Orchestrator) > RORCH (Runtime Orchestrator) > EXE. Solo HUMAN aprueba publicaciones, cambios de criterios, upgrades y ejecución bloqueada. Revisión documental no implica aprobación de las recomendaciones.

## 3. Current state
- **Publicado:** `PSM44/KT.MovemAcc`, `main`, commit `e948336cd790d998e4af6243d00246989404897e` (verificado independientemente en GitHub durante TASK046); sincronización local/remota `0/0` verificada en TASK052 (`HEAD` local y `origin/main` = `e948336cd790d998e4af6243d00246989404897e`).
- **PH1:** generación de workbook de consolidación, 15 criterios contables; SHA del workbook aceptado `38a3ffe730a2d1faa1da63fdd085d4ef4d1330ff73fa25622a73fa50fbbfcfd3` (evidencia histórica, no regenerar).
- **PH1.5:** base local `DATA/KTMA.sqlite`, esquema 1, agosto 2026; hash `b5f6b6eae6dcb2f1273f8e5d1706b6db30e52d9250ad148b68e88881ffac60d0` e integridad `ok` verificados read-only en TASK052; schema_version observado `18`.
- **Continuidad e infraestructura:** los cinco archivos `00_BOOTSTRAP/MORCH.*` fueron adoptados localmente en TASK055; TASK056/TASK057 verificaron la arquitectura Windows financiera + WSL2; HUMAN cerró `RM-GATE-002=CLOSED_INFRASTRUCTURE_ONLY` en TASK058. La aceptación financiera `RM-GATE-003` permanece abierta.

## 4. Evidence reviewed
| Evidencia | Afirmación soportada | Calidad / límite |
|---|---|---|
| Commit GitHub `e948336...` | Ocho archivos PH1.5 publicados | Existencia y contenido contrastados en tarea previa; no prueba runtime local |
| TASK044, TASK046 | 15 criterios / 54 títulos reconciliados, PH1 SHA preservado | Histórica, no reevaluada en MR.0 |
| TASK048 + TASK052 | SQLite integrity `ok`, hash SQLite y HEAD local/remoto confirmados read-only en TASK052; Python 3.13.12 WSL reportado en TASK048 | TASK052 no ejecutó pruebas Windows ni regeneró PH1/PH1.5 |
| TASK055–TASK060 | Bootstrap adoptado localmente, arquitectura Windows+WSL2 aprobada, `RM-GATE-002` cerrado sólo infraestructura, evidencia financiera TASK060 | No implica cierre automático de `RM-GATE-003` |
| `MR0_DECISION_REGISTER.md`; `MR0_RISK_REGISTER.md` | Decisiones y riesgos propuestos | Registro de gestión, no autorización |
| `HO1_CANONICAL_OPERATIONAL_CONTINUITY.md`; `HO1_RUNBOOK.md` | Procedimientos documentados | TASK048 rechazado por contrato HO.1 incompleto |
| Skills originales `MR0_Skiils.md`, `HO.1_Skiils.md`, `ROADMAP.md`, `ROADMAP_Skills.md` | Reglas de aceptación | Verificadas en paquete TASK051 |

## 5. Decisions accepted
- HUMAN aceptó PH1 y PH1.5 y autorizó su publicación controlada, ya ejecutada.
- HUMAN rechazó los entregables MR.0, HO.1 y Roadmap anteriores y autorizó preparar **versiones corregidas separadas** con unión de reglas compatibles; no autorizó sobrescribir originales ni publicar.
- HUMAN fijó la secuencia de gestión → actualización OmniRoute/DSH → reanudación, condicionada a aprobación de documentos y gates.
- HUMAN aprobó la arquitectura Windows financiera + WSL2 y cerró `RM-GATE-002` sólo para interoperabilidad de infraestructura en TASK058; no aceptó implícitamente el runtime financiero.

## 6. Open decisions
| ID | Decisión HUMAN | Recomendación (NO aprobada) |
|---|---|---|
| D-MR0-002 | Política de publicación público/privada | Allowlist exacta, control de datos y gate por transacción |
| D-MR0-003 | Fuente RAW corregida | Mantener `REJECT`; diseñar alternativa `NEW_VERSION` sin reemplazo destructivo |
| D-MR0-004 | Producto PH2 y criterios | Definir Funding Memo y mapeo antes de implementar |
| D-MR0-005 | README | Actualización bajo gate documental posterior |
| D-MR0-007 | RM-GATE-003 | Revisar evidencia financiera TASK060 y aceptar o rechazar operación |
| RD-003/RD-007/RD-008 | Desacoplamiento, infraestructura y herramientas | Diseño gradual, aprobación separada |
| GOV-SKILL-001 | Versiones superpuestas de Skills | Aplicar obligaciones compatibles conjuntamente; conflictos nuevos escalan a HUMAN |
| GOV-CONT-001 | Bootstrap canónico local | RESUELTO por adopción TASK055 y reconciliación TASK060; publicación Git sigue separada |

## 7. Risks, blockers and unknowns
| ID | Riesgo | Nivel | Control/gate |
|---|---|---|---|
| MR-R01 | Publicación de RAW/SQLite/OUTPUT en repo público | P0 | Revisión de privacidad, allowlist y autorización explícita |
| MR-R02 | Reanudar sin documentos de gestión conformes | P0 | Validación Skills + aprobación HUMAN |
| MR-R03 | RAW modificado sin política de versionado | P1 | `REJECT` hasta definición y aprobación |
| MR-R04 | PH1/PH1.5 comparten lógica financiera | P1 | Regresión cruzada, diseño antes de cambiar |
| MR-R05 | Evidencia financiera aún requiere decisión HUMAN | P0 | `RM-GATE-003` permanece OPEN |
| MR-R06 | Deriva futura del bootstrap local | P1 | Manifiesto, READ_PLAN y recovery limpio |
| MR-R07 | README desactualizado | P2 | Actualización documental controlada |

## 8. Readiness matrix
| Dimensión | Estado | Evidencia | Brecha | Próxima acción |
|---|---|---|---|---|
| Claridad del objetivo | PASS | PH1/PH1.5 aceptadas, PH2 prevista | Detalle PH2 | Taller de producto |
| Suficiencia de evidencia | NOT_READY | TASK043/TASK044/TASK058/TASK060 | 32 diferencias Excel↔SQLite; 354 controles NOT_TESTABLE | Resolución contable y nueva revisión de matriz privada |
| Privacidad/cumplimiento | PARTIAL | Allowlist TASK046 | Políticas operativas futuras | Gate por publicación |
| Técnica | PARTIAL | Base PH1/PH1.5 | Acoplamiento/versiones RAW | Evaluación de diseño |
| Runtime/proceso | PASS_INFRASTRUCTURE_ONLY | TASK056/TASK057/TASK058 | Aceptación financiera separada | RM-GATE-003 HUMAN |
| Rollback/abort | PARTIAL | Helpers SQLite y política single-writer | No aplica a aceptación HUMAN | Mantener controles |
| Propietario/autoridad | PASS | Modelo HUMAN y gates | Decisiones abiertas | Registro de decisiones |
| Costos/tiempo | UNKNOWN | Estimaciones de complejidad previas | No se aprobaron recursos | Evaluar con roadmap |
| Aceptación de usuario | PARTIAL | PH1/PH1.5 aceptadas; infraestructura aprobada | RM-GATE-001/003/004/005 abiertos | Decisiones HUMAN separadas |

## 9. Roadmap impact
La remediación documental y la adopción local del bootstrap están ejecutadas. La infraestructura Windows+WSL2 está aprobada y no debe reinstalarse. Antes de desarrollo financiero se requiere decisión HUMAN sobre `RM-GATE-003`; PH2 además exige `RM-GATE-004`.

## 10. Active DAG / next work graph
`RM-GOV-001 (documentación reconciliada) → RM-GATE-001 (aprobación HUMAN)`; `RM-GATE-002 (cerrado infraestructura) → RM-UPG-001 (completo observado) → RM-OPS-001 (evidencia financiera) → RM-GATE-003 (decisión HUMAN)`; `RM-PH2-001 → RM-GATE-004`; `RM-GATE-003 + RM-GATE-004 → RM-PH2-002`.
En paralelo tras gate adecuado: `RM-DOC-001` (README), `RM-DATA-001` (política RAW), `RM-QA-001` (diseño de pruebas). Referencia: ROADMAP_INTEGRAL borrador corregido.

## 11. Authorization matrix
| Acción | Estado | Autoridad | Evidencia requerida |
|---|---|---|---|
| Auditoría documental no destructiva | Permitida en alcance aprobado | MORCH/RORCH | Fuentes y registro |
| Nuevos borradores separados | Autorizada por HUMAN en este ciclo | HUMAN | Original intacto + validación Skill |
| Alterar código/criterios/base | BLOQUEADA | HUMAN | Gate específico |
| Borrado/limpieza | BLOQUEADA | HUMAN | Manifiesto, impacto, rollback |
| Commit/push/tag | BLOQUEADA | HUMAN | Allowlist exacta + Git preflight |
| Reinstalar/reconfigurar OmniRoute/DSH | BLOQUEADA | HUMAN | Nueva necesidad y autorización separada; arquitectura actual aprobada |
| Implementar PH2 | BLOQUEADA | HUMAN | Producto, FM0, mapeos, reglas aceptadas |

## 12. Closed gates
PH1 HUMAN_ACCEPTED; PH1.5 HUMAN_ACCEPTED; publicación GitHub PH1/PH1.5; `RM-GATE-002=CLOSED_INFRASTRUCTURE_ONLY`. `RM-GATE-001`, `RM-GATE-003`, `RM-GATE-004` y `RM-GATE-005` permanecen abiertos.

## 13. Next eligible nodes
Revisión HUMAN/contable de las 32 diferencias Excel↔SQLite preservadas por TASK060; no cerrar `RM-GATE-003` hasta resolverlas o aceptarlas explícitamente. Ninguna implementación PH2 es elegible.

## 14. Handoff requirements
Transferir SHA, rutas, evidencia y su categoría temporal; estado de aceptación separado de implementación; gates abiertos; decisiones; prohibiciones; DAG y condiciones STOP. Referencia al archivo HO.1 corregido.

## 15. Terminal convergence
`MR0_CURRENT_STATE=RECONCILED; BOOTSTRAP=CANONICALLY_ADOPTED_LOCAL; RM_GATE_002=CLOSED_INFRASTRUCTURE_ONLY; RM_GATE_003_004_005=OPEN; ACCEPTANCE=HUMAN_PENDING; PH2=BLOCKED; STOP_IF=HEAD_MISMATCH|SENSITIVE_PUBLISH|UNAUTHORIZED_MUTATION|CONFLICT_UNRESOLVED.` La cronología de los documentos rechazados y candidatos permanece como evidencia histórica.

### Glosario
MR.0 = Integrated Management Review; HO.1 = Handoff One; DAG = Directed Acyclic Graph; RAW = archivos contables de origen; WSL = Windows Subsystem for Linux; SQLite = motor local de base de datos; CLI = interfaz de línea de comandos; DSH = DeepSeek Harness; FM0 = versión inicial del Funding Memo.

