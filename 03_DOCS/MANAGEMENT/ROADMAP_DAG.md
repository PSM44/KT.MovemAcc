# Roadmap DAG — KT.MovemAcc

## 1. Leyenda

DAG (Directed Acyclic Graph, grafo acíclico dirigido) define dependencias sin ciclos. Prioridades: P0 crítico, P1 alto, P2 medio.

## 2. Nodos principales

| ID | Fase | Prioridad | Entregable | Depende de | Puede correr en paralelo |
| --- | --- | --- | --- | --- | --- |
| R0 | Aprobación roadmap | P0 | Decisión HUMAN sobre roadmap | MR.0, HO.1 | No |
| U1 | Upgrade gate | P0 | Plan y ejecución autorizada OmniRoute/DSH | R0 | No con desarrollo |
| C1 | README post-publicación | P2 | README actualizado | U1 | C2, C3 |
| C2 | Fresh clone WSL | P1 | Validación clon limpio WSL | U1 | C1, C3 |
| C3 | Windows gate | P1 | Validación Windows real | U1 | C1, C2 |
| C4 | Checklist mensual | P1 | Checklist aprobado | C2, C3 | G1 |
| G1 | Política RAW | P1 | Decisión REJECT/NEW_VERSION | R0 | C1-C4 |
| G2 | Diseño NEW_VERSION | P1 | Diseño técnico-contable si HUMAN lo aprueba | G1 | No si decisión es mantener REJECT |
| A1 | Health-check read-only | P2 | Especificación de health-check | C4 | P1 |
| P1D | Definición producto PH2 | P0 | Decisión alcance PH2 | R0 | G1, C1-C4 |
| P2D | Inventario FM0/FM | P1 | Inventario aprobado de estructura FM | P1D | G1 |
| P3D | Matriz de mapeo PH1.5→PH2 | P1 | Mapping aprobado | P2D, contrato PH1.5 | No |
| P4D | Criterios y tolerancias PH2 | P0 | Criterios HUMAN aprobados | P2D, P3D | No |
| P5I | Implementación PH2 | P0 | Código/pruebas PH2 | P4D, G1/G2, autorización HUMAN | No |
| Q1 | QA/regresión PH2 | P0 | Evidencia pruebas PH2 | P5I | No |
| PUB | Gate publicación futura | P0 | Allowlist y privacidad | C1-C4, P5I si aplica | No |
| REP | Reporting opcional | P2 | Evaluación Power BI/dbt/GE | P4D o después PH2 | Sí, diseño solamente |

## 3. Camino crítico

```text
R0 Roadmap HUMAN approval
  -> U1 OMNIROUTE_AND_DSH_UPGRADE
  -> C2/C3 Fresh clone + Windows validation
  -> C4 Monthly checklist
  -> P1D PH2 product definition
  -> P2D FM inventory
  -> P3D Mapping PH1.5 to PH2
  -> P4D Approved PH2 criteria
  -> P5I PH2 implementation
  -> Q1 PH2 QA
  -> PUB Future publication gate
```

## 4. Máximo paralelismo seguro

Después de `U1` pueden correr en paralelo:

- C1 README update.
- C2 WSL/fresh clone.
- C3 Windows gate.
- G1 decisión de política RAW (gestión, no código).
- P1D workshop de producto PH2 (sin implementación).

No pueden correr en paralelo con implementación PH2:

- Upgrade de infraestructura.
- Cambios de criterios contables sin aprobación.
- Migraciones SQLite.
- Publicación GitHub.

## 5. Gates obligatorios

### Gate R0 — Roadmap approval

Criterios:

- HUMAN aprueba o ajusta roadmap.
- Decisiones pendientes quedan explícitas.
- Development pause sigue activo.

### Gate U1 — OMNIROUTE_AND_DSH_UPGRADE

Criterios:

- Autorización HUMAN explícita.
- Backup/rollback documentado.
- Smoke tests pre/post.
- Sin cambios financieros.
- No PH2 durante upgrade.

### Gate PH2-DESIGN

Criterios:

- Producto PH2 definido.
- FM0/FM inventariado.
- Mapeos propuestos revisados.
- Criterios y tolerancias aprobadas.
- Privacy/audit definidos.

### Gate PH2-IMPLEMENTATION

Criterios:

- Autorización HUMAN explícita.
- Diseño PH2 aprobado.
- Política RAW decidida.
- Entorno validado Windows/WSL.

### Gate PUBLIC-DATA

Criterios:

- Allowlist exacta.
- No RAW, no SQLite, no OUTPUT financiero, no runtime.
- Git staging vacío antes de stage controlado.
- Revisión privacidad.

## 6. Workstreams

### WS-A Producto y criterios contables

- Definir PH2.
- Aprobar criterios.
- Mantener preguntas contables abiertas como decisiones HUMAN.

### WS-B Datos y gobernanza

- RAW hashes.
- Política de versión.
- SQLite schema y migraciones futuras.

### WS-C Operación mensual

- Checklist.
- Fresh clone.
- Windows/WSL.
- Backup/restore.

### WS-D QA y auditoría

- Regression suites.
- Reconciliaciones.
- Evidencia de linaje.
- Smoke tests post-upgrade.

### WS-E Privacidad y publicación

- Allowlists.
- Exclusiones.
- README/documentación pública.

### WS-F Tecnología opcional

- dbt/Great Expectations/Power BI sólo por caso de uso.
- Airflow no necesario en alcance actual.

## 7. Bloqueadores conocidos

- PH2 sin definición financiera aprobada.
- Windows real no validado.
- README estado público desactualizado.
- Política `NEW_VERSION` no decidida.
- Upgrade OmniRoute/DSH pendiente antes de desarrollo.
