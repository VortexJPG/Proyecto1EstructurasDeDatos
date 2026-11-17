# Contract: conocimiento del mapa, «ir a» y comentario del log (A → B)

Puntos 4 y 5 de la tabla de contactos (mapa conocido con registro e inversión
de cambios; conocimiento listo para el archivo de partida). Responde a lo que
pidió la Persona B en
[`005/contracts/interfaz-a-b-timeline.md`](../../005-linea-de-tiempo/contracts/interfaz-a-b-timeline.md).

## 1. Conocimiento en el estado de la partida

```python
class Juego:
    def serializar_conocimiento(self) -> str: ...
    def restaurar_conocimiento(self, datos: str) -> None: ...
```

- `exportar_estado()` llena `EstadoGuardable.conocimiento` con
  `serializar_conocimiento()`; `desde_estado()` lo restaura.
- Como el conocimiento va **dentro del estado**, los puntos de control de la
  línea de tiempo ya lo incluyen y la re-simulación lo reproduce: B no
  necesita guardarlo aparte. `LineaGuardable.conocimiento` queda sin uso (se
  mantiene por compatibilidad del formato).
- El retroceso lo revierte solo (cada cambio es un `CambioCasilla`).

**Cambio en archivos de B (acordado aquí):** `adaptadores/guardado.py` escribe
y lee el campo `conocimiento` del bloque global (binario) y del JSON. Sigue
siendo el formato v3 (todavía no se había entregado).

## 2. Resumen histórico

`ResumenHistorico.mapa_conocido` pasa a ser la lista de salas **exploradas**
según el conocimiento (antes: salas visitadas) y se agrega `avistadas: int`.
`formatear_resumen` muestra ambas. Cambio pequeño en `modelo/timeline.py`.

## 3. `avanzar_hasta`

```python
class Juego:
    def avanzar_hasta(self, tiempo: int) -> None: ...
```

Ejecuta eventos con tiempo ≤ `tiempo` sin tomar la decisión pendiente (se
detiene en el `TURNO_JUGADOR`). `LineaTiempo._avanzar_hasta` puede delegar en
ella. No cambia reglas.

## 4. Comandos

```python
class TipoComando(Enum):
    ...
    MAPA = "mapa"   # sin argumento
    IR_A = "ir_a"   # argumento: id de sala como texto
```

El controlador:

```python
Controlador.ir_a(argumento: str) -> ResultadoViaje
```

ejecuta cada paso con `ejecutar_accion(Accion(MOVER, dir))` (precarga, línea de
tiempo y log normales) y la vista muestra el `ResultadoViaje`.

## 5. Comentario en `partida.log`

```python
class EscritorReplay:
    def comentario(self, texto: str) -> None:  # escribe "# " + texto
```

`LectorReplay.acciones()` ignora las líneas que empiezan con `#`.

## 6. Criterio de aceptación de la interfaz

- Guardar y cargar conserva `serializar_conocimiento()` exacto.
- `historia #k` muestra las salas exploradas antes de la acción k.
- Un log con `# ir a N` se reproduce igual que sin el comentario.
