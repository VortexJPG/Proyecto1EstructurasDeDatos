# Data Model: Terreno y cazador

## Salida (modelo/mapa.py)

| Campo | Tipo | Regla |
|---|---|---|
| `direccion` | `str` | N, S, E u O |
| `origen` | `Sala` | sala dueña de la salida (nuevo: para recorrer en sentido inverso) |
| `destino` | `Sala` | |
| `puerta` | `Puerta \| None` | compartida por los dos sentidos del pasaje |
| `costo` | `int` | ≥ 1; 100 si no se declara; igual en los dos sentidos (FR-001, FR-002) |

Validación: `costo` declarado que no sea entero ≥ 1 ⇒ `ValueError` con la sala
y la dirección (FR-003).

## Sala (modelo/mapa.py)

| Campo nuevo | Tipo | Regla |
|---|---|---|
| `indice` | `int` | posición en el esqueleto (0..V-1); índice de los arreglos de rutas y de conocimiento |
| `entradas` | `list[Salida]` | salidas de otras salas que llegan a esta, en orden del esqueleto y N, S, E, O |

## Puerta (modelo/mapa.py)

| Campo nuevo | Tipo | Regla |
|---|---|---|
| `indice` | `int` | posición de creación (0..P-1) |
| `salas` | `(Sala, Sala)` | las dos salas que conecta (para la invalidación, spec 002) |
| `cerrada` | propiedad | al cambiar avisa al mapa (spec 002) |

## Enemigo (modelo/actores.py)

| Campo nuevo | Tipo | Regla |
|---|---|---|
| `comportamiento` | `Comportamiento` | se agrega `CAZADOR` ("cazador") |
| `rango` | `int` | solo cazadores; ≥ 1; falta o < 1 ⇒ `ValueError` (FR-008) |

## BuscadorRutas (modelo/rutas.py)

Estado interno, reutilizado entre búsquedas:

| Campo | Tipo | Uso |
|---|---|---|
| `_dist` | `list[int]` (V) | distancia tentativa o final |
| `_marca` | `list[int]` (V) | generación en que `_dist[i]` es válida |
| `_final` | `list[int]` (V) | generación en que la sala quedó finalizada |
| `_generacion` | `int` | se incrementa en cada búsqueda |
| `_monticulo` | `MonticuloMin[int]` | claves `dist·V + índice` |
| `salas_examinadas` | `int` | contador para `--bench` |

Operaciones:

- `calcular(objetivo, alcance, transitable, parar_en=None)`: distancias hacia
  `objetivo` por las salidas que cumplen `transitable`, hasta `alcance`.
- `distancia(sala) -> int | None`: solo si quedó finalizada en esta búsqueda.
- `primer_paso(origen, transitable) -> Salida | None`: regla de desempate R4.

## Invariantes

- Las distancias finalizadas son exactas (costos ≥ 1, Dijkstra).
- `primer_paso` solo mira vecinas finalizadas.
- Ninguna operación consume el azar del juego ni modifica el estado de juego.
