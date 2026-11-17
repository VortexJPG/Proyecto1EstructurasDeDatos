# Data Model: Niebla de guerra e «ir a»

## ConocimientoMapa (modelo/conocimiento.py)

| Campo | Tipo | Regla |
|---|---|---|
| `estado_sala` | `list[int]` (V) | 0 desconocida, 1 avistada, 2 explorada; índice `Sala.indice` |
| `recuerdo_puerta` | `list[int]` (P) | 0 sin observar, 1 abierta, 2 cerrada; índice `Puerta.indice` |

Operaciones (todas reciben la función `asignar(arreglo, índice, valor)` del
juego, que registra el cambio para el retroceso):

| Operación | Costo | Efecto |
|---|---|---|
| `estado(sala)` | O(1) | |
| `explorada(sala)` | O(1) | |
| `recuerdo(puerta)` | O(1) | |
| `salida_conocida_abierta(salida)` | O(1) | sin puerta ⇒ True; si no, recuerdo == abierta |
| `explorar(sala, asignar)` | O(grado) | sala → 2; destinos en 0 → 1 |
| `observar(puerta, asignar)` | O(1) | recuerdo ← estado real |
| `serializar()` / `restaurar(texto)` | O(V + P) | texto `dígitos-salas|dígitos-puertas` |
| `mapa_conocido(mapa)` | O(V + salidas exploradas) | `MapaConocido` para la vista y `historia` |

## MapaConocido / SalaConocida / SalidaConocida

Vista neutra (sin referencias a objetos vivos) del conocimiento:

```text
MapaConocido
  exploradas: list[SalaConocida]      # orden del esqueleto
  avistadas: int
SalaConocida
  id, nombre, actual: bool
  salidas: list[SalidaConocida]       # orden N, S, E, O
SalidaConocida
  direccion, costo
  puerta: "sin puerta" | "abierta" | "cerrada" | "sin observar"
  destino_id: int | None              # solo si el destino está explorado
  destino_nombre: str | None
```

## CambioCasilla (modelo/historial.py)

`(arreglo, índice, valor_anterior)`; `revertir` hace `arreglo[índice] =
valor_anterior`.

## EstadoGuardable.conocimiento (modelo/guardable.py) [CONTRATO A↔B]

Texto `"<V dígitos>|<P dígitos>"`. Vacío en archivos que no lo traen (solo se
reconstruye "explorada" a partir de `visitada` para no perder lo esencial).

## ResultadoViaje (controlador/controlador.py)

| Campo | Tipo |
|---|---|
| `aceptado` | `bool` (False si se rechazó sin consumir tiempo) |
| `pasos` | `int` |
| `motivo` | `str` (llegada, enemigos, daño, sin ruta, partida terminada, rechazo) |
| `destino` | `int` |

## Validaciones

- `ir a` con un argumento que no es un id de sala existente, o con una sala no
  explorada ⇒ rechazo sin tiempo (FR-018).
- `ir a` hacia la sala actual ⇒ aviso sin tiempo (FR-018).
