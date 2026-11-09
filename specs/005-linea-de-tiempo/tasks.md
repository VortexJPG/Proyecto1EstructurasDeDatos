# Tasks: Línea de tiempo e historia

**Input**: Design documents from `/specs/005-linea-de-tiempo/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/`, `quickstart.md`

**Tests**: obligatorios (un escenario del Apéndice B por prueba, antes de la
implementación).

---

## Phase 1: Setup

- [ ] T001 Confirmar la línea base: 134/134 pruebas y `--bench` sin regresiones.
- [ ] T002 [P] Confirmar que la spec 005 y el plan están en Git antes de tocar código (constitución VII).

---

## Phase 2: Foundational (bloqueante)

- [x] T003 [P] Crear `cripta/modelo/timeline.py` con `AccionRegistrada`, `PuntoControl`, `ContenidoNuevo`, `LineaTiempo` y `ResumenHistorico` (FR-001..FR-005).
- [x] T004 Implementar el registro de una acción aceptada y su tiempo en el controlador (FR-004, FR-032).
- [x] T005 Implementar la captura de contenido nuevo por acción (movimiento y precarga) (FR-017, FR-030, FR-032).
- [x] T006 Implementar puntos de control cada K con `EstadoGuardable` completo, incluido el azar (FR-015, FR-018).
- [x] T007 [P] Añadir `--checkpoint-cada K` a `OpcionesEjecucion` y `aplicacion.py` (FR-015).
- [x] T008 [P] Implementar la búsqueda binaria propia del checkpoint más cercano (sin `bisect`) (FR-016, NFR-004).
- [x] T009 Implementar la reconstrucción en un `Mapa` propio con proveedor de fichas de solo lectura (FR-008, FR-017).
- [x] T010 [P] Añadir el doble de prueba del conocimiento del mapa (FR-030).
- [x] T011 Implementar el oráculo de re-simulación desde cero en `tests/test_timeline.py` (NFR-005, SC-003).
- [x] T012 [P] Añadir `linea` y `conocimiento` a `EstadoGuardable` (FR-025, FR-030).
- [x] T013 [P] Codificar/decodificar la línea en el formato binario v3 (FR-025..FR-027, FR-026).
- [x] T014 [P] Añadir `version_formato` y la línea a la copia JSON (FR-028).
- [x] T015 Conectar la línea al controlador: crear al iniciar, registrar tras cada acción y exportar al guardar (FR-001, FR-025, FR-029).
- [ ] T016 [BLOQUEADA A] Acordar con A `Juego.avanzar_hasta(t)` y `Juego.ejecutar_accion(accion, hasta=...)` (`contracts/interfaz-a-b-timeline.md`).

**Checkpoint**: línea, checkpoints y persistencia listos para las historias.

---

## Phase 3: US1 — Consultar el pasado (P1) 🎯 MVP

**Goal**: `historia <t>` y `historia #k` muestran el estado correcto sin tocar
la partida.

### Pruebas (primero)

- [ ] T017 [P] [US1] Prueba de `historia <t>` y `historia #k` sobre una partida sintética (FR-004..FR-005, FR-010, FR-031).
- [ ] T018 [P] [US1] Prueba de que la consulta no cambia reloj, log ni historial de retroceso (FR-006..FR-008, FR-007, AC-005-04).

### Implementación

- [ ] T019 [US1] Implementar `consultar_historia(argumento)` en el controlador: parseo de `<t>`/`#k`, búsqueda de checkpoint y reconstrucción (FR-004..FR-008).
- [ ] T020 [US1] Implementar `ResumenHistorico` y su texto legible (FR-005).
- [ ] T021 [US1] Añadir `TipoComando.HISTORIA` y el despacho en `procesar_comando` (FR-004).
- [ ] T022 [A] Parsear `historia` y mostrar el resumen en consola y ventana (`mostrar_historia`) (FR-004, FR-005).

**Checkpoint**: `historia` funciona en una partida real.

---

## Phase 4: US2 — Rechazar consultas imposibles (P1)

- [ ] T023 [P] [US2] Prueba `AC-005-01`: t posterior al reloj se rechaza (FR-009).
- [ ] T024 [P] [US2] Prueba de t negativo y de `#k` fuera de rango (FR-009).
- [ ] T025 [US2] Implementar la validación y los mensajes de rechazo (FR-009, FR-014).

---

## Phase 5: US3 — La línea respeta el pergamino (P1)

- [x] T026 [P] [US3] Prueba `AC-005-02`: las acciones revertidas no aparecen (FR-011, FR-012).
- [x] T027 [P] [US3] Prueba de que se descartan los checkpoints posteriores y se rechaza el futuro (FR-013, FR-014).
- [x] T028 [US3] Implementar el recorte por `acciones_ejecutadas` al aceptar un pergamino (FR-011..FR-013).
- [x] T029 [US3] Renumerar `#k` sobre la línea vigente (FR-012).

---

## Phase 6: US4 — Varios eventos en el mismo instante (P1)

- [ ] T030 [P] [US4] Prueba `AC-005-03` con varios eventos en t (FR-002, FR-032).
- [ ] T031 [US4] Integrar `avanzar_hasta(t)` para detenerse después de todos los eventos ≤ t (FR-002, FR-003).
- [ ] T032 [US4] Garantizar que una decisión en t muestra el estado justo antes (FR-003).

---

## Phase 7: US5 — Replay sin vista (P1)

- [ ] T033 [P] [US5] Prueba de `--replay … --hasta t` con el mismo resumen que `historia` y sin vista (FR-022, FR-023).
- [ ] T034 [P] [US5] Prueba `AC-005-05`: t posterior al final muestra el final y el motivo (FR-024).
- [ ] T035 [US5] Implementar `--hasta` en `aplicacion.py` y `ReproductorReplay` (FR-022..FR-024).
- [ ] T036 [US5] Formatear el resumen de `--hasta` sin crear la vista (FR-023).

---

## Phase 8: US6 — Persistencia de la línea (P1)

- [x] T037 [P] [US6] Prueba de guardar/cargar conservando la línea y consultas posteriores (FR-025, FR-029).
- [x] T038 [P] [US6] Prueba `AC-005-06`: `.sav` v2 y JSON sin versión se rechazan (FR-027, FR-028).
- [x] T039 [US6] Terminar la codificación/decodificación v3 de acciones, contenidos y checkpoints (FR-025..FR-027).
- [x] T040 [US6] Implementar la detección explícita de P1 en binario y JSON (FR-027, FR-028).
- [x] T041 [US6] Reconstruir la línea al cargar y permitir seguir registrando (FR-029).

---

## Phase 9: US7 — Checkpoints y rendimiento (P2)

- [ ] T042 [P] [US7] Prueba de que una consulta no aplica ni deshace más de K acciones (FR-016).
- [ ] T043 [P] [US7] Prueba de memoria: checkpoints cada K y acciones, no estados por acción (FR-020, NFR-002).
- [ ] T044 [US7] Crear `cripta/bench/bench_timeline.py` con K ∈ {10, 25, 50, 100} y sin checkpoints (NFR-001, NFR-002, NFR-003, NFR-004).
- [ ] T045 [US7] Registrar el bench en `runner.py` y hacer configurables tamaños y límites (NFR-004).
- [ ] T046 [US7] Medir 5000 acciones y elegir el K por defecto con la tabla de tiempo/memoria (FR-021, NFR-001, SC-004).
- [ ] T047 [US7] Documentar el K elegido, la alternativa sin checkpoints y la decisión adelante/atrás (FR-019, FR-021).

---

## Phase 10: Polish y cierre

- [ ] T048 [P] Actualizar `README.md` con `historia`, `--hasta` y `--checkpoint-cada` (FR-004, FR-022).
- [ ] T049 [P] Añadir las secciones §5.5 y §5.6-B a `Decisiones_de_diseño.md` con la evidencia (FR-019, FR-021).
- [ ] T050 Auditar estructuras prohibidas en `timeline.py`, el bench y la persistencia (constitución I).
- [ ] T051 Ejecutar la suite completa, `--bench timeline` y guardar la evidencia en `docs/mediciones/p2_timeline.txt` (SC-002, SC-005, SC-006).
- [ ] T052 Auditoría de trazabilidad `AC-005-01..06` → tarea → código → prueba, y de `SC-001..SC-007` (SC-001..SC-007).

---

## Dependencia externa — Persona A (Fase 6)

- [ ] T053 [BLOQUEADA A] Sustituir el doble de conocimiento por `serializar_conocimiento` / `restaurar_conocimiento` de A (FR-030).
- [ ] T054 [BLOQUEADA A] Integrar `avanzar_hasta` y el límite de `ejecutar_accion` en el modelo (FR-002).
- [ ] T055 [BLOQUEADA A] Mostrar `historia` en la vista y parsear el comando (FR-004).
- [ ] T056 [BLOQUEADA A] Verificar el caso cruzado: pergamino con antorcha revierte el mapa conocido y `historia` coincide (FR-011, FR-030).

---

## Dependencias entre tareas

```text
T003..T015 → línea, checkpoints y persistencia base
T016       → interfaz de avance con A (bloquea T031)
T017..T022 → US1 (consulta) depende de T003..T015
T023..T025 → US2 depende de US1
T026..T029 → US3 depende de US1
T030..T032 → US4 depende de T016
T033..T036 → US5 depende de US1
T037..T041 → US6 depende de T013..T016
T042..T047 → US7 depende de T003..T016
T048..T052 → cierre
T053..T056 → Fase 6 con A
```

## MVP

**US1 + US2 + US3**: consultar el pasado, rechazar instantes imposibles y
respetar el pergamino. US4..US7 completan exactitud temporal, replay,
persistencia y rendimiento.
