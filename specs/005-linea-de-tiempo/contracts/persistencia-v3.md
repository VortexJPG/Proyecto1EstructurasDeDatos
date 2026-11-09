# Contract: persistencia v3

Formato binario de la Partida II (`FR-025..FR-029`, `AC-005-06`).

## Encabezado

```text
"CRPT" | versión (u16) = 3 | cantidad de salas (u32) | offset del índice (u64)
```

Un archivo de la Parte I tiene versión 2. Al leerlo:

```text
ErrorFormatoIncompatible: versión de formato 2, se esperaba 3.
El archivo es de la Parte I; no se carga en silencio.
```

## Bloque global

| Campo | Codificación |
|---|---|
| `version_formato` | u16 (3) |
| `cripta_id`, `version_cripta`, `version_catalogo` | texto |
| `semilla` | i64 |
| `estado_azar` | texto/tupla (como en v2) |
| `reloj`, `siguiente_secuencia` | i64 |
| jugador, efectos, eventos, `objetos_generados` | como en v2 |
| `linea` | bloque de línea (abajo) |

### Bloque de línea

| Campo | Codificación |
|---|---|
| `k` | u32 |
| `cantidad_acciones` | u32 |
| acciones | por cada una: índice u32, tiempo i64, tipo texto, dirección/objetivo texto |
| `cantidad_contenidos` | u32 |
| contenidos | sala i32, longitud u32, `ContenidoSala` codificado |
| `cantidad_checkpoints` | u32 |
| checkpoints | índice u32, tiempo i64, longitud u64, estado completo codificado |
| `conocimiento` | longitud u32 + bytes/texto de la interfaz A |

Cada checkpoint es un `EstadoGuardable` completo (global + salas) codificado con
las mismas rutinas, sin su propia línea (para no anidar indefinidamente).

## Secciones posteriores

- Salas del estado actual: como en v2.
- Índice de salas: como en v2.

## Copia JSON

```json
{
  "version_formato": 3,
  "cripta_id": "...",
  "version_cripta": "...",
  "version_catalogo": "...",
  "linea": {
    "k": 25,
    "acciones": [...],
    "contenidos": [...],
    "checkpoints": [...],
    "conocimiento": "..."
  },
  "jugador": {...},
  "salas": [...],
  "efectos": [...],
  "eventos": [...]
}
```

Un JSON sin `version_formato` (Parte I) se rechaza como incompatible con el
mismo mensaje (`FR-028`).

## Invariantes

- Guardar y cargar no cambia la línea (`FR-025`).
- Al cargar, los checkpoints se validan contra la versión de la cripta y del
  catálogo.
- Una partida cargada puede seguir registrando acciones y consultando
  (`FR-029`).
- Nunca se migra en silencio: si se ofrece migración, es explícita y avisada.
