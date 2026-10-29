# Roadmap — Decisiones de Gestión Pendientes

## 1. Decisiones HUMAN requeridas

| ID | Decisión | Alternativas | Riesgos | Recomendación | Requiere HUMAN |
| --- | --- | --- | --- | --- | --- |
| RD-001 | Frontera público/privado GitHub | A) Mantener allowlists exactas; B) ignorar RAW/OUTPUT globalmente; C) publicar más evidencia | A requiere disciplina; B puede interferir con paquetes públicos; C expone datos | Mantener allowlists exactas y gate privacidad | Sí |
| RD-002 | Política RAW | A) Mantener `REJECT`; B) diseñar `NEW_VERSION`; C) permitir replace | A bloquea correcciones legítimas; B requiere diseño; C amenaza historia | Mantener `REJECT` hasta diseño `NEW_VERSION` aprobado | Sí |
| RD-003 | Acoplamiento PH1/PH1.5 | A) Aceptar acoplamiento; B) modularizar reglas/parser; C) duplicar lógica | A riesgo futuro; B esfuerzo controlado; C divergencia | Diseñar modularización antes de PH2, sin cambiar ahora | Sí para priorizar |
| RD-004 | Gate Windows | A) Obligatorio; B) sólo WSL; C) soporte best-effort | A requiere ambiente; B puede fallar usuario Windows; C ambiguo | Hacer Windows gate antes de PH2 | Sí |
| RD-005 | README | A) Actualizar ya; B) posponer; C) no actualizar | A requiere tarea documental; B mantiene confusión | Actualizar después de upgrade gate | Sí |
| RD-006 | Dirección PH2 | A) Funding Memo Excel; B) reporting base de datos; C) Power BI; D) híbrido | Sin decisión no hay criterios | Hacer workshop PH2 design sin código | Sí |
| RD-007 | OmniRoute/DeepSeek Harness | A) Actualizar con gate; B) posponer; C) actualizar sin gate | C riesgo operativo; B deuda entorno | Ejecutar gate dedicado con rollback | Sí |
| RD-008 | Herramientas analíticas | A) SQLite+Python; B) PostgreSQL; C) dbt; D) GE; E) Power BI; F) Airflow | Complejidad innecesaria | SQLite+Python ahora; evaluar dbt/GE; Power BI luego; Airflow no actual | Sí para roadmap |

## 2. Evaluación tecnológica

| Tecnología | Clasificación | Motivo |
| --- | --- | --- |
| Python existente | ADOPT_NOW | Ya implementa PH1/PH1.5 y pruebas. |
| SQLite | ADOPT_NOW | Encaja con base local privada, auditoría y baja complejidad. |
| PostgreSQL | EVALUATE_LATER | Sólo si aparecen multiusuario, servidor, concurrencia o volumen mayor. |
| dbt | EVALUATE | Útil si PH2 evoluciona a modelos SQL versionados; prematuro ahora. |
| Airflow | NOT_NEEDED_CURRENT_SCOPE | Sobrecarga para flujo mensual local de dos RAW. |
| Great Expectations | EVALUATE | Puede formalizar expectativas si crece matriz de QA. |
| Power BI | ADOPT_LATER | Útil para reporting cuando contrato PH2 esté estable. |
| OmniRoute/DeepSeek Harness upgrade | GATE_REQUIRED | Debe ocurrir antes de desarrollo, con autorización y rollback. |

## 3. Criterios de aceptación por decisión

### RD-002 RAW policy

Aceptación mínima:

- Documento de política aprobado.
- Efecto sobre historia financiera definido.
- Pruebas de rollback y reconciliación definidas.
- Sin implementación hasta aprobación.

### RD-006 PH2 direction

Aceptación mínima:

- Output final definido.
- FM0 y campos objetivo inventariados.
- Mapeos y fórmulas revisados por HUMAN.
- Diferencias y tolerancias definidas.
- Auditoría por línea.

### RD-007 Upgrade

Aceptación mínima:

- Evidencia pre-upgrade.
- Backup/rollback.
- Smoke tests pre/post.
- Confirmación sin cambios en RAW/SQLite/OUTPUT/criterios.

## 4. Decisiones no aprobadas por este documento

Este documento no aprueba:

- PH2 implementation.
- `NEW_VERSION`.
- PostgreSQL/dbt/Great Expectations/Power BI/Airflow.
- Cambios en criterios contables.
- Git publication.
- OmniRoute/DeepSeek Harness upgrade.

Sólo prepara alternativas y recomendaciones para decisión HUMAN.

## 5. Reconciliación TASK058

- `RM-GATE-002=CLOSED_INFRASTRUCTURE_ONLY` por autorización HUMAN explícita en TASK058, sustentada por las observaciones TASK056/TASK057.
- DSH y OmniRoute permanecen en WSL2; no se justifica instalación nativa en Windows.
- Windows es el único escritor autorizado de la SQLite canónica; WSL2 es consumidor read-only o delega escrituras a Windows.
- `RM-GATE-003`, `RM-GATE-004` y `RM-GATE-005` permanecen `OPEN`. Este cierre no acepta el runtime financiero ni autoriza PH2 o publicación.
