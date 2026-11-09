# Implementation Plan: Línea de tiempo e historia

**Branch**: `005-linea-de-tiempo` | **Date**: 2026-11-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-linea-de-tiempo/spec.md`

## Summary

Registrar la línea vigente de la partida (acciones y contenido nuevo), tomar
puntos de control completos cada K acciones y reconstruir el estado de
cualquier instante pasado re-simulando desde el punto de control más cercano
(≤ K acciones). Las acciones revertidas por un pergamino se recortan de la
línea. `historia <t>`/`historia #k` muestran un resumen sin tocar la partida;
`--replay … --hasta` hace lo mismo sin vista. La persistencia sube a formato v3
y guarda la línea completa; un archivo de P1 se detecta como incompatible.

## Technical Context

**Language/Version**: Python 3.11+ (3.14.4 en el equipo).

**Primary Dependencies**: solo biblioteca estándar; reutiliza el motor de
eventos y el guardado existentes.

**Storage**: `partida_guardada.sav` binario v3 (+ copia JSON con envoltura de
versión); checkpoints y deltas dentro del archivo.

**Testing**: `unittest`, pruebas deterministas con semillas fijas y un oráculo
que re-simula desde cero.

**Target Platform**: CLI (Linux/Windows); `--replay` y `--bench` sin vista.

**Project Type**: proyecto único (modelo + adaptadores + controlador + vista).

**Performance Goals**: consulta `historia` ≤ 50 ms con ≥ 5000 acciones y el K
por defecto; memoria ∝ deltas + un checkpoint cada K.

**Constraints**:
- Sin `dict`, `set`, `heapq`, `bisect`, `collections` ni `networkx` en el
  problema evaluado.
- Determinismo: el checkpoint incluye el estado de `random.Random`.
- Máximo K acciones aplicadas/deshechas por consulta.
- `--replay … --hasta` y las consultas no instancian la vista.
- Archivos de P1 nunca se cargan en silencio.
- El conocimiento del mapa depende de la interfaz de A; se usa un doble hasta
  recibirla.

**Scale/Scope**: partidas de ≥ 5000 acciones; K a medir (candidatos 10, 25, 50,
100) y alternativa sin puntos de control.

## Constitution Check

| Principio | Cumplimiento | Evidencia / decisión |
|---|---|---|
| I. Estructuras a mano | PASA | `TablaOrdenada`/`ConjuntoOrdenado`, `BufferCircular` y búsqueda binaria propia; nada prohibido. |
| II. Determinismo | PASA | Re-simulación con la misma semilla y estado del azar en cada checkpoint. |
| III. MVC sin vista | PASA | El resumen histórico es un valor del modelo/controlador; `--hasta` no crea vista. |
| IV. Sin datos de cripta | PASA | Todo sale del estado y del log. |
| V. Presupuesto | PASA | La reconstrucción no hace solicitudes: usa los checkpoints y el contenido registrado. |
| VI. Rendimiento con `--bench` | PASA | Se medirá tiempo y memoria para ≥ 3 K y sin checkpoints. |
| VII. Spec antes que código | PASA | Spec 005 confirmada en `2dae08e`. |

**Resultado:** sin violaciones; no se necesita `Complexity Tracking`.

## Project Structure

### Documentation (this feature)

```text
specs/005-linea-de-tiempo/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── historia-cli.md
│   ├── persistencia-v3.md
│   └── interfaz-a-b-timeline.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
cripta/
├── modelo/
│   ├── timeline.py          # NUEVO: línea, checkpoints, reconstrucción y resumen
│   ├── guardable.py         # línea y conocimiento en el estado guardable
│   ├── juego.py             # (A) avanzar_hasta(t) y enlace con conocimiento
│   └── mapa.py              # (A) mapa conocido (interfaz)
├── adaptadores/
│   └── guardado.py          # formato v3 + detección de P1 (binario y JSON)
├── controlador/
│   ├── aplicacion.py        # --checkpoint-cada y --hasta
│   ├── controlador.py       # crear/registrar/recortar la línea y consultar
│   ├── comandos.py          # TipoComando.HISTORIA (contrato A↔B)
│   └── replay.py            # --replay … --hasta
├── vista/
│   ├── base.py              # (A) mostrar_historia
│   ├── vista_consola.py     # (A) parseo de "historia <t>|#k"
│   └── vista_grafica.py     # (A) mostrar el resumen
└── bench/
    ├── bench_timeline.py    # NUEVO: tiempo/memoria para ≥ 3 K y sin checkpoints
    └── runner.py            # registrar el bench

tests/
├── test_timeline.py         # NUEVO: AC-005-01..06, oráculo y recorte
├── test_integracion.py      # --hasta, guardar/cargar y P1
└── test_red.py              # sin cambios de red
```

**Structure Decision**: la línea es lógica de partida (modelo) y no conoce red
ni vista; el controlador la alimenta y la consulta. La reconstrucción usa un
`Mapa` propio del verificador histórico y un `Juego` reconstruido desde el
checkpoint, para no tocar la partida viva.

## Phase 0: Research

Salida: [`research.md`](./research.md). Decisiones:

- Línea = acciones + contenido nuevo + checkpoints; reconstrucción **hacia
  adelante** desde el checkpoint más cercano.
- Checkpoint = `EstadoGuardable` completo + estado de `random.Random`.
- Búsqueda binaria propia del checkpoint (nada de `bisect`).
- Recorte por posición al usar pergamino; descartar checkpoints posteriores.
- `Juego.avanzar_hasta(t)` para el estado exacto entre decisiones (interfaz
  con A).
- Persistencia v3 con línea completa y detección de P1.
- Mediciones de K y elección del valor por defecto.

## Phase 1: Design & Contracts

- [`data-model.md`](./data-model.md): `AccionRegistrada`, `PuntoControl`,
  `LineaTiempo`, `ResumenHistorico`, `ConocimientoSerializado`.
- [`contracts/historia-cli.md`](./contracts/historia-cli.md): comandos, salida,
  rechazos y `--hasta`.
- [`contracts/persistencia-v3.md`](./contracts/persistencia-v3.md): formato,
  versión y P1.
- [`contracts/interfaz-a-b-timeline.md`](./contracts/interfaz-a-b-timeline.md):
  `avanzar_hasta`, conocimiento del mapa y `mostrar_historia`.
- [`quickstart.md`](./quickstart.md): validación de los 6 escenarios.

## Re-evaluación de la Constitución (post-diseño)

| Principio | Resultado |
|---|---|
| I. Estructuras a mano | PASA: búsqueda binaria propia y contenedores del repo. |
| II. Determinismo | PASA: azar incluido en cada checkpoint. |
| III. MVC sin vista | PASA: resumen como dato; `--hasta` sin vista. |
| IV. Sin datos de cripta | PASA: todo viene del estado. |
| V. Presupuesto | PASA: reconstrucción sin red. |
| VI. Rendimiento | PASA: bench de K y memoria. |
| VII. Spec antes que código | PASA. |

## Complexity Tracking

Sin violaciones. La única complejidad adicional (registrar contenido nuevo por
acción) evita que la reconstrucción dependa de la red o de la partida viva.

## Trazabilidad requisitos → decisiones → tareas

| Requisitos | Decisión | Tareas |
|---|---|---|
| FR-001, FR-002, FR-003 | R1, R4 | T003, T004, T030, T031, T032 |
| FR-004, FR-005, FR-006, FR-007, FR-008 | R1, R2, R8 | T017, T018, T019, T020, T021, T022 |
| FR-009, FR-010 | R4 | T023, T024, T025 |
| FR-011, FR-012, FR-013, FR-014 | R5 | T026, T027, T028, T029 |
| FR-015, FR-016, FR-017, FR-018, FR-019, FR-020, FR-021 | R3, R6, R10 | T006, T007, T008, T042, T043, T044, T045, T046, T047 |
| FR-022, FR-023, FR-024 | R2, R9 | T033, T034, T035, T036 |
| FR-025, FR-026, FR-027, FR-028, FR-029 | R7 | T012, T013, T014, T037, T038, T039, T040, T041 |
| FR-030 | R6 + interfaz A | T005, T010, T053 |
| FR-031, FR-032 | R2, R9 | T004, T011, T017, T030 |
| NFR-001, NFR-002, NFR-003, NFR-004, NFR-005 | R3, R9, R10 | T042, T043, T044, T045, T046, T047 |
| SC-001, SC-002, SC-003, SC-004, SC-005, SC-006, SC-007 | Evidencia y trazabilidad | T017, T023, T026, T030, T033, T037, T042, T052 |

**Nota:** las menciones a `dict`, `set`, `heapq`, `bisect`, `collections` y
`networkx` en este plan son prohibiciones de la constitución, no dependencias.

## Dependencias externas

- **A**: `Juego.avanzar_hasta(t)`, serialización del conocimiento del mapa,
  `Vista.mostrar_historia` y parseo de `historia <t>|#k`.
- **Contrato A↔B**: `ComandoUsuario` gana `TipoComando.HISTORIA`.
- Hasta que A entregue el conocimiento, se usa la interfaz mínima con un doble
  de prueba (`tests/test_timeline.py`).

## Próximo paso

`/speckit.tasks` y `/speckit.analyze` antes de implementar.
