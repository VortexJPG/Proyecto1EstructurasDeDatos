# Tasks: Resolubilidad y llaves

**Input**: Design documents from `/specs/004-resolubilidad-llaves/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/`, `quickstart.md`

**Tests**: obligatorios (el documento de la Parte II exige una prueba por
escenario y prueba antes de implementación). En cada historia, la tarea de
prueba va **antes** de la implementación y debe fallar primero.

**Formato**: `[ID] [P?] [US?] Descripción con ruta y requisito`.

---

## Phase 1: Setup

**Propósito**: dejar el terreno listo sin tocar lógica de juego.

- [ ] T001 Confirmar la línea base: `.venv/bin/python -m unittest discover -s tests` en verde y `--bench` sin cambios (SC-001).
- [ ] T002 [P] Verificar que la spec 004 y el plan están confirmados en Git antes de tocar código (constitución VII).

---

## Phase 2: Foundational (bloqueante)

**Propósito**: contrato de llaves, persistencia, presupuesto, generador
sintético y oráculo. Sin esto ninguna historia se puede probar.

- [x] T003 [P] Añadir `llaves(cripta_id)` a `cripta/adaptadores/fuente_datos.py` y su DTO `UbicacionLlave`/`RespuestaLlaves` en `cripta/modelo/datos.py`; actualizar los dobles de prueba que implementan la interfaz (FR-016, FR-017).
- [x] T004 [P] Implementar `GET /v1/criptas/<id>/llaves` en `cripta/adaptadores/cliente_http.py`, con el header existente y el conteo de presupuesto (FR-016, FR-019).
- [x] T005 [P] Implementar la lectura de `llaves.json` en `cripta/adaptadores/fuente_offline.py` para `--offline` (FR-015).
- [x] T006 [P] Guardar/leer `llaves.json` en `cripta/adaptadores/almacen_disco.py` dentro de la carpeta de la cripta, invalidado por la versión existente (FR-018, FR-021).
- [ ] T007 Ordenar la consulta en `cripta/controlador/controlador.py`: primero `datos_cripta` (fija presupuesto), después esqueleto y llaves; propagar error si se agota (FR-019, FR-020, SC-007).
- [x] T008 [P] Pruebas de contrato de `/llaves` en `tests/test_red.py`: campos, `enemigo`, 404, presupuesto agotado y versión (FR-016..FR-021).
- [ ] T009 [P] Implementar el generador determinista en `cripta/bench/sinteticos.py`: salas, costos, llaves encadenadas, puertas cambiantes y `llave_salida`; documentar la firma y el DTO de salida para A (FR-014, SC-005).
- [ ] T010 [P] Prueba del generador: dos corridas con la misma semilla producen la misma cripta y no usan estructuras prohibidas (FR-007, SC-002).
- [ ] T011 [P] Implementar el oráculo ingenuo en `tests/test_resolubilidad.py` (repetir recorrido por llave), solo para pruebas (SC-005, NFR-005).

**Checkpoint**: contrato, caché, presupuesto y generador listos.

---

## Phase 3: US1 — Verificar una cripta sin jugarla (P1) 🎯 MVP

**Goal**: `--verificar <cripta>` devuelve un veredicto sin abrir la vista.
**Independent Test**: verificar una cripta resoluble y una no resoluble y
comprobar salida y ausencia de vista/log.

### Pruebas (primero)

- [ ] T012 [P] [US1] Prueba de verificación de una cripta resoluble y una no resoluble en `tests/test_resolubilidad.py` (FR-001, FR-002, FR-003, FR-004, FR-005).
- [ ] T013 [P] [US1] Prueba de que `--verificar` no instancia la vista ni escribe `partida.log` en `tests/test_integracion.py` (FR-012, SC-006).

### Implementación

- [ ] T014 [US1] Crear `cripta/modelo/verificacion.py` con las entidades de `data-model.md` y las estructuras propias de `research.md` (FR-001, FR-005).
- [ ] T015 [US1] Implementar el recorrido incremental único y la retención/liberación de puertas por llave (FR-001, FR-002, FR-003, FR-004, FR-006, FR-007).
- [ ] T016 [US1] Implementar el veredicto con la condición estricta de `sala_salida` y el motivo (FR-005).
- [ ] T017 [US1] Añadir `--verificar <cripta>` en `cripta/controlador/aplicacion.py` con el flujo de `contracts/verificar-cli.md` y una preparación ligera (datos + esqueleto + llaves, sin contenido ni precarga) (FR-012, SC-007).
- [ ] T018 [US1] Formatear el reporte (`texto_resolubilidad`) en el controlador, sin vista (FR-012, FR-013).

**Checkpoint**: `--verificar` funciona de punta a punta sobre criptas sintéticas.

---

## Phase 4: US3 — Entender por qué no se puede ganar (P1)

**Goal**: reporte completo con frontera, llaves inobtenibles, ubicaciones y
ciclo concreto.
**Independent Test**: `AC-004-01` y una cripta con dos llaves encadenadas.

### Pruebas (primero)

- [ ] T019 [P] [US3] Prueba `AC-004-01`: llave de salida detrás de su propia puerta ⇒ no resoluble y ciclo concreto en `tests/test_resolubilidad.py` (FR-009).
- [ ] T020 [P] [US3] Prueba de frontera, llaves inobtenibles y ubicaciones (incluida `llave_salida` ausente y llave de puerta no listada) en `tests/test_resolubilidad.py` (FR-008, FR-022, FR-023).

### Implementación

- [ ] T021 [US3] Reportar frontera bloqueada sin duplicar puertas compartidas, con sala alcanzable, sala del otro lado, dirección y llave (FR-008, SC-003).
- [ ] T022 [US3] Reportar llaves inobtenibles con todas sus ubicaciones (sala y enemigo) (FR-008, FR-024, SC-003).
- [ ] T023 [US3] Detectar el ciclo concreto con dependencias llave→llave, recorrido por id y puerta representativa determinista (FR-009, SC-003).
- [ ] T024 [US3] Añadir el motivo explícito para `llave_salida` ausente y para la falta de puerta de salida con llave (FR-005, FR-023).

**Checkpoint**: el reporte explica cualquier bloqueo y cita el ciclo.

---

## Phase 5: US5 — Ubicación de llaves desde el servicio (P1)

**Goal**: interpretar correctamente `/llaves`, incluidas llaves de enemigos, y
respetar versión y presupuesto.
**Independent Test**: `AC-004-02` y cambio de versión.

### Pruebas (primero)

- [ ] T025 [P] [US5] Prueba `AC-004-02`: una llave en `suelta` de un errante se ubica en su sala inicial (FR-017).
- [ ] T026 [P] [US5] Prueba de invalidación por versión y de reutilización de `llaves.json` (FR-018, FR-021).
- [ ] T027 [P] [US5] Prueba de presupuesto: la consulta de llaves cuenta y el agotamiento da error explícito (FR-019, FR-020, SC-007).

### Implementación

- [ ] T028 [US5] Integrar la interpretación de `enemigo` y la sala inicial en el verificador (FR-017).
- [ ] T029 [US5] Unificar duplicados de una llave con criterio determinista de ubicación reportada (FR-024).

**Checkpoint**: las llaves del servicio se interpretan igual en línea y offline.

---

## Phase 6: US2 — No iniciar una partida imposible (P1)

**Goal**: bloquear el inicio sin `--forzar` y mantener el reporte disponible.
**Independent Test**: `AC-004-04` y la variante con `--forzar`.

### Pruebas (primero)

- [ ] T030 [P] [US2] Prueba `AC-004-04`: sin `--forzar` no se crea partida ni bitácora y se sale con código 3 (FR-010).
- [ ] T031 [P] [US2] Prueba de `--forzar`: la partida inicia y el reporte sigue disponible (FR-011).

### Implementación

- [ ] T032 [US2] Añadir `--forzar` en `cripta/controlador/aplicacion.py` y la verificación previa en `cripta/controlador/controlador.py`, antes de crear la partida y el replay (FR-010, FR-011).
- [ ] T033 [US2] Exponer `reporte_resolubilidad()`/`texto_resolubilidad()` para que la vista muestre el reporte al iniciar (FR-013).
- [ ] T034 [US2] Ajustar códigos de salida (0/1/2/3) según `contracts/verificar-cli.md` (FR-010).

**Checkpoint**: una cripta imposible no arranca salvo decisión explícita.

---

## Phase 7: US4 — Orden de llaves reproducible (P2)

**Goal**: orden válido y determinista, con desempate por id.
**Independent Test**: `AC-004-03` con dos ejecuciones.

### Pruebas (primero)

- [ ] T035 [P] [US4] Prueba `AC-004-03`: dos verificaciones producen el mismo orden (FR-007).
- [ ] T036 [P] [US4] Prueba de validez del orden: cada llave aparece después de las necesarias (FR-006).

### Implementación

- [ ] T037 [US4] Ordenar los ids de llaves por sala con `ordenamiento.ordenar` y liberar en orden de id (FR-006, FR-007).
- [ ] T038 [US4] Añadir la comprobación de determinismo al bench o a la prueba de integración (SC-002).

**Checkpoint**: el orden es reproducible y válido.

---

## Phase 8: Polish y mediciones

- [ ] T039 [P] Crear `cripta/bench/bench_resolubilidad.py`: incremental vs. ingenuo para K = 5..80 y 100..5000 salas, con semillas fijas y mediana/mínimo (SC-004, NFR-001, NFR-002, NFR-003, NFR-004).
- [ ] T040 [P] Registrar el bench en `cripta/bench/runner.py` y verificar los límites configurables.
- [ ] T041 Medir la cripta publicada más grande (300 salas): ≤ 200 ms o desviación documentada (SC-004, NFR-001, NFR-002).
- [ ] T042 [P] Añadir las pruebas que citan `AC-004-01..04` a la auditoría de trazabilidad (SC-001).
- [ ] T043 Actualizar `README.md` con `--verificar`, `--forzar`, el reporte y las mediciones (Parte II).
- [ ] T044 Ejecutar la suite completa y `--bench`; guardar la evidencia en `docs/mediciones/`.
- [ ] T045 Auditar estructuras prohibidas en `cripta/modelo/verificacion.py`, el generador y el bench (`dict`, `set`, `heapq`, `bisect`, `collections`, `networkx`) (constitución I).

**Checkpoint**: mediciones guardadas, límites verificados y documentación al día.

---

## Dependencia externa — Spec 001 de la Persona A

Estas tareas **no** se implementan hasta que la spec 001 de A esté confirmada
en Git (constitución VII y §3 de la Parte II). Los `FR-xxx` de A se coordinan
antes de empezar.

- [ ] T046 [P] [BLOQUEADA] Leer y exponer `DatosSalida.costo` en `cripta/modelo/datos.py`; persistirlo en `esqueleto.json` (FR de spec 001 de A, por coordinar).
- [ ] T047 [P] [BLOQUEADA] Leer `Ficha.rango` y transportar `comportamiento: "cazador"` en `cripta/modelo/datos.py` (FR de spec 001 de A, por coordinar).
- [ ] T048 [BLOQUEADA] Acordar con A la interfaz `Salida.costo`, `Enemigo.rango`, `Comportamiento.CAZADOR` y `mostrar_resolubilidad()` (`contracts/interfaz-a-b.md`).
- [ ] T049 [BLOQUEADA] Pruebas del contrato web (costo ausente = 100, `rango` ≥ 1, cazador) en `tests/test_red.py`.

---

## Dependencias entre tareas

```text
T003..T007  → base del contrato de llaves
T009..T011  → generador y oráculo para todas las pruebas
T012..T018  → US1 (verificador y CLI)
T019..T024  → US3 (reporte y ciclo) depende de US1
T025..T029  → US5 (llaves) depende de T003..T007
T030..T034  → US2 (bloqueo de partida) depende de US1 y US3
T035..T038  → US4 (orden) depende de US1
T039..T045  → mediciones y cierre
T046..T049  → bloqueadas por la spec 001 de A
```

## MVP

El mínimo entregable es **US1 + US5**: verificar con llaves del servicio,
imprimir el veredicto y no abrir la vista. US3 y US2 completan el valor
(reporte y bloqueo); US4 añade el orden determinista.
