# Implementation Plan: Resolubilidad y llaves

**Branch**: `004-resolubilidad-llaves` | **Date**: 2026-11-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-resolubilidad-llaves/spec.md`

**Note**: Plan generado siguiendo `/speckit.plan`; las decisiones de estructura
están en `research.md` y el detalle de entidades en `data-model.md`.

## Summary

Verificar si una cripta puede ganarse antes de jugarla, impedir el inicio si no
es resoluble (salvo `--forzar`) y explicar el bloqueo con frontera, llaves
inobtenibles y ciclo concreto. La verificación se hace con **un único recorrido
incremental** de la región alcanzable: las puertas cerradas se retienen
asociadas a su llave y, cuando la llave se obtiene, se liberan solo esas
puertas y el recorrido continúa. El mismo recorrido produce el orden
determinista de llaves, la frontera bloqueada y las llaves inobtenibles. La
ubicación de llaves se consulta al servicio (`GET /v1/criptas/<id>/llaves`),
se puede persistir y se invalida por versión.

## Technical Context

**Language/Version**: Python 3.11+ (el repo se ejecuta con 3.14.4 en el equipo
de desarrollo).

**Primary Dependencies**: solo biblioteca estándar en el verificador y en el
generador sintético; `requests` queda detrás del adaptador HTTP existente.

**Storage**: caché local en disco por cripta (`AlmacenCripta`), con
`version.txt`; la respuesta de llaves se guarda como un archivo más de la
cripta y se invalida con la validación de versión ya existente.

**Testing**: `unittest` (`python -m unittest discover -s tests`), pruebas
deterministas con semillas fijas y un oráculo ingenuo para comparar.

**Target Platform**: CLI de escritorio (Linux/Windows) y cliente del servicio
web; `--verificar`, `--bench` y `--replay` funcionan sin vista.

**Project Type**: proyecto único (modelo + adaptadores + controlador + vista).

**Performance Goals**: verificación ≤ 200 ms en la cripta publicada más grande
(hoy 300 salas); costo asintótico ≈ lineal en salas + salidas + llaves.

**Constraints**:
- Prohibido `dict`, `set`, `heapq`, `bisect`, `collections`, `networkx` y
  cualquier biblioteca de grafos o rutas.
- Determinismo estricto: mismas entradas ⇒ mismo veredicto y mismo orden.
- `--verificar` no instancia la vista ni escribe en `partida.log`.
- El presupuesto incluye la consulta de llaves.
- Sin datos de una cripta concreta en el código.

**Scale/Scope**: criptas publicadas de 6 a 300 salas; el generador sintético
debe cubrir miles de salas y muchas llaves encadenadas para medir la tendencia.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumplimiento | Evidencia / decisión |
|---|---|---|
| I. Estructuras a mano (NO NEGOCIABLE) | PASA | Se usan `TablaOrdenada`/`ConjuntoOrdenado`, `ColaEnlazada` y listas propias. Nada de `dict`, `set`, `heapq`, `bisect`, `collections` ni `networkx`. |
| II. Determinismo | PASA | Un solo recorrido FIFO con salidas en orden N,S,E,O y desempate por id de llave; ids ordenados con `ordenar` propio. |
| III. MVC sin vista | PASA | El verificador vive en el modelo/controlador; `--verificar` construye el mapa y no la vista. |
| IV. Sin datos de cripta en el código | PASA | Todo sale de `DatosCripta`, del esqueleto y de la respuesta de llaves. |
| V. Presupuesto de solicitudes | PASA | `datos_cripta` fija el presupuesto antes de pedir `/llaves`; la respuesta se cachea por versión. |
| VI. Rendimiento con `--bench` | PASA | Se medirá incremental vs. ingenuo con semillas fijas y límites configurables. |
| VII. Spec antes que código | PASA | `spec.md` confirmada y clarificada antes de este plan (commits `065e6d9`). |

**Resultado del gate:** sin violaciones. No se necesita `Complexity Tracking`.

## Project Structure

### Documentation (this feature)

```text
specs/004-resolubilidad-llaves/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones, alternativas y complejidad
├── data-model.md        # Fase 1: entidades y validaciones
├── quickstart.md        # Fase 1: guía de validación
├── contracts/
│   ├── llaves.md        # Contrato del servicio (Swagger v1.1.0)
│   ├── verificar-cli.md # Contrato de --verificar/--forzar y salida
│   └── interfaz-a-b.md  # Punto 1 B→A: costo, rango y cazador
├── checklists/
│   └── requirements.md
└── tasks.md             # Lo genera /speckit.tasks
```

### Source Code (repository root)

```text
cripta/
├── modelo/
│   ├── verificacion.py        # NUEVO: verificación incremental y reporte
│   ├── datos.py               # costo en DatosSalida, rango en Ficha
│   ├── mapa.py                # (A) exponer costo de salida a consumir
│   └── juego.py               # (A) usar el costo de la salida al moverse
├── adaptadores/
│   ├── fuente_datos.py        # NUEVO método llaves()
│   ├── cliente_http.py        # GET /v1/criptas/<id>/llaves
│   ├── fuente_offline.py      # llaves.json del paquete local
│   └── almacen_disco.py       # guardar/leer llaves.json por versión
├── controlador/
│   ├── aplicacion.py          # --verificar y --forzar
│   ├── controlador.py         # verificar al iniciar y mostrar reporte
│   └── comandos.py            # (si el reporte se consulta en partida)
├── bench/
│   ├── sinteticos.py          # NUEVO: generador determinista por semilla
│   ├── bench_resolubilidad.py # NUEVO: incremental vs. ingenuo
│   └── runner.py              # registrar el nuevo bench
└── vista/
    └── vista_consola.py       # (A) mostrar el reporte al iniciar

tests/
├── test_resolubilidad.py      # NUEVO: AC-004-01..04, oráculo, determinismo
├── test_red.py                # /llaves, presupuesto y versión
└── test_integracion.py        # --verificar sin vista y arranque bloqueado
```

**Structure Decision**: se mantiene la estructura MVC existente. El verificador
es lógica de juego (modelo) y no conoce red, disco ni vista; el controlador
orquesta la consulta, la persistencia y las banderas. El generador sintético
vive en `bench/` porque lo consumen las mediciones y las pruebas, no el juego.

## Phase 0: Outline & Research

Salida: [`research.md`](./research.md). Resuelve:

- recorrido incremental único y liberación de puertas retenidas;
- orden determinista de llaves y desempate por id;
- detección determinista del ciclo concreto;
- frontera bloqueada con puertas compartidas (sin duplicar);
- persistencia de `/llaves` por versión y respeto del presupuesto;
- oráculo ingenuo para pruebas;
- generador de criptas sintéticas determinista;
- auditoría de estructuras prohibidas.

## Phase 1: Design & Contracts

Salidas:

- [`data-model.md`](./data-model.md): entidades, campos, relaciones,
  validaciones e invariantes.
- [`contracts/llaves.md`](./contracts/llaves.md): contrato exacto del servicio.
- [`contracts/verificar-cli.md`](./contracts/verificar-cli.md): banderas,
  códigos de salida y formato del reporte.
- [`contracts/interfaz-a-b.md`](./contracts/interfaz-a-b.md): lo que B entrega
  a A para `costo`, `rango` y `cazador` (referencia a la spec 001 de A).
- [`quickstart.md`](./quickstart.md): comandos y resultados esperados.

## Re-evaluación de la Constitución (post-diseño)

| Principio | Resultado |
|---|---|
| I. Estructuras a mano | PASA: el diseño solo usa estructuras propias del repo. |
| II. Determinismo | PASA: el orden de descubrimiento es función de la FIFO, del orden N,S,E,O y del id. |
| III. MVC sin vista | PASA: el reporte es un valor del modelo; la vista solo lo imprime. |
| IV. Sin datos de cripta | PASA: ni el verificador ni el generador codifican ids reales. |
| V. Presupuesto | PASA: la consulta de llaves se hace después de fijar el presupuesto. |
| VI. Rendimiento | PASA: el bench compara contra el ingenuo con límites configurables. |
| VII. Spec antes que código | PASA: la spec está confirmada; el código empieza en Fase 3C. |

## Complexity Tracking

Sin violaciones que justificar. La única complejidad añadida (retención de
puertas por llave) es necesaria para cumplir el costo ≈ lineal y evitar
repetir el recorrido una vez por llave.

## Trazabilidad requisitos → decisiones → tareas

| Requisitos | Decisión de diseño | Tareas |
|---|---|---|
| FR-001, FR-002, FR-003, FR-004, FR-005 | R1 (recorrido incremental), R3, R4 | T014, T015, T016, T019, T020, T024 |
| FR-006, FR-007 | R2 (orden determinista) | T015, T035, T036, T037, T038 |
| FR-008 | R3 (frontera e inobtenibles) | T020, T021, T022 |
| FR-009 | R4 (ciclo concreto) | T019, T023 |
| FR-010, FR-011 | Contrato CLI + gate de inicio | T030, T031, T032, T034 |
| FR-012, FR-013 | MVC sin vista + reporte | T013, T017, T018, T033 |
| FR-014 | R7 (generador sin datos fijos) | T009, T042, T045 |
| FR-015 | R5 (offline) | T005 |
| FR-016, FR-017 | R5 + contrato `/llaves` | T003, T004, T008, T025, T028 |
| FR-018, FR-019, FR-020, FR-021 | R5 (versión y presupuesto) | T006, T007, T026, T027 |
| FR-022, FR-023, FR-024 | R3, R4 (casos ambiguos) | T020, T022, T024, T029 |
| NFR-001, NFR-002 | R1, R9 (mediciones) | T039, T041 |
| NFR-003, NFR-004 | R9 (límites configurables) | T039, T040 |
| NFR-005 | R6 (oráculo) | T011, T012 |
| SC-001 | Escenarios con prueba | T012, T019, T020, T025, T030, T035, T042 |
| SC-002 | Determinismo | T010, T035, T038 |
| SC-003 | Reporte completo | T021, T022, T023, T024 |
| SC-004 | 200 ms en 300 salas | T039, T041 |
| SC-005 | Oráculo | T011, T012 |
| SC-006 | Sin vista ni `partida.log` | T013, T017 |
| SC-007 | Presupuesto | T007, T027 |

**Nota sobre estructuras prohibidas:** las menciones a `dict`, `set`, `heapq`,
`bisect`, `collections` y `networkx` en este plan son **prohibiciones
explícitas** de la constitución, no dependencias del diseño.

## Dependencias externas

- **Spec 001 de A** (costo de salida, ficha de cazador con `rango`): los
  `FR-xxx` se coordinarán con A y el código de esa parte no se implementa hasta
  que su spec esté confirmada en Git.
- **Spec 003 de A** (mapa conocido): no interviene en esta capacidad.
- **Servicio**: Swagger v1.1.0 es la referencia; no se inventan campos.

## Próximo paso

`/speckit.tasks` para descomponer en tareas pequeñas con sus `FR-xxx`, y
`/speckit.analyze` antes de implementar.
