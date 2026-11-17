# Tasks: Invalidación de rutas

**Input**: Design documents from `/specs/002-invalidacion-rutas/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`; spec 001 implementada
hasta T017.

**Tests**: obligatorios y antes de la implementación; citan `002/FR-xxx` y
`AC-002-xx`.

---

## Phase 1: Setup

- [x] T001 Confirmar la línea base y que la spec 002 está clarificada y versionada (constitución VII).
- [x] T002 [P] Reutilizar el oráculo desde cero de `tests/apoyo_p2.py` (FR-001).
- [x] T003 [P] Agregar a `tests/apoyo_p2.py` una cuadrícula con puertas abiertas en todos los pasajes y cazadores repartidos (FR-009).

## Phase 2: Pruebas (primero)

- [x] T004 [P] Prueba AC-002-01: una puerta de la ruta del cazador se cierra entre dos turnos ⇒ la decisión coincide con el oráculo (otra ruta o esperar) en `tests/test_invalidacion.py` (FR-001, FR-003).
- [x] T005 [P] Prueba: el jugador cambia de sala ⇒ la siguiente decisión apunta a la sala nueva (FR-003).
- [x] T006 [P] Prueba AC-002-02: una puerta se cierra fuera de la región ⇒ mismas decisiones y ningún cálculo nuevo (contadores) (FR-004, FR-005).
- [x] T007 [P] Prueba: un pergamino revierte una apertura de puerta ⇒ la siguiente decisión coincide con el oráculo (FR-006).
- [x] T008 Prueba aleatoria: puertas que cambian, jugador que se mueve y cazadores que mueren; cada decisión de cada estrategia coincide con el oráculo (FR-001, FR-002, SC-002).
- [x] T009 Prueba AC-002-03: la misma partida con las cuatro estrategias da el mismo estado final y el mismo `partida.log` (FR-007, FR-008).

## Phase 3: Implementación

- [x] T010 `Puerta.cerrada` como propiedad que avisa al mapa (`Mapa.al_cambiar_puerta`) en `cripta/modelo/mapa.py` (FR-003, FR-005).
- [x] T011 `RutasCazadores` en `cripta/modelo/rutas.py`: caché con sala objetivo y alcance, región por marcas de generación, invalidación fina y contadores (`calculos`, `reutilizados`) (FR-002..FR-006, FR-010).
- [x] T012 `EstrategiaCazador` con `COMPARTIDA`, `COMPARTIDA_GRUESA`, `RECALCULAR_SIEMPRE` e `INDIVIDUAL`, elegible al crear el `Juego` (FR-008).
- [x] T013 `Juego` crea `RutasCazadores` y registra el oyente de puertas; `desde_estado` arranca con caché vacía (FR-006, FR-007).
- [x] T016 La caché es perezosa: sin cazadores que decidan no se calcula nada (FR-011).

## Phase 4: Mediciones

- [x] T014 `--bench invalidacion` en `cripta/bench/bench_rutas.py`: puertas estables vs. inestables × cuatro estrategias, con tiempo, cálculos, reutilizados y salas examinadas (FR-009, FR-010, NFR-002, NFR-003).
- [x] T015 Las cuatro estrategias en la cripta de referencia con el bot; guardar en `docs/mediciones/p2_rutas.txt` y escribir §5.2 en `DECISIONES.md` (SC-003, SC-004).
- [x] T017 Revisar el límite de 20 ms con la estrategia por defecto (NFR-001).

## Phase 5: Auditoría de trazabilidad

- [x] T018 [P] Pruebas de las mediciones con contadores deterministas (una búsqueda con puertas estables, cero invalidaciones con puertas lejanas, menos salas examinadas que recalcular) y del límite de 20 ms, en `tests/test_bench_rutas.py` (FR-005, FR-009, FR-010, NFR-001, NFR-002, NFR-003).

## Notes

- `/speckit.analyze` (2026-11-15): todos los FR tienen tarea; T010 toca
  `mapa.py`, que es de la Persona A; ningún cambio a contratos de la Persona B.
- Auditoría de trazabilidad (2026-11-17): cada FR y NFR tiene al menos una
  tarea y una prueba que lo cita (`00N/FR-xxx` en el nombre o la descripción de
  la prueba). Los requisitos de medición se prueban con contadores deterministas
  (búsquedas, reutilizaciones, salas examinadas) en `tests/test_bench_rutas.py`.
  Matriz completa en [`trazabilidad.md`](./trazabilidad.md).
