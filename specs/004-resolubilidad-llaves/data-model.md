# Data Model: Resolubilidad y llaves

Entidades del dominio y del verificador, con sus validaciones. Los nombres de
estructuras concretas están en `research.md`; aquí se describe **qué datos** se
manejan.

## 1. Entidades del servicio

### UbicacionLlave

Representa un lugar donde se puede obtener una llave (`FR-016`, `FR-017`).

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `id` | texto | sí | id de tipo de la llave |
| `sala` | entero | sí | sala donde se obtiene |
| `enemigo` | texto o nulo | no | si existe, la llave está en el campo `suelta` de esa instancia y `sala` es la sala **inicial** del enemigo |

**Validaciones**

- `sala` debe existir en el esqueleto.
- Si `enemigo` existe, debe existir una instancia con ese id en la sala
  indicada; si no, la ubicación es inválida y se reporta.
- El mismo `id` puede aparecer en varias ubicaciones (`FR-024`).

### RespuestaLlaves

| Campo | Tipo | Regla |
|---|---|---|
| `version_cripta` | texto | versión con la que se obtuvo; debe coincidir con la vigente |
| `llaves` | lista de `UbicacionLlave` | una o más entradas |

**Persistencia**: `llaves.json` dentro de la carpeta de la cripta, junto a
`version.txt`. La validación de versión existente borra el archivo cuando la
versión cambia (`FR-018`, `FR-021`).

## 2. Entidades del verificador

### CriptaVerificable

Vista mínima de una cripta para verificar, sin contenido de salas ni partida en
curso.

| Campo | Tipo | Regla |
|---|---|---|
| `datos` | `DatosCripta` | sala inicial, sala de salida, `llave_salida`, versión |
| `salas` | esqueleto completo | todas las salas y salidas |
| `llaves` | `RespuestaLlaves` | ubicaciones consultadas o cacheadas |

### PuertaRetenida

Una puerta cerrada encontrada durante la expansión, pendiente de su llave.

| Campo | Tipo | Regla |
|---|---|---|
| `puerta_id` | texto | única por puerta, aunque conecte dos salas |
| `llave_id` | texto | llave que la abre |
| `desde_sala` | entero | sala alcanzable desde la que se encontró |
| `hacia_sala` | entero | sala del otro lado |
| `direccion` | texto | N, S, E u O, para el reporte |

**Invariante**: una puerta compartida se retiene **una sola vez**; al liberarla
se encola `hacia_sala` si no estaba visitada.

### RegionAlcanzable

| Campo | Tipo | Regla |
|---|---|---|
| `visitadas` | marca por id de sala | cada sala se marca una vez |
| `cola` | FIFO de salas | orden determinista de expansión |
| `llaves_obtenidas` | marca por id de llave | solo crece; las llaves no se consumen |
| `retenidas` | puertas por llave | solo puertas cerradas de llaves no obtenidas |

**Invariantes**

- Toda sala marcada es alcanzable desde la sala inicial con las llaves
  obtenidas hasta ese momento.
- Una llave solo se marca obtenida si alguna de sus ubicaciones es una sala
  visitada (`FR-003`, `FR-017`).
- Una puerta retenida solo se libera cuando su llave se obtiene.

### LlaveInobtenible

| Campo | Tipo | Regla |
|---|---|---|
| `id` | texto | llave sin ubicación en la región alcanzable |
| `ubicaciones` | lista de `UbicacionLlave` | todas las ubicaciones conocidas |
| `puertas_que_la_bloquean` | lista de `PuertaFrontera` | puertas que habría que cruzar |

### PuertaFrontera

| Campo | Tipo | Regla |
|---|---|---|
| `puerta_id` | texto | una entrada por puerta |
| `desde_sala` | entero | sala de la región alcanzable |
| `hacia_sala` | entero | sala del otro lado |
| `direccion` | texto | dirección del lado alcanzable |
| `llave_requerida` | texto | llave que la abre |

### PasoCiclo

| Campo | Tipo | Regla |
|---|---|---|
| `llave` | texto | llave que se intenta obtener |
| `puerta_id` | texto | puerta concreta que la bloquea |
| `llave_requerida` | texto | llave que abre esa puerta |

Un ciclo es una secuencia de `PasoCiclo` donde la última llave requerida es la
primera de la secuencia (`FR-009`).

### ResultadoVerificacion

| Campo | Tipo | Regla |
|---|---|---|
| `resoluble` | booleano | según `FR-005` |
| `motivo` | texto | obligatorio si no es resoluble (p. ej. falta `llave_salida`, no hay puerta de salida con llave) |
| `orden_llaves` | lista de textos | vacía si no es resoluble; cada llave una vez y en orden válido (`FR-006`) |
| `llaves_inobtenibles` | lista de `LlaveInobtenible` | vacía si es resoluble |
| `frontera` | lista de `PuertaFrontera` | vacía si es resoluble |
| `ciclo` | lista de `PasoCiclo` o nulo | solo si existe (`FR-009`) |
| `llave_salida_obtenida` | booleano | parte del diagnóstico |
| `salida_por_puerta_con_llave` | booleano | resultado de la condición estricta de `FR-005` |

**Invariantes del reporte**

- Si `resoluble` es verdadero: `orden_llaves` contiene `llave_salida`,
  `llaves_inobtenibles` y `frontera` están vacías y `ciclo` es nulo.
- Si `resoluble` es falso: `motivo` no está vacío y al menos una de las listas
  de diagnóstico tiene contenido.
- El reporte es un valor inmutable para el consumidor: verificar no modifica la
  cripta ni el estado de una partida.

## 3. Transiciones

```text
inicio
  └─ visitar sala inicial
       ├─ descubrir llaves de la sala (orden de id)
       ├─ descubrir salidas (orden N, S, E, O)
       │    ├─ abierta → visitar destino
       │    └─ cerrada → retener bajo su llave
       └─ por cada llave obtenida
            └─ liberar sus puertas retenidas → visitar el otro lado
fin de la cola
  └─ construir ResultadoVerificacion
       ├─ ¿llave_salida obtenida? ¿salida con llave alcanzable? → resoluble
       └─ si no → frontera + inobtenibles + ciclo
```

## 4. Extensiones de contrato para la Persona A

Estas entidades pertenecen a la **spec 001** de A; la Persona B solo las lee y
las deja disponibles:

| Campo | Dónde | Regla |
|---|---|---|
| `DatosSalida.costo` | `modelo/datos.py` | entero ≥ 1; ausente = 100 |
| `Ficha.rango` | `modelo/datos.py` | entero ≥ 1; obligatorio para `cazador` (validar) |
| `comportamiento = "cazador"` | `modelo/actores.py` (A) | A debe aceptarlo en su enumeración |

**Validación**: si `comportamiento == "cazador"` y no hay `rango`, la ficha es
inválida y se informa; no se inventa un rango.

## 5. Archivos persistidos

| Archivo | Contenido | Invalidación |
|---|---|---|
| `<datos>/<cripta>/version.txt` | versión vigente | — |
| `<datos>/<cripta>/llaves.json` | `RespuestaLlaves` | se borra al cambiar la versión |
| `<datos>/<cripta>/esqueleto.json` | esqueleto | ya existente en P1 |

## 6. Trazabilidad entidad → requisito

| Entidad | Requisitos |
|---|---|
| `UbicacionLlave` / `RespuestaLlaves` | FR-016, FR-017, FR-018, FR-021, FR-024 |
| `PuertaRetenida` / `RegionAlcanzable` | FR-001..FR-005, FR-006, FR-007 |
| `PuertaFrontera` / `LlaveInobtenible` | FR-008, FR-022, FR-023 |
| `PasoCiclo` | FR-009 |
| `ResultadoVerificacion` | FR-005, FR-006, FR-008, FR-009, FR-010, FR-011, FR-013 |
| Extensiones `costo`/`rango`/`cazador` | Spec 001 de A (IDs por coordinar) |
