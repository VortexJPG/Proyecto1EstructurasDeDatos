# Tasks: Terreno y cazador

**Input**: Design documents from `/specs/001-terreno-cazador/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`

**Tests**: obligatorios. En cada historia la prueba va antes de la
implementación y cita el requisito (`001/FR-xxx`, `AC-001-xx`).

**Formato**: `[ID] [P?] [US?] Descripción con ruta y requisito`.

---

## Phase 1: Setup

- [x] T001 Confirmar la línea base: `python -m unittest discover -s tests` en verde antes de tocar código (constitución, flujo 1).
- [x] T002 [P] Confirmar que `spec.md` de 001 está clarificada y versionada antes del código (constitución VII).
- [x] T003 [P] Preparar `tests/apoyo_p2.py`: constructor de criptas a mano (salas, salidas con costo y puertas, fichas) y oráculo de distancias desde cero O(V²) sin estructuras prohibidas (FR-015, SC-002).

## Phase 2: Foundational

- [x] T004 Prueba: costo por defecto 100, costo compartido por pasaje y primer sentido en el orden del esqueleto en `tests/test_terreno_cazador.py` (FR-001, FR-002).
- [x] T005 Prueba: `costo` 0, negativo o no entero ⇒ `ValueError` con sala y dirección (FR-003).
- [x] T006 [P] Prueba: el jugador cruza una salida de costo 250 y su turno queda en t=250; un errante y un rastreador tardan el costo de la salida (FR-004, FR-005, FR-006).
- [x] T007 [P] Prueba: ficha de cazador sin `rango` o con `rango` < 1 ⇒ `ValueError` (FR-008).
- [x] T010 Implementar `Salida.costo`, `Salida.origen`, `Sala.indice`, `Sala.entradas`, `Puerta.indice` y `Puerta.salas` en `cripta/modelo/mapa.py`, con la validación de costo (FR-001, FR-002, FR-003).
- [x] T011 Usar el costo de la salida en `Juego._mover` en `cripta/modelo/juego.py` (FR-004).
- [x] T012 Devolver el costo de la salida en `_actuar_errante` y `_actuar_rastreador` en `cripta/modelo/comportamiento.py` (FR-005).
- [x] T013 [P] Prueba de AC-001-05 (velocidad 200 con costo 1 ⇒ intervalo 1) y AC-001-06 (cambio de velocidad durante un movimiento de costo 300) (FR-004, FR-007).
- [x] T014 Agregar `Comportamiento.CAZADOR` y `Enemigo.rango` validado en `cripta/modelo/actores.py` (FR-008).

**Checkpoint**: el terreno funciona para todos los actores.

## Phase 3: US2 — El cazador persigue por la ruta más barata (P1) 🎯 MVP

- [x] T008 [P] [US2] Pruebas AC-001-01 (sin ruta ⇒ espera 100), AC-001-02 (d > rango ⇒ espera 100), AC-001-03 (menos salas pero más caro), ataque en la misma sala y movimiento de una sola sala con el costo de la salida (FR-009..FR-012).
- [x] T015 [US2] Crear `cripta/modelo/rutas.py` con `BuscadorRutas`: Dijkstra inverso sobre `Sala.entradas`, `MonticuloMin` con claves enteras, arreglos con marcas de generación, alcance y parada temprana (FR-010, NFR-002).
- [x] T016 [US2] Implementar `primer_paso` con la regla de desempate sobre distancias finalizadas (FR-012, FR-013).
- [x] T017 [US2] Implementar `_actuar_cazador` en `cripta/modelo/comportamiento.py` usando `juego.rutas` (FR-009..FR-012).

## Phase 4: US3 — Desempate reproducible (P1)

- [x] T009 [P] [US3] Prueba AC-001-04 (dos vecinas empatadas ⇒ menor id) y misma vecina por dos salidas ⇒ primera en N, S, E, O (FR-013).
- [x] T018 [US3] Prueba aleatoria: cientos de situaciones deterministas (cuadrículas con costos iguales y aleatorios, puertas cerradas al azar) donde cada decisión coincide con el oráculo (FR-013, FR-015, SC-002).
- [x] T019 [US3] Prueba: la decisión no depende de que el contenido de las salas esté cargado ni de la niebla (FR-014).
- [x] T020 [US3] Prueba: cazador dormido no actúa; la decisión no consume el azar y dos corridas dan la misma partida (FR-016, FR-017, SC-005).
- [x] T021 [US3] Conectar con la spec 002 (`RutasCazadores` y sus estrategias) y probar que todas dan las mismas decisiones (FR-015).

## Phase 5: US5 — Ver el terreno y reconocer a los cazadores (P2)

- [x] T022 [P] [US5] Mostrar el costo de cada salida y la marca `[cazador, rango N]` en `cripta/vista/vista_consola.py`, con prueba en `tests/test_terreno_cazador.py` (FR-019, FR-020).
- [x] T023 [P] [US5] Mostrar el costo en el panel de salidas y la marca de cazador en `cripta/vista/vista_grafica.py` (FR-019, FR-020).

## Phase 6: US4 — Decenas de cazadores (P2) y mediciones

- [x] T024 Mejorar el harness `cripta/bench/runner.py`: mediana, p95 y máximo, y revisión de límites con PASA/FALLA (NFR-004).
- [x] T025 Crear `cripta/bench/bench_rutas.py`: 1 vs. 10 vs. 50 cazadores, rango pequeño vs. grande, compartido vs. individual (FR-021, NFR-003).
- [x] T026 [P] Medir montículo vs. búsqueda lineal del mínimo y el tiempo de una decisión de rango pequeño al crecer la cripta (NFR-002, SC-004).
- [x] T027 Medir el ciclo en la cripta de referencia con todos los cazadores activos y revisar el límite de 20 ms (NFR-001, SC-003).
- [x] T028 Guardar la salida en `docs/mediciones/p2_rutas.txt` y escribir §5.1 en `DECISIONES.md` (NFR-003).

## Phase 7: Auditoría de trazabilidad

- [x] T029 [P] Prueba de que `cripta/` no tiene ids reales de criptas, instancias ni fichas (leídos de los paquetes offline) y quitar el id escrito en el bench, en `tests/test_terreno_cazador.py` y `cripta/bench/bench_rutas.py` (FR-018).
- [x] T030 [P] Pruebas de las mediciones con contadores deterministas y del límite de 20 ms en la cripta de referencia, en `tests/test_bench_rutas.py` (FR-021, NFR-001, NFR-002, NFR-003, NFR-004).

## Dependencies & Execution Order

- T003 antes de todas las pruebas.
- T010 → T011/T012 → T015 → T016 → T017.
- T021 depende de la spec 002 (`RutasCazadores`).
- T025..T028 dependen de T017 y de T021.

## Notes

- `/speckit.analyze` (2026-11-15): sin requisitos sin tarea; FR-015 se cubre con
  la spec 002 (T021); ninguna tarea propone estructuras prohibidas; la spec no
  nombra estructuras.
- Auditoría de trazabilidad (2026-11-17): cada FR y NFR tiene al menos una
  tarea y una prueba que lo cita (`00N/FR-xxx` en el nombre o la descripción de
  la prueba). Los requisitos de medición se prueban con contadores deterministas
  (búsquedas, reutilizaciones, salas examinadas) en `tests/test_bench_rutas.py`.
  Matriz completa en [`trazabilidad.md`](./trazabilidad.md).
