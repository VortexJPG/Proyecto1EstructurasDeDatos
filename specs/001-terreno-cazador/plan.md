# Implementation Plan: Terreno y cazador

**Branch**: `001-terreno-cazador` | **Date**: 2026-11-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-terreno-cazador/spec.md`

**Note**: plan escrito siguiendo `/speckit.plan`. Las decisiones con sus
alternativas están en [`research.md`](./research.md) y las entidades en
[`data-model.md`](./data-model.md).

## Summary

Cada salida tiene un costo (100 si no lo declara) que reemplaza la constante
de movimiento de la Parte I para todos los actores. El cazador decide con una
**búsqueda de costo mínimo hacia el jugador** (Dijkstra sobre las salidas de
entrada, es decir, en sentido inverso) acotada por el alcance necesario, con
un **montículo binario propio** para escoger la siguiente sala y **arreglos
indexados por posición de sala con marcas de generación** para registrar
distancias sin reiniciar arreglos completos. Como todos los cazadores
persiguen al mismo objetivo, una sola búsqueda desde la sala del jugador da la
distancia de todas las salas a la vez: cada cazador decide en O(grado) leyendo
las distancias de sus vecinas y aplicando el desempate de §3.2. La
alternativa "un cálculo por cazador" se mantiene como estrategia medible.

## Technical Context

**Language/Version**: Python 3.11+ (desarrollo con 3.14).

**Primary Dependencies**: solo biblioteca estándar; ninguna biblioteca de
grafos ni de rutas.

**Storage**: N/A (el costo viene en el esqueleto que ya persiste la Persona B).

**Testing**: `unittest`; oráculo de referencia "desde cero" en las pruebas
(Dijkstra sin montículo, O(V²)) para comparar cada decisión.

**Target Platform**: CLI (terminal y ventana); `--bench` sin vista.

**Project Type**: proyecto único MVC existente.

**Performance Goals**: ciclo entre decisiones ≤ 20 ms con decenas de cazadores
en la cripta de referencia (300 salas, 36 cazadores); decisión de rango
pequeño independiente del tamaño de la cripta.

**Constraints**: prohibidos `dict`, `set`, `heapq`, `bisect`, `collections`,
`networkx` y bibliotecas de rutas (§6.2); determinismo; sin datos de cripta en
el código.

**Scale/Scope**: criptas publicadas de 6 a 300 salas; el bench usa criptas
sintéticas de hasta 10 000 salas.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumplimiento | Evidencia / decisión |
|---|---|---|
| I. Estructuras a mano | PASA | `MonticuloMin` propio (Parte I) y arreglos `list` como almacenamiento contiguo; nada de `heapq`, `dict` ni `set`. |
| II. Determinismo | PASA | La decisión no usa el azar; salidas en N, S, E, O; desempate por menor id definido por la regla, no por el orden del montículo. |
| III. MVC sin vista | PASA | La búsqueda vive en el modelo; `--bench` construye juegos sin vista. |
| IV. Sin datos de cripta | PASA | Costos y rangos vienen del esqueleto y del catálogo. |
| V. Presupuesto | PASA | No hace solicitudes: el esqueleto completo ya se descarga al iniciar. |
| VI. Rendimiento con `--bench` | PASA | Se mide compartido vs. individual, rango pequeño vs. grande y 1 vs. muchos. |
| VII. Spec antes que código | PASA | `spec.md` clarificada; el código empieza después de confirmarla. |

**Resultado del gate:** sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/001-terreno-cazador/
├── spec.md
├── plan.md              # este archivo
├── research.md          # decisiones R1..R7 con alternativas
├── data-model.md        # entidades y validaciones
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
cripta/
├── modelo/
│   ├── mapa.py            # Salida.costo, Salida.origen, Sala.indice, Sala.entradas,
│   │                      #   validación de costo, costo compartido por pasaje
│   ├── actores.py         # Comportamiento.CAZADOR, Enemigo.rango (validado)
│   ├── rutas.py           # NUEVO: BuscadorRutas (Dijkstra inverso acotado) y
│   │                      #   RutasCazadores (estrategias y caché, spec 002)
│   ├── comportamiento.py  # _actuar_cazador; errante/rastreador devuelven el costo
│   └── juego.py           # _mover usa el costo de la salida; crea RutasCazadores
├── vista/
│   ├── vista_consola.py   # costo de cada salida, marca [cazador]
│   └── vista_grafica.py   # costo en el panel de salidas, marca de cazador
└── bench/
    ├── runner.py          # harness: mediana, p95, máximo y revisión de límites
    └── bench_rutas.py     # NUEVO: compartido vs. individual, rango, 1 vs. muchos

tests/
├── apoyo_p2.py            # NUEVO: criptas de prueba a mano y oráculo desde cero
└── test_terreno_cazador.py # NUEVO: AC-001-01..06 y FR-001..FR-021
```

**Structure Decision**: la búsqueda es lógica del juego (modelo). Se separa en
`rutas.py` porque la usan dos clientes: el cazador (spec 001/002) y «ir a»
(spec 003), con filtros de salidas distintos.

## Phase 0: Outline & Research

Salida: [`research.md`](./research.md). Resuelve:

- R1: dirección de la búsqueda (desde cada cazador vs. desde el jugador);
- R2: cola de prioridad (montículo propio vs. búsqueda lineal del mínimo);
- R3: registro de distancias sin reiniciar arreglos (marcas de generación);
- R4: cómo cumplir el desempate con cualquier algoritmo;
- R5: acotar por rango;
- R6: costo de un pasaje con declaraciones distintas;
- R7: mediciones planificadas.

## Phase 1: Design & Contracts

- [`data-model.md`](./data-model.md): `Salida.costo`, `Sala.indice`,
  `Sala.entradas`, `Enemigo.rango`, `BuscadorRutas`.
- Contrato con la Persona B: el de
  [`specs/004-resolubilidad-llaves/contracts/interfaz-a-b.md`](../004-resolubilidad-llaves/contracts/interfaz-a-b.md)
  (lectura de `costo` y `rango`). No se crea contrato nuevo.

### Estructuras elegidas

| Problema | Estructura | Alternativa medida | Complejidad esperada |
|---|---|---|---|
| Siguiente sala a examinar | `MonticuloMin` (Parte I) con claves enteras `dist·n + índice` | Búsqueda lineal del mínimo en un arreglo | O((V'+E') log V') vs. O(V'²) |
| Distancias | Arreglo por índice de sala + marca de generación | Reiniciar el arreglo en cada búsqueda | O(V') vs. O(V) por búsqueda |
| Salidas de entrada | `Sala.entradas` (arreglo por sala, armado una vez) | Recorrer todas las salas | O(grado) vs. O(V) |
| Decisión de un cazador | Lectura O(grado) de distancias compartidas | Una búsqueda por cazador | O(1·búsqueda + N·grado) vs. O(N·búsqueda) |

V' y E' son las salas y salidas dentro del alcance de la búsqueda.

### Módulos afectados

`mapa.py`, `actores.py`, `comportamiento.py`, `juego.py`, nuevo `rutas.py`,
las dos vistas, `bench/runner.py`, nuevo `bench/bench_rutas.py`.

### Mediciones planificadas (§6.3)

- Un cazador frente a 10 y 50 cazadores activos.
- Rango pequeño (300) frente a rango grande (sin límite efectivo).
- Cálculo compartido frente a individual.
- Criptas sintéticas deterministas de 400, 2 500 y 10 000 salas con costos
  aleatorios, y la cripta de referencia (offline).
- Montículo frente a búsqueda lineal del mínimo.
- Ciclo entre decisiones (mediana, p95 y máximo) en la cripta de referencia
  con todos los cazadores activos (límite 20 ms).

## Re-evaluación de la Constitución (post-diseño)

| Principio | Resultado |
|---|---|
| I | PASA: solo `MonticuloMin` y arreglos propios. |
| II | PASA: el desempate se aplica sobre distancias exactas, independiente del orden de exploración. |
| III | PASA. |
| IV | PASA. |
| V | PASA. |
| VI | PASA. |
| VII | PASA. |

## Complexity Tracking

Sin violaciones. La única complejidad añadida (marcas de generación y claves
enteras en el montículo) se justifica con las mediciones de R2 y R3.

## Trazabilidad requisitos → decisiones → tareas

| Requisitos | Decisión | Tareas |
|---|---|---|
| FR-001, FR-002, FR-003 | R6 | T004, T005, T010 |
| FR-004, FR-005, FR-006, FR-007 | costo en `_mover` y en la IA | T006, T011, T012, T013 |
| FR-008 | validación de la ficha | T007, T014 |
| FR-009, FR-010, FR-011, FR-012 | R1, R2, R3, R5 | T008, T015, T016, T017 |
| FR-013 | R4 | T009, T018 |
| FR-014, FR-016, FR-017, FR-018 | R1 | T019, T020, T029 |
| FR-015 | spec 002 | T021 |
| FR-019, FR-020 | vistas | T022, T023 |
| FR-021, NFR-001..NFR-004 | R7 | T024..T028, T030 |

**Nota:** las menciones a estructuras prohibidas son prohibiciones de la
constitución, no dependencias.
