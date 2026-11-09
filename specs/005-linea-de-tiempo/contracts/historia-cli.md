# Contract: `historia` y `--hasta`

Contrato de la consulta histórica (`FR-004..FR-014`, `FR-022..FR-024`).

## Comandos en partida

```text
historia <t>     estado después de todos los eventos con tiempo ≤ t
historia #k      estado justo antes de la k-ésima acción vigente
```

- `<t>` es un entero ≥ 0.
- `<k>` es un entero ≥ 1.
- La consulta **no** consume reloj, **no** se escribe en `partida.log` y **no**
  altera la partida ni el historial de retroceso.

## Salida

```text
Historia en t=1200 (acción #4)
Sala: 7 — Pasillo de las urnas
Vida: 24/30   Ataque: 8   Defensa: 4   Velocidad: 100
Inventario: Daga oxidada, Poción menor, Pergamino de retroceso
Efectos: veneno (magnitud 2, hasta t=1280)
Enemigos en la sala:
  - Rata gigante #2: 7/12 (activo)
Mapa conocido:
  - salas: 1, 2, 3, 7
```

El formato exacto puede ajustarse en implementación, pero deben aparecer todos
los campos de `FR-005`.

## Rechazos

| Caso | Respuesta |
|---|---|
| `historia <t>` con t > reloj actual | error claro; no se muestra estado |
| `historia <t>` con t < 0 | error de uso |
| `historia #k` con k < 1 o k > acciones vigentes | error claro |
| Instante posterior a un recorte | error claro (la línea termina en el reloj actual) |

Un rechazo **no** termina la partida ni consume tiempo.

## Replay sin vista

```bash
python main.py --replay partida.log --hasta 1200 [--offline [DIR]]
```

- Reproduce las acciones del log hasta el instante t y avanza los eventos hasta
  t.
- Imprime el mismo resumen que `historia <t>`.
- No instancia la vista.
- Si t es posterior al final del log: muestra el estado final e indica
  `La partida terminó antes (victoria|derrota)`; código de salida 0.
- Si t es negativo: error de uso.

## Puntos de control

```bash
python main.py --cripta cripta-02 --checkpoint-cada 25
```

- K entero ≥ 1.
- Por defecto, el valor elegido en el plan con `--bench`.
- Cambiar K no altera la partida; solo la memoria y el tiempo de consulta.

## Garantías

- La reconstrucción usa como máximo K acciones (`FR-016`).
- No hace solicitudes al servicio (`FR-017` y constitución V).
- No toca los pines de la caché viva.
- Es determinista (`FR-031`).
