# Implementation Plan: Invalidación de rutas

**Branch**: `002-invalidacion-rutas` | **Date**: 2026-11-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-invalidacion-rutas/spec.md`

## Summary

El cálculo compartido de la spec 001 (distancias de todas las salas hacia la
sala del jugador, hasta un alcance) se **guarda y se reutiliza** entre
cazadores y entre turnos mientras siga siendo válido. Se invalida solo por los
eventos que pueden cambiar la respuesta: (1) el jugador cambió de sala;
(2) cambió una puerta con al menos una de sus salas dentro de la región del
cálculo; (3) decide un cazador con rango mayor que el alcance. Para detectar
(2) sin depender de que cada regla avise a mano, `Puerta.cerrada` pasa a ser
una propiedad que notifica al mapa en **toda** asignación (abrir, cerrar,
retroceso, carga). Mover o matar actores y cambiar velocidades no invalida.
Se agregan las estrategias "recalcular siempre", "invalidación gruesa" e
"individual" para medir, y todas producen la misma partida.

## Technical Context

**Language/Version**: Python 3.11+.

**Primary Dependencies**: ninguna nueva.

**Storage**: N/A. El cálculo es derivado: no se guarda ni se revierte.

**Testing**: `unittest` con un oráculo desde cero; simulación aleatoria con
puertas que cambian y comparación de cada decisión; partidas idénticas entre
estrategias.

**Target Platform**: CLI y `--bench` sin vista.

**Performance Goals**: ≤ 20 ms por ciclo con decenas de cazadores; menos salas
examinadas con puertas estables.

**Constraints**: §6.2 (sin `dict`, `set`, `heapq`, `bisect`, `collections`);
determinismo.

**Scale/Scope**: cripta de referencia (300 salas, 56 puertas, 36 cazadores) y
cuadrículas sintéticas con muchas puertas.

## Constitution Check

| Principio | Cumplimiento | Evidencia |
|---|---|---|
| I. Estructuras a mano | PASA | Reutiliza `BuscadorRutas` (montículo y arreglos propios); la región se consulta con las marcas de generación en O(1). |
| II. Determinismo | PASA | La caché no decide nada: solo evita repetir un cálculo que daría lo mismo; probado contra el oráculo y entre estrategias. |
| III. MVC sin vista | PASA | Todo en el modelo; contadores para `--bench`. |
| IV. Sin datos de cripta | PASA | |
| V. Presupuesto | PASA | Sin solicitudes. |
| VI. Rendimiento con `--bench` | PASA | Puertas estables vs. inestables; reutilizar vs. recalcular siempre. |
| VII. Spec antes que código | PASA | |

## Project Structure

```text
specs/002-invalidacion-rutas/
├── spec.md
├── plan.md
├── research.md
├── checklists/requirements.md
└── tasks.md

cripta/modelo/
├── mapa.py        # Puerta.cerrada como propiedad que avisa al mapa
├── rutas.py       # RutasCazadores: estrategias, caché, región e invalidación
└── juego.py       # registra el oyente de puertas; expone juego.rutas
cripta/bench/
└── bench_rutas.py # escenarios de puertas estables e inestables
tests/
└── test_invalidacion.py
```

## Phase 0: Research

Ver [`research.md`](./research.md): tabla evento → información invalidada,
prueba de que una puerta fuera de la región no cambia la respuesta, cómo se
detectan los cambios de puertas (propiedad) y por qué la caché no es estado.

## Phase 1: Design

### Tabla de invalidación

| Evento | ¿Puede cambiar la decisión? | Qué se invalida |
|---|---|---|
| El jugador cambia de sala | Sí (cambia el objetivo) | Todo el cálculo |
| Se abre/cierra una puerta con una sala en la región | Sí | Todo el cálculo |
| Se abre/cierra una puerta con las dos salas fuera de la región | No (R2 de research) | Nada |
| Decide un cazador con rango > alcance | Para ese cazador | Se rehace con alcance mayor |
| Otro actor se mueve, muere o se activa | No (los actores no bloquean) | Nada; cada cazador lee su propia sala |
| Cambia una velocidad | No (cambia cuándo, no hacia dónde) | Nada |
| Retroceso | Sí (puertas y sala del jugador) | Lo detectan la propiedad de puertas y la comparación de sala |
| Cargar partida / reconstruir para `historia` | Sí | Juego nuevo ⇒ caché vacía |

### Estrategias (`EstrategiaCazador`)

| Estrategia | Qué hace | Para qué |
|---|---|---|
| `COMPARTIDA` (por defecto) | Un cálculo desde el jugador, reutilizado con invalidación fina | Juego |
| `COMPARTIDA_GRUESA` | Igual, pero cualquier cambio de puerta invalida | Medir el valor de la invalidación fina |
| `RECALCULAR_SIEMPRE` | Un cálculo desde el jugador en cada turno de cazador | "Recalcular siempre" de §5.2 |
| `INDIVIDUAL` | Un cálculo por turno, acotado por el rango del cazador y detenido al llegar a su sala | "Un cálculo por cazador" de §5.1 |

### Mediciones planificadas

- Cuadrícula sintética de 2 500 salas con todas las salidas con puerta abierta,
  30 cazadores de rango 2 400 lejos del jugador, 200 decisiones.
- Puertas estables (0 cambios por decisión) vs. inestables (20 cambios por
  decisión, elegidos con semilla en toda la cripta).
- Para cada estrategia: tiempo por decisión (mediana), cálculos hechos,
  reutilizados y salas examinadas.
- Las mismas cuatro estrategias en la cripta de referencia jugando una
  partida con el bot (puertas reales con cierre automático).

## Re-evaluación de la Constitución (post-diseño)

Sin cambios: PASA en los siete principios.

## Complexity Tracking

La propiedad de `Puerta.cerrada` agrega una llamada por cambio de puerta (no
por consulta). Se justifica porque cubre retroceso, carga y efectos sin tener
que recordar avisar en cada regla.

## Trazabilidad

| Requisitos | Decisión | Tareas |
|---|---|---|
| FR-001, FR-002 | R1, R2 | T004, T008, T009 |
| FR-003 | tabla de invalidación | T005, T010 |
| FR-004, FR-005 | R2 | T006, T010 |
| FR-006 | R3 | T007, T011 |
| FR-007, FR-008 | estrategias | T012, T013 |
| FR-009, FR-010, NFR-002, NFR-003 | mediciones | T014, T015, T018 |
| FR-011 | caché perezosa | T016 |
| NFR-001 | spec 001 | T017, T018 |
