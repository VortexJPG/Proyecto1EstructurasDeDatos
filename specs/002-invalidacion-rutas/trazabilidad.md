# Trazabilidad: Invalidación de rutas

Cada requisito de [`spec.md`](./spec.md) con su escenario, sus tareas de [`tasks.md`](./tasks.md), dónde está el código (dentro de `cripta/`) y las pruebas que lo citan (dentro de `tests/`). Las tareas y las pruebas se sacaron automáticamente de los archivos (cada prueba cita `002/FR-xxx` o `AC-002-xx` en su nombre o descripción); para correr una sola prueba: `python -m unittest tests.<archivo>.<Clase>.<prueba> -v`.

Escenarios: `USn-m` = historia de usuario n, escenario m de la spec; `AC-…` = caso del Apéndice B.

| Requisito | Escenario | Tareas | Código | Pruebas |
|---|---|---|---|---|
| FR-001 | AC-002-01, US1-2, US1-3 | T002, T004, T008 | `modelo/rutas.py` `RutasCazadores.decidir` | `test_invalidacion.test_002_sc002_todas_las_decisiones_iguales_al_oraculo`<br>`test_invalidacion.test_ac_002_01_puerta_de_la_ruta_se_cierra_entre_turnos` |
| FR-002 | US2 | T008, T011 | `modelo/rutas.py` `RutasCazadores.decidir` (caché) | `test_invalidacion.test_002_sc002_todas_las_decisiones_iguales_al_oraculo` |
| FR-003 | AC-002-01, US1-2 | T004, T005, T010, T011 | `modelo/rutas.py` `decidir` (sala objetivo) y `puerta_cambio` | `test_invalidacion.test_002_fr003_el_jugador_cambia_de_sala`<br>`test_invalidacion.test_ac_002_01_puerta_de_la_ruta_se_cierra_entre_turnos` |
| FR-004 | US2-3 | T006, T011 | `modelo/rutas.py` (la caché no depende de actores ni velocidades) | `test_invalidacion.test_002_fr004_reutiliza_entre_cazadores_y_turnos`<br>`test_invalidacion.test_ac_002_02_puerta_lejos_no_obliga_a_recalcular` |
| FR-005 | AC-002-02 | T006, T010, T011, T018 | `modelo/rutas.py` `puerta_cambio`, `BuscadorRutas.en_region`; `modelo/mapa.py` `Puerta.cerrada` | `test_bench_rutas.test_002_fr009_nfr003_puertas_inestables_lejos`<br>`test_invalidacion.test_ac_002_02_puerta_lejos_no_obliga_a_recalcular` |
| FR-006 | US1-3 | T007, T011, T013 | `modelo/mapa.py` `Puerta.cerrada` (propiedad); `modelo/juego.py` `desde_estado` | `test_invalidacion.test_002_fr006_pergamino_revierte_una_apertura` |
| FR-007 | AC-002-03 | T009, T013 | `modelo/rutas.py` (la caché no decide nada) | `test_invalidacion.test_ac_002_03_misma_partida_con_todas_las_estrategias` |
| FR-008 | AC-002-03 | T009, T012 | `modelo/rutas.py` `EstrategiaCazador` | `test_invalidacion.test_ac_002_03_misma_partida_con_todas_las_estrategias` |
| FR-009 | US3-2 | T003, T014, T018 | `bench/bench_rutas.py` `bench_invalidacion`, `bench_referencia_bot` | `test_bench_rutas.test_002_fr009_fr010_nfr002_puertas_estables`<br>`test_bench_rutas.test_002_fr009_nfr003_puertas_inestables_lejos` |
| FR-010 | US3-2 | T011, T014, T018 | `modelo/rutas.py` contadores `calculos`/`reutilizados`/`invalidaciones` | `test_bench_rutas.test_002_fr009_fr010_nfr002_puertas_estables` |
| FR-011 | Borde «sin cazadores» | T016 | `modelo/rutas.py` (caché perezosa: solo calcula si un cazador decide) | `test_invalidacion.test_002_fr011_sin_cazadores_no_hay_calculos` |
| NFR-001 | — | T017, T018 | `bench/bench_rutas.py` `bench_ciclo_referencia` | `test_bench_rutas.test_001_nfr001_002_nfr001_ciclo_en_la_referencia` |
| NFR-002 | US2-2 | T014, T018 | `bench/bench_rutas.py` `bench_invalidacion` | `test_bench_rutas.test_002_fr009_fr010_nfr002_puertas_estables` |
| NFR-003 | — | T014, T018 | `bench/bench_rutas.py` `bench_invalidacion` (semillas fijas) | `test_bench_rutas.test_002_fr009_nfr003_puertas_inestables_lejos` |

## Casos del Apéndice B

| Caso | Pruebas |
|---|---|
| AC-002-01 | `test_invalidacion.test_ac_002_01_puerta_de_la_ruta_se_cierra_entre_turnos` |
| AC-002-02 | `test_invalidacion.test_ac_002_02_puerta_lejos_no_obliga_a_recalcular` |
| AC-002-03 | `test_invalidacion.test_ac_002_03_misma_partida_con_todas_las_estrategias` |
