# Tasks: Fin de partida y cripta no resoluble en la interfaz

**Input**: [`spec.md`](./spec.md), [`plan.md`](./plan.md). Las pruebas citan
`006/FR-xxx` o `AC-006-xx`.

- [x] T001 Confirmar la spec 006 en Git antes del código (constitución VII).
- [x] T002 `Controlador.ejecutar_interactivo` repite la partida si la vista pide reintentar al ganar o morir; `reiniciar_partida` y `_montar_precarga` en `cripta/controlador/controlador.py` (FR-001..FR-006, FR-012).
- [x] T003 Prueba: reintentar juega otra partida en la misma cripta desde cero; salir termina, en `tests/test_reintentar.py` (AC-006-01, AC-006-02, FR-002, FR-004, FR-005).
- [x] T004 Botones «Reintentar» (izquierda) y «Salir» (derecha) en la pantalla final de `cripta/vista/vista_grafica.py`, con teclado y ratón, y prueba en `tests/test_reintentar.py` (FR-007, AC-006-03, AC-006-04).
- [x] T005 Pregunta `[R] Reintentar  [S] Salir` en `cripta/vista/vista_consola.py`, con prueba (FR-008).
- [x] T006 Volver a la lista con una cripta no resoluble elegida de la lista y pedir la lista una sola vez; `mostrar_no_resoluble` en `cripta/vista/base.py` y pantalla del reporte en la ventana (FR-009, FR-011, FR-012).
- [x] T007 Pruebas: ventana y terminal muestran el reporte y dejan elegir otra cripta; con `--cripta` se sale con código 3, en `tests/test_vista_grafica.py` y `tests/test_interfaz_a_b.py` (AC-006-05, AC-006-06, FR-009, FR-010).
