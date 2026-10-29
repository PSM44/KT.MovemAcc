# HO.1 — Entradas Verificables para Roadmap Integral

## 1. Línea base para roadmap

- PH1: aceptado por HUMAN, publicado en GitHub, workbook aceptado preservado históricamente.
- PH1.5: aceptado por HUMAN, publicado en GitHub, base SQLite local validada para agosto 2026.
- PH2: no implementado, no autorizado.
- HEAD canónico: `e948336cd790d998e4af6243d00246989404897e`.
- Base local actual: SQLite V1 con periodo `2026.08`.

## 2. Hallazgos MR.0 que alimentan roadmap

### P0

1. Mantener frontera estricta público/privado: RAW, SQLite, runtime y outputs financieros fuera de GitHub salvo autorización específica.
2. Completar continuidad operacional antes de nueva implementación.

### P1

1. Workflow mensual manual requiere checklist y validación fresh clone.
2. Política de fuente sólo `REJECT`; falta diseño de `NEW_VERSION` para correcciones legítimas.
3. Acoplamiento entre parser/reglas PH1 y persistencia PH1.5.
4. Windows real no fue ejecutado en MR.0/HO.1.
5. PH2 requiere definición funcional antes de código.

### P2

1. README debe actualizarse para reflejar publicación completada.
2. SQLite local requiere disciplina de backup/locking.
3. Herramientas nuevas deben evaluarse por necesidad real, no por moda.

## 3. Roadmap candidato por fases

### Fase A — Continuidad y documentación post-publicación

- Actualizar README con estado real PH1/PH1.5 publicado.
- Crear checklist mensual aprobado por HUMAN.
- Validar Windows y WSL en ambiente real.
- Validar fresh clone: dependencias, RAW provistos por usuario, comandos de consulta.

### Fase B — Diseño PH2 sin implementación

- Definir objetivo de PH2: Funding Memo, reporting, Power BI u otro.
- Definir criterios de aceptación financiera.
- Definir mapeos desde PH1.5 hacia PH2.
- Definir qué queda manual y qué automatizado.
- Definir formato de evidencia.

### Fase C — Gobernanza de versiones de fuente

- Decidir si `REJECT` permanece como única política.
- Si se requiere `NEW_VERSION`, diseñar migración, tablas, contratos y pruebas antes de implementar.
- Definir cómo se invalida o conserva historia previa.

### Fase D — Observabilidad y controles no destructivos

- Diseñar un comando de health-check read-only.
- Diseñar reporte de readiness mensual.
- Agregar validaciones que no escriban Excel ni SQLite.

### Fase E — Evaluación de herramientas

- SQLite: mantener ahora.
- dbt (data build tool): evaluar si PH2 requiere modelos SQL versionados.
- Great Expectations: evaluar para expectativas de datos si crece la matriz de controles.
- Power BI: adoptar luego si hay contrato estable y necesidad de visualización.
- Airflow: rechazar en alcance actual; reevaluar sólo ante orquestación recurrente multi-fuente.
- OmniRoute/DeepSeek Harness: no actualizar todavía; preparar plan de cambio aislado.

## 4. Controles previos para actualización OmniRoute y DeepSeek Harness

Antes de cualquier upgrade:

1. Registrar versión actual y motivo de cambio.
2. Confirmar que no hay operación financiera en curso.
3. Exportar/guardar evidencia de estado Git y entorno.
4. Probar actualización en entorno aislado.
5. Validar que PH1/PH1.5 comandos básicos siguen importando.
6. Validar que no se modifican RAW, SQLite ni outputs.
7. Definir rollback.
8. Solicitar autorización HUMAN explícita.

## 5. Decisiones HUMAN no convertidas en aprobación

- Actualizar README: pendiente.
- Política `NEW_VERSION`: pendiente.
- Dirección PH2: pendiente.
- Gate Windows obligatorio: pendiente.
- Adopción de dbt/Great Expectations/Power BI: pendiente de caso de uso.
- Upgrade OmniRoute/DeepSeek Harness: pendiente de autorización separada.

## 6. Evidencias mínimas para iniciar el roadmap

- MR.0 review, decisión y riesgo.
- HO.1 continuidad, runbook y entradas roadmap.
- Estado Git local/remoto sincronizado.
- Integridad SQLite read-only.
- Lista de artefactos privados excluidos.
- Confirmación de que PH2 sigue no autorizado.
