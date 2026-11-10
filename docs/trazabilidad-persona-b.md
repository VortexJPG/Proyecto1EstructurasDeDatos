# Trazabilidad — Persona B (Parte II)

Auditoría de requisitos → tareas → código → prueba, para la defensa y para la
lista de verificación de §8. Se actualiza al cerrar cada fase.

## Spec 004 — Resolubilidad y llaves

| Requisitos | Código | Prueba / evidencia |
|---|---|---|
| FR-001..FR-005 | `cripta/modelo/verificacion.py` | `tests/test_resolubilidad.py::PruebaVerificador` |
| FR-006, FR-007 | orden por sala/id | `test_resoluble`, `test_ac_004_03_dos_corridas_mismo_orden`, `test_validez_del_orden` |
| FR-008, FR-009 | frontera, inobtenibles y ciclo | `test_no_resoluble_con_ciclo`, `test_frontera_sin_duplicar_puerta_compartida` |
| FR-010, FR-011 | gate de inicio y `--forzar` | `tests/test_integracion.py::PruebaBloqueoInicio` |
| FR-012, FR-013 | `--verificar` y reporte | `PruebaCliVerificar`, `Controlador.texto_resolubilidad` |
| FR-014 | sin datos de cripta | `tests/test_sinteticos.py` + revisión de código |
| FR-015..FR-019 | llaves, offline, versión y presupuesto | `tests/test_red.py::PruebaClienteHTTP`, `PruebaFuenteOffline`, `PruebaAlmacenLlaves` |
| FR-020 | error por presupuesto | `test_llaves_presupuesto_agotado` |
| FR-021..FR-024 | persistencia, duplicados y casos ambiguos | `test_llave_duplicada`, `test_puerta_exige_llave_no_listada`, `test_llave_salida_ausente` |
| NFR-001..NFR-005 | `--bench resolubilidad` | `docs/mediciones/p2_resolubilidad.txt`, `test_coincide_con_el_oraculo` |
| AC-004-01 | ciclo | `test_no_resoluble_con_ciclo` |
| AC-004-02 | llave de enemigo | `test_llave_de_enemigo` |
| AC-004-03 | dos corridas | `test_ac_004_03_dos_corridas_mismo_orden` |
| AC-004-04 | sin `--forzar` no inicia | `PruebaBloqueoInicio.test_sin_forzar_no_inicia_ni_crea_replay` |

## Spec 005 — Línea de tiempo e historia

| Requisitos | Código | Prueba / evidencia |
|---|---|---|
| FR-001..FR-008 | `cripta/modelo/timeline.py`, `Controlador.consultar_historia` | `tests/test_timeline.py::PruebaLineaBase`, `PruebaComandoHistoria` |
| FR-009, FR-010 | validación de rangos | `test_rechazos`, `test_historia_en_cero` |
| FR-011..FR-014 | recorte y renumeración | `test_recorte_por_pergamino` |
| FR-015..FR-021 | checkpoints, K y memoria | `test_checkpoints_cada_k_y_acciones`, `--bench timeline` |
| FR-022..FR-024 | `--hasta` y fin anticipado | `tests/test_timeline.py::PruebaReplayHasta` |
| FR-025..FR-029 | formato v3 y P1 | `PruebaPersistenciaLinea` |
| FR-030 | conocimiento del mapa | doble: salas visitadas; **integración con A pendiente** (T053) |
| FR-031, FR-032 | determinismo y eventos intermedios | `test_reconstruccion_coincide_con_el_oraculo` |
| NFR-001 | 50 ms con 5000 acciones | `docs/mediciones/p2_timeline.txt`: K=50 → 0.81 ms |
| NFR-002..NFR-004 | memoria y varios K | tabla de memoria del mismo archivo |
| NFR-005 | oráculo | `test_reconstruccion_coincide_con_el_oraculo` |
| AC-005-01 | t futuro se rechaza | `test_rechazos` |
| AC-005-02 | acciones revertidas | `test_recorte_por_pergamino` |
| AC-005-03 | varios eventos en el mismo instante | **PENDIENTE**: instantes entre decisiones requieren `Juego.avanzar_hasta` (A, T016/T030-T032) |
| AC-005-04 | no altera nada | `test_consulta_no_altera_nada` |
| AC-005-05 | `--hasta` posterior al final | `test_hasta_despues_del_final` |
| AC-005-06 | archivo de P1 | `test_p1_binario_se_rechaza`, `test_p1_json_se_rechaza` |
| SC-001..SC-007 | resumen y evidencia | pruebas citadas + `docs/mediciones/p2_timeline.txt` |
| §5.5 y §5.6-B | `Decisiones_de_diseño.md` | secciones 5.5 y 5.6 |

## Pendiente de la Persona B (y por qué)

| Ítem | Estado | Dependencia |
|---|---|---|
| `T048` spec 004: acordar la interfaz de `costo`/`rango`/`cazador` | Pendiente | Coordinación con A |
| `T016`, `T030..T032`: instantes entre decisiones | Pendiente | `Juego.avanzar_hasta` de A |
| `T053`, `T054`, `T056`: conocimiento del mapa y caso pergamino/antorcha | Pendiente | Interfaz de conocimiento de A |
| Defensa: recorrido de 2 requisitos y cambio de regla | Hecho | `docs/defensa-persona-b.md` |
| §5.4, §5.5 y §5.6-B | Hecho | `Decisiones_de_diseño.md` |
| `historia` en consola y ventana | Hecho | `T055`; tecla `V` |

## Verificación rápida

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python main.py --bench resolubilidad
.venv/bin/python main.py --bench timeline
.venv/bin/python main.py --verificar cripta-05
.venv/bin/python main.py --offline --replay docs/mediciones/p1_partida_cripta-02_semilla3.log --hasta 0
```
