# Tasks: Niebla de guerra e «ir a»

**Input**: Design documents from `/specs/003-niebla-ir-a/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/`; spec 001 hasta T017 (búsqueda de rutas).

**Tests**: obligatorios y antes de la implementación; citan `003/FR-xxx` y
`AC-003-xx`.

---

## Phase 1: Setup

- [x] T001 Confirmar la línea base y que la spec 003 está clarificada y versionada (constitución VII).
- [x] T002 [P] Acordar con B el contrato `contracts/interfaz-a-b-conocimiento.md` (puntos 4 y 5).
- [x] T003 [P] Agregar a `tests/apoyo_p2.py` criptas pequeñas con antorcha, trampas, enemigos dormidos y puertas con cierre automático.

## Phase 2: Pruebas (primero)

- [x] T004 [P] [US1] Estados al inicio (inicial explorada, destinos avistados, resto desconocido) y al entrar a salas (FR-001..FR-006).
- [x] T005 [P] [US1] Memoria de puertas: observar al entrar y al cambiar estando presente; recuerdo viejo tras un cierre automático lejos; puerta sin observar (FR-007..FR-009).
- [x] T006 [P] [US4] AC-003-04: antorcha explora vecinas sin activar enemigos ni trampas; AC-003-05: un pergamino revierte la exploración de la antorcha (FR-010, FR-011, FR-015).
- [x] T007 [P] [US5] Guardar/cargar conserva el conocimiento; `historia #k` muestra el mapa conocido de ese momento (FR-014, FR-016).
- [x] T008 [P] [US3] AC-003-01 (destino no explorado ⇒ rechazo sin tiempo), AC-003-02 (puerta recordada abierta pero cerrada ⇒ se actualiza y recalcula; sin ruta ⇒ se detiene sin tiempo extra), AC-003-03 (enemigos dormidos se activan y el viaje se detiene), daño, llegada, no abre puertas, AC-003-06 (pergamino revierte solo el último paso) (FR-017..FR-023, FR-025, FR-026).
- [x] T009 [P] [US3] `partida.log` con un paso por línea y el comentario `# ir a N`; el replay del log da el mismo estado (FR-024, FR-027).

## Phase 3: Implementación

- [x] T010 [US1] `cripta/modelo/conocimiento.py` con `ConocimientoMapa` (arreglos por índice, explorar, observar, serializar, restaurar) (FR-001..FR-006, NFR-002, NFR-003).
- [x] T011 [US1] `CambioCasilla` en `cripta/modelo/historial.py` y `Juego._asignar_casilla` (FR-015, NFR-004).
- [x] T012 [US1] Revelar la sala al iniciar y al entrar; observar puertas al entrar, al abrir y al cerrarse estando presente (`efectos.cerrar_puerta`) (FR-002, FR-003, FR-007, FR-008).
- [x] T013 [US4] Antorcha: explorar vecinas al entrar mientras esté encendida (FR-010, FR-011).
- [x] T014 [US2] `MapaConocido` y `Juego.mapa_conocido()` para la vista y `historia` (FR-012, FR-013).
- [x] T015 [US2] Comando `mapa` y salidas según conocimiento en `cripta/vista/vista_consola.py` (FR-012, FR-013).
- [x] T016 [US2] Tecla `M` (mapa) y `G` (ir a) en `cripta/vista/vista_grafica.py` (FR-013, FR-026).
- [x] T017 [US5] `EstadoGuardable.conocimiento`, `serializar_conocimiento`/`restaurar_conocimiento`, codificación en `adaptadores/guardado.py` (FR-014).
- [x] T018 [US5] `ResumenHistorico` con salas exploradas y avistadas en `cripta/modelo/timeline.py`; `Juego.avanzar_hasta` (FR-016).
- [x] T019 [US3] `Juego.paso_hacia(destino)` con `BuscadorRutas` y el filtro de conocimiento (FR-019, FR-021, FR-023).
- [x] T020 [US3] `Controlador.ir_a()` con `ResultadoViaje`, validación sin tiempo y condiciones de parada; `TipoComando.IR_A` y `MAPA` (FR-017, FR-018, FR-020, FR-022, FR-026).
- [x] T021 [US3] `EscritorReplay.comentario()` y lectura que ignora `#` en `adaptadores/bitacora_replay.py` (FR-024).

## Phase 4: Mediciones

- [x] T022 `--bench mapa_conocido`: consulta de sala y puerta (arreglo vs. lista vs. `TablaOrdenada`), exploración y retroceso de 5 salas en `cripta/bench/bench_rutas.py` (NFR-002..NFR-005).
- [x] T023 `--bench ir_a`: paso con el mapa completo en la cripta de referencia, 2 500 y 10 000 salas (límite 5 ms); guardar en `docs/mediciones/p2_rutas.txt` y escribir §5.3 en `DECISIONES.md` (NFR-001, SC-003, SC-004).

## Phase 5: Auditoría de trazabilidad

- [x] T024 [P] Pruebas de las mediciones (casos registrados en `--bench`, exploración y retroceso con costo fijo, consultas de las tres estructuras) y del límite de 5 ms del paso de «ir a» en la referencia, en `tests/test_bench_rutas.py` (NFR-001, NFR-002, NFR-003, NFR-004, NFR-005).

## Notes

- `/speckit.analyze` (2026-11-15): cada FR tiene tarea y prueba; los cambios en
  archivos de B están en el contrato; ninguna tarea usa estructuras prohibidas.
- Auditoría de trazabilidad (2026-11-17): cada FR y NFR tiene al menos una
  tarea y una prueba que lo cita (`00N/FR-xxx` en el nombre o la descripción de
  la prueba). Los requisitos de medición se prueban con contadores deterministas
  (búsquedas, reutilizaciones, salas examinadas) en `tests/test_bench_rutas.py`.
  Matriz completa en [`trazabilidad.md`](./trazabilidad.md).
