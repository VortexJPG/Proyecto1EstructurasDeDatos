# Data Model: Línea de tiempo e historia

Entidades de la línea, del resumen y de la persistencia. Los nombres de
estructuras concretas están en `research.md`.

## 1. AccionRegistrada

Una acción aceptada del jugador dentro de la línea vigente.

| Campo | Tipo | Regla |
|---|---|---|
| `indice` | entero | 1-based sobre la línea vigente; se renumera tras un recorte (`FR-012`) |
| `tiempo` | entero | reloj al que empieza la acción (decisión) |
| `accion` | registro de acción | tipo, dirección u objetivo |
| `contenidos_nuevos` | lista de `ContenidoSala` | salas cargadas después de esta acción (movimiento o precarga) |

**Invariantes**

- `indice` consecutivo desde 1.
- `tiempo` no decreciente.
- Toda acción de la línea fue aceptada por el motor.
- Una acción revertida por un pergamino no existe en la línea.

## 2. PuntoControl

Copia completa del estado en una acción múltiplo de K.

| Campo | Tipo | Regla |
|---|---|---|
| `indice_accion` | entero | 0 = estado inicial; K, 2K, … |
| `tiempo` | entero | reloj del estado |
| `estado` | `EstadoGuardable` | jugador, salas, efectos, agenda, `objetos_generados` |
| `estado_azar` | tupla | `random.Random.getstate()` (ya está dentro de `estado`) |

**Invariantes**

- Hay como máximo un punto de control cada K acciones (`FR-015`).
- El estado del generador aleatorio está incluido (`FR-018`).
- Un punto de control posterior al recorte se descarta (`FR-013`).
- El punto 0 existe siempre y representa el estado inicial.

## 3. ContenidoNuevo

| Campo | Tipo | Regla |
|---|---|---|
| `sala` | entero | sala incorporada |
| `contenido` | `ContenidoSala` | enemigos, objetos y trampas iniciales |
| `indice_accion` | entero | acción después de la cual se incorporó |

**Invariantes**

- Un contenido se guarda una sola vez por sala en toda la línea.
- Aplicarlo no consume azar ni secuencia; no cambia la partida.

## 4. LineaTiempo

| Campo | Tipo | Regla |
|---|---|---|
| `semilla` | entero | semilla de la partida |
| `k` | entero ≥ 1 | acciones entre puntos de control |
| `acciones` | lista de `AccionRegistrada` | línea vigente |
| `contenidos` | lista de `ContenidoNuevo` | salas cargadas |
| `checkpoints` | lista de `PuntoControl` | ordenados por `indice_accion` |
| `conocimiento` | `ConocimientoSerializado` | mapa conocido en el estado actual |

**Invariantes**

- `len(acciones)` = número de acciones vigentes = `juego.jugador.acciones_ejecutadas`.
- Los checkpoints están ordenados y sus índices son múltiplos de K.
- El checkpoint 0 y el estado actual se corresponden con la misma semilla.
- La línea es determinista (`FR-031`).

## 5. ResumenHistorico

Lo que se muestra en `historia` y en `--hasta`.

| Campo | Tipo | Regla |
|---|---|---|
| `reloj` | entero | instante consultado |
| `sala` | entero + nombre | sala del jugador |
| `vida` / `vida_max` | enteros | |
| `ataque`, `defensa`, `velocidad` | enteros | estadísticas efectivas |
| `inventario` | lista de objetos | con nombre y orden real |
| `efectos` | lista de efectos | tipo, magnitud y fin |
| `enemigos` | lista | presentes en la sala, con vida y activo/dormido (`clarify`) |
| `mapa_conocido` | estructura de A | conocimiento en ese instante (`FR-030`) |
| `terminada` | enum / nulo | si la partida había terminado y cómo |

**Invariantes**

- El resumen es un valor inmutable: consultarlo no altera la partida
  (`FR-008`).
- Si `reloj > reloj_actual`, la consulta se rechaza (`FR-009`).
- Varios eventos en el mismo instante se reflejan todos (`AC-005-03`).

## 6. ConocimientoSerializado

Interfaz con la Persona A (punto 5 de la tabla de contactos).

| Operación | Contrato |
|---|---|
| `serializar(juego) -> bytes/texto` | estado del conocimiento en ese instante |
| `deserializar(blob, juego)` | restaura el conocimiento en un juego reconstruido |

Hasta que A la entregue, el doble de prueba usa una representación mínima
(lista de salas conocidas) que se sustituye en la Fase 6.

## 7. Persistencia v3

| Bloque | Contenido |
|---|---|
| Encabezado | `CRPT`, versión 3, cantidad de salas, offset del índice |
| Global | estado actual + `version_formato`, `semilla`, azar, línea (K, acciones, contenidos, conocimiento) |
| Checkpoints | por cada punto: índice, tiempo, longitud y estado completo codificado |
| Salas | estado actual por sala |
| Índice | offsets de las salas |

**Validaciones**

- v2 o cualquier versión distinta ⇒ `ErrorFormatoIncompatible` con mensaje
  explícito (`FR-027`).
- JSON sin `version_formato` ⇒ incompatible (`FR-028`).
- Una partida cargada conserva la línea y puede seguir registrando (`FR-029`).

## 8. Relaciones y transiciones

```text
iniciar partida
  └─ checkpoint 0 (estado inicial)

ejecutar acción aceptada
  ├─ registrar acción + tiempo
  ├─ registrar contenidos nuevos
  └─ si acciones % K == 0 → checkpoint

usar pergamino aceptado
  └─ truncar línea en acciones_ejecutadas
       ├─ descartar acciones posteriores
       └─ descartar checkpoints posteriores

historia t / #k
  ├─ validar rango
  ├─ buscar checkpoint ≤ objetivo (búsqueda binaria propia)
  ├─ reconstruir en mapa propio + re-simular ≤ K acciones
  ├─ avanzar_hasta(t) si el objetivo es un instante
  └─ construir ResumenHistorico (sin tocar la partida)

guardar / cargar
  ├─ incluir línea completa
  └─ rechazar P1 de forma explícita
```

## 9. Trazabilidad entidad → requisito

| Entidad | Requisitos |
|---|---|
| `AccionRegistrada` | FR-004, FR-011, FR-012, FR-032 |
| `PuntoControl` | FR-015..FR-021 |
| `ContenidoNuevo` | FR-017, FR-030, FR-032 |
| `LineaTiempo` | FR-001..FR-008, FR-031 |
| `ResumenHistorico` | FR-005, FR-009, FR-010, NFR-001 |
| `ConocimientoSerializado` | FR-030 |
| Persistencia v3 | FR-025..FR-029 |
