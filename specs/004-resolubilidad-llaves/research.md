# Research: Resolubilidad y llaves

Decisiones técnicas para el problema §5.4, alineadas con `spec.md`
(`FR-001..FR-024`, `SC-001..SC-007`). Este documento **no crea reglas nuevas**:
solo elige cómo cumplir la spec y qué alternativas se descartan.

## R1. Recorrido incremental único

**Decisión.** Expandir la región alcanzable una sola vez desde la sala inicial,
con una cola FIFO. Las puertas cerradas que se encuentran se **retienen
asociadas a la llave que las abre**. Cuando una llave se obtiene, se liberan
solo sus puertas retenidas y la expansión continúa; el recorrido **no se
reinicia**.

**Por qué.** Cumple `FR-001..FR-005` con costo ≈ lineal
(`SC-004`, `NFR-002`) y, en la misma pasada, produce el orden de llaves
(`FR-006`), la frontera (`FR-008`) y las llaves inobtenibles (`FR-008`).

**Cómo.** Sin nombrar clases todavía (eso está en `data-model.md`):

- región alcanzable marcada por id de sala (arreglo indexado o tabla ordenada);
- cola FIFO propia con las salas por expandir;
- por cada llave, una lista propia de puertas retenidas;
- al visitar una sala: se marcan las llaves que allí se obtienen (en orden de
  id), se liberan sus puertas y se encolan las salas del otro lado;
- las salidas se recorren siempre N, S, E, O;
- una puerta compartida entre dos sentidos se retiene una sola vez.

**Alternativas descartadas.**

| Alternativa | Por qué se descarta |
|---|---|
| Repetir el recorrido completo por cada llave | O(K·(R+E)); se conserva solo como **oráculo** de pruebas (R6). |
| Ignorar las puertas cerradas y comprobar aparte | Da falsos positivos: una llave puede estar detrás de una puerta. |
| Explorar el espacio de estados (subconjuntos de llaves) | Exponencial; innecesario porque las llaves no se consumen. |

**Complejidad esperada.** O(R + E + D + K log K), donde R = salas, E = salidas,
D = puertas liberadas (cada una se libera como mucho una vez) y K log K = ordenar
los ids de llaves por sala. Sin factores que dependan de K por cada sala.

## R2. Orden determinista de llaves

**Decisión.** Cada llave recibe un índice según su id (orden propio del repo).
Las ubicaciones se agrupan por sala; las llaves de una misma sala se liberan en
orden de id. Entre salas distintas, el orden lo fija la FIFO, que es
determinista porque las salidas se recorren N, S, E, O.

**Por qué.** `FR-006`, `FR-007` y `AC-004-03`. Dos ejecuciones con la misma
cripta y versión producen el mismo orden.

**Alternativas descartadas.**

| Alternativa | Por qué se descarta |
|---|---|
| Elegir en cada paso la llave de menor id global | O(K²) y no aporta nada al determinismo. |
| Ordenar solo al final por id | No garantiza que cada llave aparezca después de las necesarias. |
| Usar el orden de llegada de la respuesta HTTP | Depende de la red; rompe el determinismo. |

## R3. Frontera bloqueada y llaves inobtenibles

**Decisión.** Al terminar la expansión, las puertas que siguen retenidas bajo
llaves no obtenidas forman la frontera. Se reportan una sola vez por puerta
(aunque conecte dos salas), con la sala alcanzable, la sala del otro lado y la
llave que requiere. Las llaves cuya ubicación nunca entró en la región
alcanzable se reportan como inobtenibles, con su sala (y enemigo si aplica).

**Por qué.** `FR-008` y `AC-004-01`.

**Detalle.** Una puerta retenida desde un lado puede quedar alcanzable desde el
otro por un camino distinto; al liberar cualquiera de sus lados se encola el
lado no visitado.

## R4. Detección determinista del ciclo concreto

**Decisión.** Construir la relación «llave k necesita la llave j» a partir de la
frontera: si para alcanzar alguna ubicación de k hay que cruzar una puerta que
requiere j y j es inobtenible, entonces k depende de j. Para cada llave se
guarda **una** puerta representativa (la de menor id de sala y dirección),
elegida de forma determinista.

El ciclo se busca recorriendo las llaves inobtenibles en orden de id y siguiendo
siempre la dependencia de menor id; si se repite una llave, se reporta la
secuencia concreta de llaves y puertas, por ejemplo:
`itm_llave_negra → p-4E-6 (requiere itm_llave_negra) → itm_llave_negra`.

**Por qué.** `FR-009` y `AC-004-01`, sin recorrer toda la historia ni usar
bibliotecas de grafos.

**Alternativas descartadas.**

| Alternativa | Por qué se descarta |
|---|---|
| Reportar solo "hay un ciclo" | La spec exige el ciclo concreto. |
| Algoritmo de componentes fuertemente conexas | Correcto pero más complejo; con K pequeño el recorrido dirigido basta. |
| Recorrer en orden de aparición | Menos estable ante cambios de datos; el orden por id es reproducible. |

**Complejidad.** O(K + D), con K llaves y D puertas de frontera.

## R5. Persistencia de `/llaves` y presupuesto

**Decisión.**

1. Primero `datos_cripta` (fija `presupuesto_solicitudes`).
2. Después el esqueleto y la respuesta de llaves.
3. `llaves.json` se guarda dentro de la carpeta de la cripta; la validación de
   versión existente borra todo el contenido de la carpeta cuando la versión
   cambia, así que la invalidación es automática (`FR-018`, `FR-021`).
4. Si el presupuesto se agota, el error se propaga con un mensaje claro y
   `--verificar` termina con código distinto de 0 (`FR-020`).
5. `--offline` lee `llaves.json` del paquete local y no consume presupuesto
   (`FR-015`).

**Alternativas descartadas.**

| Alternativa | Por qué se descarta |
|---|---|
| Guardar las llaves dentro de `esqueleto.json` | Mezcla dos contratos y complica la invalidación selectiva. |
| No persistir la respuesta | Gasta presupuesto en cada inicio y el servicio puede limitar solicitudes. |
| Borrar archivos a mano al cambiar la versión | La spec exige usar la validación de versión existente. |

## R6. Oráculo ingenuo para pruebas

**Decisión.** Implementar una verificación ingenua que repite el recorrido desde
cero cada vez que obtiene una llave, con costo O(K·(R+E)). Se usa **solo en
pruebas** sobre criptas sintéticas pequeñas, para comprobar que el incremental
da el mismo veredicto y el mismo conjunto de llaves obtenibles (`SC-005`).
No se usa en producción.

**Por qué.** Es la forma más simple de tener una referencia independiente.

## R7. Generador de criptas sintéticas deterministas

**Decisión.** Un generador en `cripta/bench/sinteticos.py` que, a partir de una
semilla y parámetros, produce una cripta completa: datos generales, esqueleto,
contenido, ubicaciones de llaves y fichas mínimas. Parámetros:

- número de salas y grado de conectividad;
- rango de costos de salida;
- número de llaves y profundidad de encadenamiento (cada llave puede exigir
  cruzar puertas de llaves anteriores);
- puertas cambiantes (`cierre_automatico`) y puertas que empiezan cerradas;
- posición de `llave_salida` y de la sala de salida.

**Por qué.** Lo necesita la Persona A (punto 3, B→A) y lo usan el bench y las
pruebas. Debe ser determinista y no usar estructuras prohibidas.

**Alternativas descartadas.**

| Alternativa | Por qué se descarta |
|---|---|
| Generar criptas distintas en cada corrida | Rompe la reproducibilidad de las mediciones. |
| Reutilizar `cripta-0x` como banco de pruebas | Tamaño fijo, pocas llaves y no permite mostrar tendencias. |

## R8. Auditoría de estructuras prohibidas

| Necesidad | Se usa | Prohibido que se evita |
|---|---|---|
| Sala por id | `TablaOrdenada` (arreglo ordenado + búsqueda binaria) | `dict` |
| Marcar visitadas / llaves obtenidas | `ConjuntoOrdenado` o arreglo de booleanos por índice | `set` |
| Cola de expansión | `ColaEnlazada` | `collections.deque` |
| Puertas retenidas por llave | `TablaOrdenada` + `ListaDoble` propias | `defaultdict` / listas de listas sin control |
| Ordenar ids | `ordenamiento.ordenar` | `sorted()` / `list.sort()` |
| Detección de ciclo | recorrido dirigido propio sobre arreglos | `networkx` |

Los `dict` que aparecen al leer JSON en los adaptadores son lectura de datos,
no índices del problema evaluado, y ya se aceptaban en la Parte I.

## R9. Mediciones planificadas

- **Incremental vs. ingenuo** con criptas sintéticas de 100, 500, 1000 y 5000
  salas y K = 5, 10, 20, 40, 80 llaves encadenadas.
- **Verificación real** sobre la cripta publicada más grande (300 salas) para
  comprobar `SC-004` (≤ 200 ms).
- Varias repeticiones con semillas fijas; reportar mediana y mínimo.
- Límites configurables en `--bench` (no constantes en el código).
- Dos ejecuciones idénticas para `SC-002`.
