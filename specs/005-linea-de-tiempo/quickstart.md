# Quickstart: validar la línea de tiempo

Guía de validación de la capacidad. Los comandos describen el comportamiento
**esperado tras la implementación**; hoy `historia`, `--hasta` y
`--checkpoint-cada` todavía no existen.

## Requisitos

```bash
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

- Paquete offline actualizado (con `llaves.json`) o conexión al servicio.
- Partidas sintéticas deterministas para las pruebas de mismo instante y K.

## 1. Pruebas automatizadas

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Esperado: suite en verde, incluida `tests/test_timeline.py` con
`AC-005-01..06`.

## 2. Consulta en partida

```bash
.venv/bin/python main.py --offline --cripta cripta-02 --nombre Prueba
```

Dentro de la partida:

```text
> historia 0
> historia 200
> historia #3
```

Esperado:

- `historia 0` muestra el estado inicial (sala inicial, reloj 0).
- `historia 200` muestra el estado después de todos los eventos con tiempo ≤ 200.
- `historia #3` muestra el estado justo antes de la tercera acción.
- Después de cada consulta, el reloj y la partida siguen igual.

## 3. Rechazo de instantes futuros

```text
> historia 999999
```

Esperado: mensaje de rechazo; no se muestra estado ni se consume tiempo.
`AC-005-01`.

## 4. Recorte por pergamino

1. Realizar 3 acciones.
2. Usar un pergamino (`Z` en la ventana o `retroceder` en la terminal).
3. Consultar `historia 0` y `historia #1`.

Esperado: las acciones revertidas no aparecen; la numeración empieza de nuevo.
`AC-005-02`.

## 5. Varios eventos en el mismo instante

```bash
.venv/bin/python -m unittest tests.test_timeline -v
```

Esperado: la consulta en t muestra el estado después de **todos** los eventos
de ese instante. `AC-005-03`.

## 6. La consulta no altera nada

Antes y después de `historia`, comparar:

- reloj del jugador,
- líneas de `partida.log`,
- historial de retroceso (`puede_retroceder`, cambios del último intervalo).

Esperado: idénticos. `AC-005-04`.

## 7. Replay sin vista

```bash
.venv/bin/python main.py --offline --replay partida.log --hasta 1200
```

Esperado: mismo resumen que `historia 1200`, sin abrir la vista. Si 1200 es
posterior al final:

```text
La partida terminó antes (victoria|derrota).
```

`AC-005-05`.

## 8. Guardar, cargar y archivo de P1

```bash
# dentro de la partida
> guardar
> cargar
> historia 300
```

Esperado: la línea se conserva y `historia 300` sigue funcionando.

Con un `.sav` de la Parte I:

```text
ErrorFormatoIncompatible: versión de formato 2, se esperaba 3.
```

Nunca se carga en silencio. `AC-005-06`.

## 9. Puntos de control y rendimiento

```bash
.venv/bin/python main.py --bench timeline
```

Esperado:

- consultas con K ∈ {10, 25, 50, 100} y sin checkpoints;
- tiempo ≤ 50 ms con 5000 acciones y el K por defecto;
- memoria ∝ acciones + checkpoints/K;
- el K por defecto queda justificado con la tabla.

Variables: `CRIPTA_TIMELINE_K`, `CRIPTA_TIMELINE_ACCIONES`,
`CRIPTA_TIMELINE_REPS`, `CRIPTA_LIMITE_HISTORIA_MS`.

## 10. Oráculo

```bash
.venv/bin/python -m unittest tests.test_timeline -v
```

Esperado: para muchos t y K, el estado reconstruido es idéntico al
re-simulado desde cero (`SC-003`).
