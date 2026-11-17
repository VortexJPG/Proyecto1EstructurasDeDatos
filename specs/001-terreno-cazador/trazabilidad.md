# Trazabilidad: Terreno y cazador

Cada requisito de [`spec.md`](./spec.md) con su escenario, sus tareas de [`tasks.md`](./tasks.md), dónde está el código (dentro de `cripta/`) y las pruebas que lo citan (dentro de `tests/`). Las tareas y las pruebas se sacaron automáticamente de los archivos (cada prueba cita `001/FR-xxx` o `AC-001-xx` en su nombre o descripción); para correr una sola prueba: `python -m unittest tests.<archivo>.<Clase>.<prueba> -v`.

Escenarios: `USn-m` = historia de usuario n, escenario m de la spec; `AC-…` = caso del Apéndice B.

| Requisito | Escenario | Tareas | Código | Pruebas |
|---|---|---|---|---|
| FR-001 | US1-2 | T004, T010 | `modelo/mapa.py` `Mapa.construir` (paso 4) y `Salida.costo` | `test_terreno_cazador.test_001_fr001_costo_por_defecto_100` |
| FR-002 | US1-2, borde «costos distintos» | T004, T010 | `modelo/mapa.py` `Mapa.construir` (paso 4), `Mapa._indice_regreso_costo` | `test_terreno_cazador.test_001_fr002_costo_compartido_por_pasaje`<br>`test_terreno_cazador.test_001_fr002_costos_distintos_gana_el_primero_del_esqueleto`<br>`test_terreno_cazador.test_001_fr002_puerta_y_costo_en_lados_distintos` |
| FR-003 | Borde «costo inválido» | T005, T010 | `modelo/mapa.py` `_validar_costo` | `test_terreno_cazador.test_001_fr003_costo_invalido_es_error` |
| FR-004 | US1-1, AC-001-05 | T006, T011, T013 | `modelo/juego.py` `Juego._mover`, `Juego.calcular_intervalo` | `test_terreno_cazador.test_001_fr004_jugador_cruza_salida_de_costo_250`<br>`test_terreno_cazador.test_ac_001_05_velocidad_alta_y_costo_1_da_intervalo_1` |
| FR-005 | US1-5 | T006, T012 | `modelo/comportamiento.py` `_actuar_errante`, `_actuar_rastreador` | `test_terreno_cazador.test_001_fr005_errante_tarda_el_costo_de_la_salida`<br>`test_terreno_cazador.test_001_fr005_rastreador_tarda_el_costo_de_la_salida` |
| FR-006 | US1 (clarify) | T006 | `constantes.py` `COSTO_ESPERAR`/`COSTO_ATACAR`; `modelo/juego.py` `_esperar` | `test_terreno_cazador.test_001_fr006_otras_acciones_no_cambian` |
| FR-007 | AC-001-06 | T013 | `modelo/efectos.py` `GestorEfectos.reajustar_turno` | `test_terreno_cazador.test_ac_001_06_cambio_de_velocidad_escala_el_restante` |
| FR-008 | Borde «cazador sin rango» | T007, T014 | `modelo/actores.py` `Comportamiento.CAZADOR`, `Enemigo.__init__` | `test_terreno_cazador.test_001_fr008_cazador_con_rango`<br>`test_terreno_cazador.test_001_fr008_cazador_sin_rango_es_ficha_invalida` |
| FR-009 | US2-4 | T008, T017 | `modelo/comportamiento.py` `IAEnemigos.actuar` | `test_terreno_cazador.test_001_fr009_ataca_si_comparte_sala` |
| FR-010 | AC-001-03, US2-6 | T008, T015, T017 | `modelo/rutas.py` `BuscadorRutas.calcular` | `test_terreno_cazador.test_ac_001_03_menos_salas_pero_mas_caro` |
| FR-011 | AC-001-01, AC-001-02 | T008, T017 | `modelo/rutas.py` `RutasCazadores.decidir` | `test_terreno_cazador.test_ac_001_01_sin_ruta_abierta_espera_100`<br>`test_terreno_cazador.test_ac_001_02_ruta_mas_cara_que_el_rango_espera` |
| FR-012 | US2-5 | T008, T016, T017 | `modelo/rutas.py` `BuscadorRutas.primer_paso`; `modelo/comportamiento.py` `_actuar_cazador` | `test_terreno_cazador.test_001_fr012_ruta_igual_al_rango_se_mueve`<br>`test_terreno_cazador.test_001_fr012_un_paso_con_el_costo_de_la_salida` |
| FR-013 | AC-001-04, US3-2 | T009, T016, T018 | `modelo/rutas.py` `BuscadorRutas.primer_paso` | `test_terreno_cazador.test_001_fr013_misma_vecina_por_dos_salidas`<br>`test_terreno_cazador.test_001_sc002_decisiones_iguales_al_oraculo`<br>`test_terreno_cazador.test_ac_001_04_empate_va_a_la_vecina_de_menor_id` |
| FR-014 | US2-6 | T019 | `modelo/rutas.py` `salida_abierta` (no mira el conocimiento ni el contenido) | `test_terreno_cazador.test_001_fr014_no_depende_del_contenido_ni_de_la_niebla` |
| FR-015 | US3-2 (SC-002) | T003, T018, T021 | `modelo/rutas.py` `RutasCazadores` (detalle en la spec 002) | `test_terreno_cazador.test_001_sc002_decisiones_iguales_al_oraculo` |
| FR-016 | Borde «cazador dormido» | T020 | `modelo/juego.py` `_activar_enemigos` (solo los activos tienen turno) | `test_terreno_cazador.test_001_fr016_cazador_dormido_no_actua` |
| FR-017 | US3-2 | T020 | `modelo/rutas.py` (la decisión no usa `juego.azar`) | `test_terreno_cazador.test_001_fr017_la_decision_no_consume_el_azar` |
| FR-018 | Supuestos | T029 | todo `cripta/`; `bench/bench_rutas.py` `id_referencia` | `test_terreno_cazador.test_001_fr018_el_codigo_no_tiene_datos_de_criptas_concretas` |
| FR-019 | US5-1 | T022, T023 | `vista/vista_consola.py` `mostrar_estado`; `vista/vista_grafica.py` `_dibujar_salidas` | `test_niebla.test_003_fr012_la_consola_no_muestra_salas_sin_explorar`<br>`test_terreno_cazador.test_001_fr019_fr020_consola_muestra_costos_y_marca_cazadores` |
| FR-020 | US5-2 | T022, T023 | `vista/base.py` `etiqueta_enemigo`, `es_cazador` | `test_terreno_cazador.test_001_fr019_fr020_consola_muestra_costos_y_marca_cazadores` |
| FR-021 | US4 | T025, T030 | `bench/bench_rutas.py` `registrar`, `bench_decisiones`, `bench_busqueda` | `test_bench_rutas.test_001_fr021_bench_registra_los_casos_de_6_3` |
| NFR-001 | US4-1 | T027, T030 | `bench/bench_rutas.py` `bench_ciclo_referencia`, `revisar_limites` | `test_bench_rutas.test_001_nfr001_002_nfr001_ciclo_en_la_referencia` |
| NFR-002 | US4-2 | T015, T026, T030 | `modelo/rutas.py` (marcas de generación); `bench_decisiones` con rango 300 | `test_bench_rutas.test_001_nfr002_rango_pequeno_no_depende_del_tamano` |
| NFR-003 | US4 | T025, T028, T030 | `bench/bench_rutas.py` `bench_decisiones` (compartida vs. individual) | `test_bench_rutas.test_001_nfr003_compartido_contra_individual` |
| NFR-004 | — | T024, T030 | `bench/runner.py` `estadisticas`, `muestras` | `test_bench_rutas.test_001_nfr004_mediciones_deterministas_y_estadisticas` |

## Casos del Apéndice B

| Caso | Pruebas |
|---|---|
| AC-001-01 | `test_terreno_cazador.test_ac_001_01_sin_ruta_abierta_espera_100` |
| AC-001-02 | `test_terreno_cazador.test_ac_001_02_ruta_mas_cara_que_el_rango_espera` |
| AC-001-03 | `test_terreno_cazador.test_ac_001_03_menos_salas_pero_mas_caro` |
| AC-001-04 | `test_terreno_cazador.test_ac_001_04_empate_va_a_la_vecina_de_menor_id` |
| AC-001-05 | `test_terreno_cazador.test_ac_001_05_velocidad_alta_y_costo_1_da_intervalo_1` |
| AC-001-06 | `test_terreno_cazador.test_ac_001_06_cambio_de_velocidad_escala_el_restante` |
