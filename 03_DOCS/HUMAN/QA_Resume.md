# QA_Resume.md — Estado consolidado de decisiones vigentes

**Proyecto:** KT.MovemAcc  
**Corte:** 2026-10-21  
**Estado:** `DRAFT_FOR_HUMAN_REVIEW`  
**Fuente de detalle:** `QA.md` (IDs Q-001 a Q-068, decisiones D01–D08).  
**Regla de autoridad:** HUMAN confirmado > normativa oficial efectiva > evidencia independiente > declaración del ejecutor > recomendación. Los estados reportados no sustituyen aprobación empresarial.

## 00. Resumen ejecutivo

1. **Regla temporal HUMAN aprobada:** los reportes contables contienen **movimientos acumulados desde el día 0 del proyecto hasta el cierre del período a las 23:59 horas**. Agosto 2026: desde el origen hasta **2026-08-31 23:59**, no solo movimientos de agosto. No implica que todas las partidas del FM puedan copiarse sin evaluar naturaleza contable y reglas de reconocimiento.
2. **Roadmap HUMAN aprobado:** (A) PH1 local autónomo, (B) vaciado al Funding Memo, (C) `.exe` o Docker. IA para desarrollo/mantenimiento, **no** para operación mensual ordinaria.
3. **Roles:** HUMAN aprueba; MORCH metaorquesta; RORCH/DSH ejecuta su ámbito técnico; **SPECIALIST = Codex Desktop + NTV**; QA debe tener oráculo independiente cuando corresponda.
4. **PH1 operativo:** RORCH informa CLI Python multiperíodo sin IA/WSL/Excel COM/internet; ejecución PowerShell Windows **sin certificación nativa todavía**. Octubre real aún no probado.
5. **USECASE_PHASE1:** HUMAN aprobado; RORCH reporta promoción byte-identical a `03_DOCS/HUMAN/UseCase_PHASE1.md`; otros documentos no demostraron sincronización integral.
6. **Finanzas:** `FM2026.08_VALIDATION.xlsx` es prototipo de validación, **no** libro de producción aprobado. 72 destinos FM; SPECIALIST_003 informa 15 técnicos verificados, 18 ambiguos, 9 unmapped contables, 30 no contables. **0 mapeos aprobados por HUMAN**.
7. **PH1/PH1.5:** persisten **32 FAIL** con diagnóstico `SOURCE_SEMANTIC_MISMATCH` de Impulsa; ningún FAIL se promueve por inferencia. Hash histórico del PH1 aceptado no disponible como bytes físicos observables según SPECIALIST.
8. **Gobernanza:** `RM-GATE-003=OPEN`, `RM-GATE-004=OPEN`; ni QA PASS ni creación de archivo los cierran.
9. **NTV ROOT:** persisten ruta Windows malformada dentro del repo, residuos de pruebas en BACKUPS y discrepancia entre aprobación HUMAN y carga efectiva de Skills QA en Codex. Requieren reconciliación, no limpieza ciega.

## 01. Decisiones y reglas vigentes — solo confirmadas

| ID | Decisión | Fuente / autoridad | Impacto obligatorio |
|---|---|---|---|
| A-01 | Fecha de corte reportes = acumulado desde día 0 hasta fin de mes 23:59. | HUMAN, 2026-10-21 | PH1 y diseño FM; no tratar cada mayor como movimiento exclusivo del mes. |
| A-02 | Motor PH1 ejecutable sin IA en operación mensual. | HUMAN | No exigir ChatGPT, DSH ni RORCH para ejecutar cada mes. |
| A-03 | Orden Fase A → Funding Memo → `.exe`/Docker. | HUMAN | No anteponer packaging a correspondencias financieras. |
| A-04 | SPECIALIST es Codex Desktop + NTV. | HUMAN | No etiquetar resultados de este chat como SPECIALIST. |
| A-05 | NTV incluye orden, limpieza, ownership, retención y estructura ROOT. | HUMAN | Preflight/inventario y postflight de higiene obligatorios por alcance. |
| A-06 | Downloads real `C:\Users\aazcl\Downloads` es descartable en ≤24 h. | HUMAN | Nunca fuente canónica ni respaldo de evidencia única. |
| A-07 | Dos QA Skills, transversal e interna KTMA, aprobadas en contenido por HUMAN. | HUMAN | La instalación/carga efectiva se verifica por entorno, no se reabre aprobación. |
| A-08 | `USECASE_PHASE1.md` aprobado por HUMAN. | HUMAN | Conservar bytes; documentar en su ubicación canónica sin editarlo silenciosamente. |
| A-09 | Los artefactos originales financieros no deben alterarse en auditorías y prototipos. | Reglas operativas NTV aceptadas | Entradas read-only, hashes y escritura solo con permisos específicos. |
| A-10 | RM-GATE-003 y RM-GATE-004 abiertos hasta aprobación HUMAN. | Gobierno reiterado | No implementar población productiva ni cerrar gates automáticamente. |

## 02. Hechos técnicos útiles, sin convertirlos en decisión HUMAN

| Asunto | Estado de evidencia |
|---|---|
| PH1 `OUTPUT/YYYY.MM/CAMYYYY.MM_CONSOL.ALIGN.xlsx` | Convención reportada; octubre real pendiente. |
| Entrada mensual `RAW.INPUT/YYYY.MM` con mayor Eplaza/Impulsa `.xlsb` | Convención operativa documentada, verificar estructura mensual. |
| PH1 CLI `python -m kt_movemacc.cli ph1 --period ... --out-dir ...` | Reportado por RORCH; contraste con entrypoint HO.1 y Windows real pendiente. |
| PH1 actual SHA `5acba7...ec5ec` / histórico aceptado `38a3ff...fcfd3` | Identidades distintas; no restaurar/promover automáticamente. |
| FM `FM2026.08_VALIDATION.xlsx` | `VALIDATION_CANDIDATE`, no autoridad de producción. |
| Columna C = valores V0, D/E/F = total/entidad en parte del libro | Análisis del workbook; regla de escritura no aprobada. |
| SPECIALIST_003 15+18+9 mapping contables / 30 no contables | Reporte técnico; 0 aprobación financiera. |
| 32 fallos jerárquicos Impulsa | Causas identificadas según SPECIALIST; FAIL activos. |
| DSH QA wrapper L2 | Implementación local reportada, sin hook global. |

## 03. Decisiones D01–D08 pendientes y próximo punto humano

| ID | Tema | Lo que YA sabemos | Qué NO se ha aprobado |
|---|---|---|---|
| D01 | Fecha, corte y reconocimiento | HUMAN define acumulado desde origen a 23:59 del último día del período. | Medida por partida, saldos/movimientos acumulados, capitalizados/P&L, ajustes y reversiones. |
| D02 | Asignación entidad | No duplicar criterios por glosa. | Cuentas/proyecto realmente atribuibles a Impulsa vs Eplaza. |
| D03 | Construcción | E38 residual propuesto y alternativas E37/39/40/41. | Partición económica mutuamente excluyente. |
| D04 | Financiamiento | E53 residual propuesto; excluir doble conteo. | Bases de terreno, pólizas, costos financieros y signos. |
| D05 | Cuatro casos Eplaza | E49/E52/E54 técnicamente verificables; E41 ambiguo; E52 cero observado. | Adopción financiera, E41 y origen económico final. |
| D06 | Ventas y fuentes externas | 20 destinos reportados EXTERNAL_BUSINESS_SOURCE. | Dueño, período, fuente, bruto/neto, entidades y evidencia. |
| D07 | IVA, fee y preferente | E/F61,65,69 vacías según SPECIALIST_003; existen fórmulas derivadas posteriores. | Bases, tasas, calendario, devengo, impuesto, redondeo. |
| D08 | Capital y retorno | Histórico C77=C70/C75; destinos E/F75–77 no resueltos. | Capital requerido, fórmula de retorno y denominadores. |

**Orden operativo sugerido, NO aprobado automáticamente:** SPECIALIST documenta y reconcilia a nivel fuente lo posible bajo D01–D05; HUMAN decide solo reglas de negocio insuficientemente determinadas; después D06–D08; versión aprobada del registry; QA; aprobación de población separada.

## 04. Anomalías de gobierno e higiene abiertas

| Incidencia | Estado / acción segura |
|---|---|
| Directorio interno `...\C\Users\aazcl\Downloads` y otros nombres malformados | Confirmados por HUMAN e informados por SPECIALIST; remediación propuesta NTV010B **no ejecutada**; inventario/quarantina acotada antes de borrado. |
| Outputs de test en `08_EVIDENCE/BACKUPS` | Seis archivos reportados por SPECIALIST_003; reclasificación/retención/cleanup con grant. |
| `~$` lock Excel y residuos `__pycache__` | No borrar si activo ni limpiar sin permiso. |
| QA Skills estatus candidato en cuerpo vs aprobación HUMAN e instalación informada por RORCH | Disputa de metadata / descubrimiento real en Codex; revisar, no revocar decisión HUMAN. |
| Reportes/dispositivos en Downloads | No dejar allí única evidencia o criterio. |
| Documentación PH1 | USECASE oficializado reportado; sincronización README/Roadmap/HO.1 sin prueba. |

## 05. Regla de mantenimiento

1. `QA.md` conserva preguntas y respuestas individuales, incluyendo decisiones supersedidas y contradicciones.
2. `QA_Resume.md` **solo** conserva la interpretación actualmente vigente, con referencia al Q-ID y a evidencia/autoridad.
3. Ninguna propuesta, reporte RORCH ni SPECIALIST se etiqueta `HUMAN_APPROVED` sin una respuesta HUMAN específica.
4. Cada cambio material incluye fecha, actor, evidencia, razón, impacto, autoridad y registro de revisión; sin sustitución silenciosa.
5. La Skill `QA_SKILLS.MovemACC.md` gobierna el proceso de conservación/actualización una vez que HUMAN la apruebe y se instale conforme a la política local. No suplanta `SKILLS.QA.TRANSVERSAL.md` (quality assurance técnico).
