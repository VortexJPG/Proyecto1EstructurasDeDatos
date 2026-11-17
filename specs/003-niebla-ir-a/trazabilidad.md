# Trazabilidad: Niebla de guerra e «ir a»

Cada requisito de [`spec.md`](./spec.md) con su escenario, sus tareas de [`tasks.md`](./tasks.md), dónde está el código (dentro de `cripta/`) y las pruebas que lo citan (dentro de `tests/`). Las tareas y las pruebas se sacaron automáticamente de los archivos (cada prueba cita `003/FR-xxx` o `AC-003-xx` en su nombre o descripción); para correr una sola prueba: `python -m unittest tests.<archivo>.<Clase>.<prueba> -v`.

Escenarios: `USn-m` = historia de usuario n, escenario m de la spec; `AC-…` = caso del Apéndice B.

| Requisito | Escenario | Tareas | Código | Pruebas |
|---|---|---|---|---|
| FR-001 | US1-1 | T004, T010 | `modelo/conocimiento.py` `ConocimientoMapa` | `test_niebla.test_003_fr001_fr002_fr004_estado_inicial` |
| FR-002 | US1-1 | T004, T010, T012 | `modelo/juego.py` `iniciar` → `_revelar` | `test_niebla.test_003_fr001_fr002_fr004_estado_inicial` |
| FR-003 | US1 | T004, T010, T012 | `modelo/juego.py` `_entrar_a_sala` → `_revelar`; `ConocimientoMapa.explorar` | `test_niebla.test_003_fr003_entrar_explora` |
| FR-004 | US1-1 | T004, T010 | `modelo/conocimiento.py` `ConocimientoMapa.explorar` | `test_niebla.test_003_fr001_fr002_fr004_estado_inicial`<br>`test_niebla.test_003_fr003_entrar_explora` |
| FR-005 | US2-1 | T004, T010 | `modelo/conocimiento.py` `ConocimientoMapa.mapa_conocido` | `test_niebla.test_003_fr013_mapa_conocido_solo_lo_explorado` |
| FR-006 | US1-3 | T004, T010 | `vista/base.py` `destino_conocido` | `test_niebla.test_003_fr012_la_consola_no_muestra_salas_sin_explorar`<br>`test_niebla.test_003_fr013_mapa_conocido_solo_lo_explorado` |
| FR-007 | US1-2 | T005, T012 | `ConocimientoMapa.observar`; `modelo/juego.py` `_abrir`, `observar_si_presente`; `modelo/efectos.py` `cerrar_puerta` | `test_niebla.test_003_fr007_cambio_visto_estando_presente`<br>`test_niebla.test_003_fr007_fr008_memoria_de_puertas` |
| FR-008 | US1-2 | T005, T012 | `modelo/conocimiento.py` `recuerdo_puerta` | `test_niebla.test_003_fr007_fr008_memoria_de_puertas` |
| FR-009 | Clarify (antorcha) | T005 | `modelo/conocimiento.py` `SIN_OBSERVAR` | `test_niebla.test_003_fr007_fr008_memoria_de_puertas`<br>`test_niebla.test_003_fr009_puerta_de_vecina_por_antorcha_queda_sin_observar` |
| FR-010 | AC-003-04 | T006, T013 | `modelo/juego.py` `_revelar` | `test_niebla.test_ac_003_04_antorcha_explora_vecinas_sin_activar` |
| FR-011 | AC-003-04 | T006, T013 | `modelo/juego.py` `_revelar` (no llama a `_activar_enemigos`) | `test_niebla.test_ac_003_04_antorcha_explora_vecinas_sin_activar` |
| FR-012 | US1-3, US2-2 | T014, T015 | `vista/base.py` `destino_conocido`, `lineas_mapa_conocido` | `test_niebla.test_003_fr012_la_consola_no_muestra_salas_sin_explorar`<br>`test_niebla.test_003_fr013_mapa_conocido_solo_lo_explorado` |
| FR-013 | US2-1 | T014, T015, T016 | `modelo/juego.py` `mapa_conocido`; `vista/vista_consola.py` `mostrar_mapa`; `vista/vista_grafica.py` `_dibujar_mapa` | `test_niebla.test_003_comandos_mapa_e_ir_a_en_la_consola`<br>`test_niebla.test_003_fr013_mapa_conocido_solo_lo_explorado` |
| FR-014 | US5-2 | T007, T017 | `modelo/juego.py` `exportar_estado`/`desde_estado`; `adaptadores/guardado.py` | `test_niebla.test_003_fr014_guardar_y_cargar_conserva_el_conocimiento` |
| FR-015 | AC-003-05 | T006, T011 | `modelo/historial.py` `CambioCasilla`; `modelo/juego.py` `_asignar_casilla` | `test_niebla.test_ac_003_05_pergamino_revierte_la_antorcha` |
| FR-016 | US5-3 | T007, T018 | `modelo/timeline.py` `LineaTiempo.resumen` | `test_niebla.test_003_fr016_historia_muestra_el_mapa_conocido_de_ese_momento` |
| FR-017 | US3 | T008, T020 | `controlador/controlador.py` `Controlador.ir_a` | `test_niebla.test_003_fr022_llega_al_destino` |
| FR-018 | AC-003-01 | T008, T020 | `modelo/juego.py` `validar_ir_a`; `Controlador.ir_a` | `test_niebla.test_ac_003_01_destino_no_explorado_se_rechaza_sin_tiempo` |
| FR-019 | US3 | T008, T019 | `modelo/juego.py` `paso_hacia`; `ConocimientoMapa.transitable_conocida` | `test_niebla.test_003_fr019_ruta_mas_barata_conocida_y_desempate` |
| FR-020 | US3 | T008, T020 | `Controlador.ir_a` (cada paso es `ejecutar_accion(MOVER)`) | `test_niebla.test_003_fr022_llega_al_destino` |
| FR-021 | AC-003-02 | T008, T019 | `Controlador.ir_a` (recalcula antes de cada paso) | `test_niebla.test_ac_003_02_puerta_recordada_abierta_pero_cerrada`<br>`test_niebla.test_ac_003_02_recalcula_y_usa_otra_ruta` |
| FR-022 | AC-003-02, AC-003-03, US3-4 | T008, T020 | `Controlador.ir_a` (condiciones de parada) | `test_niebla.test_003_fr022_llega_al_destino`<br>`test_niebla.test_003_fr022_recibe_dano_y_se_detiene`<br>`test_niebla.test_ac_003_02_puerta_recordada_abierta_pero_cerrada`<br>`test_niebla.test_ac_003_03_entra_a_sala_con_enemigos_dormidos` |
| FR-023 | US3-5 | T008, T019 | `ConocimientoMapa.transitable_conocida` (solo puertas recordadas abiertas) | `test_niebla.test_003_fr023_no_abre_puertas` |
| FR-024 | US3-6 | T009, T021 | `adaptadores/bitacora_replay.py` `EscritorReplay.comentario`, `LectorReplay.acciones` | `test_niebla.test_003_fr024_log_con_pasos_y_comentario_y_replay_fiel` |
| FR-025 | AC-003-06 | T008 | `modelo/juego.py` `usar_pergamino` (cada paso es una acción) | `test_niebla.test_ac_003_06_pergamino_revierte_solo_el_ultimo_paso` |
| FR-026 | US3-4 | T008, T016, T020 | `controlador/controlador.py` `ResultadoViaje`; `vista/base.py` `texto_viaje`, `mostrar_viaje` | `test_niebla.test_003_comandos_mapa_e_ir_a_en_la_consola` |
| FR-027 | US3-6 | T009 | `Controlador.ir_a` | `test_niebla.test_003_fr024_log_con_pasos_y_comentario_y_replay_fiel` |
| NFR-001 | — | T023, T024 | `bench/bench_rutas.py` `bench_ir_a_referencia` | `test_bench_rutas.test_003_nfr001_paso_de_ir_a_en_la_referencia` |
| NFR-002 | — | T010, T022, T024 | `modelo/conocimiento.py` (arreglos); `bench_consulta_conocimiento` | `test_bench_rutas.test_003_nfr002_consulta_constante` |
| NFR-003 | — | T010, T022, T024 | `ConocimientoMapa.explorar`; `bench_explorar` | `test_bench_rutas.test_003_nfr003_explorar_cuesta_lo_revelado` |
| NFR-004 | — | T011, T022, T024 | `CambioCasilla`; `bench_revertir_antorcha` | `test_bench_rutas.test_003_nfr004_revertir_cuesta_lo_cambiado` |
| NFR-005 | — | T022, T024 | `bench/bench_rutas.py` `registrar` | `test_bench_rutas.test_001_fr021_bench_registra_los_casos_de_6_3` |

## Casos del Apéndice B

| Caso | Pruebas |
|---|---|
| AC-003-01 | `test_niebla.test_ac_003_01_destino_no_explorado_se_rechaza_sin_tiempo` |
| AC-003-02 | `test_niebla.test_ac_003_02_puerta_recordada_abierta_pero_cerrada`<br>`test_niebla.test_ac_003_02_recalcula_y_usa_otra_ruta` |
| AC-003-03 | `test_niebla.test_ac_003_03_entra_a_sala_con_enemigos_dormidos` |
| AC-003-04 | `test_niebla.test_ac_003_04_antorcha_explora_vecinas_sin_activar` |
| AC-003-05 | `test_niebla.test_ac_003_05_pergamino_revierte_la_antorcha` |
| AC-003-06 | `test_niebla.test_ac_003_06_pergamino_revierte_solo_el_ultimo_paso` |
