# Research: Línea de tiempo e historia

Decisiones para el problema §5.5, alineadas con `spec.md`
(`FR-001..FR-032`, `NFR-001..NFR-005`). No introduce reglas nuevas.

## R1. Representación de la línea

**Decisión.** La línea vigente guarda:

1. la **secuencia de acciones del jugador** (con el reloj al que empiezan);
2. el **contenido nuevo** que se incorporó después de cada acción (salas que
   la precarga o el movimiento cargaron);
3. **puntos de control** completos cada K acciones.

**Por qué.** El motor es determinista (una sola semilla), así que re-simular
las acciones reproduce exactamente todos los eventos intermedios sin guardar
un delta por mutación. Las acciones son O(1) cada una; el contenido nuevo se
guarda una vez por sala; los checkpoints son los únicos objetos grandes.

**Alternativas descartadas.**

| Alternativa | Por qué se descarta |
|---|---|
| Guardar cada mutación (delta) de todos los eventos | Memoria y persistencia mucho mayores; los `Cambio` actuales referencian objetos vivos y son difíciles de serializar. |
| Copia completa en cada acción | Prohibida por memoria (acciones × estado). |
| Guardar solo el log de replay y re-simular desde el inicio | Una consulta costaría O(n) acciones, no ≤ K. |

## R2. Reconstrucción hacia adelante

**Decisión.** Para un instante objetivo se busca el punto de control más
cercano **anterior o igual**, se reconstruye un `Juego` desde ese estado y se
re-simulan como máximo K acciones; después se avanzan los eventos hasta el
instante exacto. Cada checkpoint incluye el estado de `random.Random`.

**Por qué.** Reutiliza el motor real (una sola fuente de verdad), evita
invertir mutaciones y cumple FR-016 (≤ K acciones). El estado del azar en el
checkpoint garantiza que la re-simulación sea idéntica.

**Alternativas descartadas.**

| Alternativa | Por qué se descarta |
|---|---|
| Invertir deltas desde el estado actual | Habría que guardar y serializar todos los deltas; además, el estado actual puede estar muy lejos. |
| Re-simular desde el inicio | O(n) por consulta; incumple 50 ms con 5000 acciones. |
| Guardar una copia por acción | Memoria prohibitiva. |

## R3. Puntos de control y K

**Decisión.** Checkpoint en las acciones 0, K, 2K, … (el 0 es el estado
inicial). Una consulta aplica como máximo K acciones. `--checkpoint-cada K`
configura K; el valor por defecto se elige con `--bench` comparando tiempo y
memoria para K ∈ {10, 25, 50, 100} y la alternativa sin checkpoints.

**Por qué.** FR-015/016/020/021. Con K pequeño la consulta es rápida pero el
archivo y la memoria crecen; con K grande pasan lo contrario. El cruce se mide.

**Alternativa descartada.** Checkpoint cada acción: cumple el tiempo pero
incumple la memoria.

## R4. Semántica del instante y avance hasta t

**Decisión.** El estado en t es el que queda después de ejecutar todos los
eventos con tiempo ≤ t. Para lograrlo hacen falta dos operaciones del motor:

- `Juego.avanzar_hasta(t)`: ejecuta eventos de la agenda mientras su tiempo sea
  ≤ t; no ejecuta acciones del jugador.
- `Juego.ejecutar_accion(accion, hasta=None)`: con `hasta`, aplica la acción y
  avanza eventos solo hasta ese instante; sin `hasta`, conserva el
  comportamiento actual (hasta la siguiente decisión).

Ambas son **interfaz con la Persona A**; no cambian las reglas, solo permiten
detenerse en un instante. Hasta que A las entregue, la línea usa un doble de
prueba para las pruebas de reconstrucción.

**Por qué.** Sin el límite, ejecutar una acción avanza hasta la siguiente
decisión y se pasa de t. Para `#k` no hace falta (el estado justo antes de una
decisión ya está disponible).

**Alternativa descartada.** Aceptar solo instantes de decisión: incumple la
spec.

## R5. Recorte por pergamino

**Decisión.** Al revertir un intervalo, la línea se trunca en la posición
`juego.jugador.acciones_ejecutadas` (que el propio retroceso restaura). Se
eliminan las acciones posteriores y todos los checkpoints con índice mayor que
la nueva longitud. La numeración `#k` se recalcula sobre la línea vigente.

**Por qué.** FR-011..FR-014 y AC-005-02. Truncar por posición es O(1) para la
lista (o O(n) al copiar) y no recorre toda la historia.

## R6. Contenido nuevo por acción

**Decisión.** Después de cada acción se registran las salas cuyo contenido se
incorporó (movimiento y precarga) como `ContenidoSala`. En la reconstrucción se
aplican a un `Mapa` propio antes de ejecutar la acción correspondiente. Ese
contenido no consume azar ni secuencia, así que no altera la partida.

**Por qué.** Sin esto, re-simular una acción que entra a una sala cargada
después del checkpoint fallaría (`requiere_sala`) o consultaría la red. Con
esto la reconstrucción es offline y exacta (FR-017, V de la constitución).

**Alternativa descartada.** Pedir el contenido al servicio durante una
consulta: gastaría presupuesto y podría no estar disponible.

## R7. Persistencia v3

**Decisión.** El formato binario sube a v3. El bloque global lleva la línea:
acciones, contenidos y checkpoints (cada checkpoint es un `EstadoGuardable`
completo codificado como bloque). La copia JSON lleva `version_formato` y la
misma información. Un archivo v2 (P1) se rechaza con
`ErrorFormatoIncompatible`; un JSON sin `version_formato` también.

**Por qué.** FR-025..FR-029 y AC-005-06. Nunca se carga en silencio.

**Alternativa descartada.** Guardar la línea en un archivo aparte: rompe la
portabilidad de una partida y la validación de versiones.

## R8. Consulta sin tocar la partida viva

**Decisión.** La reconstrucción usa un `Mapa` propio construido desde el
esqueleto y un `Juego` nuevo desde el checkpoint. El proveedor de fichas es un
envoltorio de solo lectura que delega `obtener` y hace `fijar`/`liberar` no-op,
para no alterar los pines de la caché viva. La consulta no escribe en el log ni
en la línea.

**Por qué.** FR-006..FR-008 y AC-005-04. Evita efectos laterales sobre la
partida en curso.

## R9. Oráculo y pruebas

**Decisión.** Para muchos t y K se compara el estado reconstruido con el
obtenido re-simulando desde cero hasta t (oráculo). Se comparan reloj, jugador,
inventario, efectos, enemigos de la sala, agenda y conocimiento. Los seis
escenarios del Apéndice B se prueban con IDs `AC-005-01..06`.

## R10. Bench y elección de K

**Decisión.** `bench_timeline.py` mide:

- tiempo de consulta para K ∈ {10, 25, 50, 100} y para la alternativa sin
  checkpoints, con partidas sintéticas de 5000 acciones;
- memoria aproximada: suma de tamaños de checkpoints + acciones + contenidos;
- varias repeticiones, semillas fijas y mediana; límites configurables.

El K por defecto se elige en el cruce de tiempo/memoria y se documenta en
`DECISIONES.md` (§5.5).

## R11. Auditoría de estructuras prohibidas

| Necesidad | Se usa | Prohibido |
|---|---|---|
| Checkpoints ordenados por índice | `TablaOrdenada` + `busqueda_binaria` propia | `bisect` |
| Acciones | `list` (arreglo contiguo) | — |
| Recorte | truncar por posición | recorrer toda la historia |
| Contenido nuevo | `TablaOrdenada` por sala | `dict` |
| Resumen | listas y `ordenar` propio | `sorted` |

Nada de `heapq`, `collections` ni `networkx`.
