# Research: Invalidación de rutas

## R1. Qué información depende de qué

El cálculo compartido es la función `dist(v)` = costo mínimo de `v` a la sala
del jugador `J`, restringida a las salas con `dist(v) ≤ A` (alcance). Depende
solo de: la sala `J`, el estado de las puertas y `A`. **No** depende de dónde
están los cazadores (cada uno lee su sala), de las velocidades ni del reloj.
Por eso un movimiento de otro actor o un cambio de velocidad no invalidan
nada.

## R2. Una puerta fuera de la región no cambia la respuesta

Sea `S = {v : dist(v) ≤ A}` (la región). Sea una puerta entre `a` y `b` con
`a ∉ S` y `b ∉ S`.

- **Cerrarla** solo puede quitar rutas. Toda ruta de costo ≤ A hacia `J` pasa
  solo por salas de `S` (cada sala de esa ruta tiene distancia ≤ A). Como el
  pasaje `a–b` no tiene extremos en `S`, ninguna de esas rutas lo usa: `S` y
  sus distancias no cambian.
- **Abrirla** solo puede agregar rutas que usan `a–b`. Si una ruta nueva de
  costo ≤ A la usara, el tramo desde `b` (o `a`) hasta `J` sería una ruta de
  costo < A sin ese pasaje, y entonces `b ∈ S`. Contradicción.

Por lo tanto basta revisar, en cada cambio de puerta, si alguno de sus dos
extremos está en `S`. Con las marcas de generación del buscador eso es O(1).
La regla es conservadora: una puerta en la región que no está en ninguna ruta
usada también invalida (puede costar un cálculo de más, nunca una decisión
distinta).

## R3. El cálculo no es estado del juego

No se guarda, no se registra en el historial ni en la línea de tiempo. Se
invalida solo, sin que el retroceso lo sepa:

- la sala del jugador se compara por identidad en cada decisión;
- `Puerta.cerrada` es una propiedad: el `setattr` que usa el retroceso
  (`CambioAtributo.revertir`), la carga y `Mapa.reiniciar_contenido` también
  pasan por ella y avisan;
- `Juego.desde_estado` crea un juego nuevo con su caché vacía.

**Alternativa descartada**: avisar a mano desde `_abrir` y `cerrar_puerta`. Es
fácil olvidar un camino (el retroceso restaura puertas con `setattr`), y un
aviso olvidado daría decisiones distintas a las de un cálculo desde cero.

## R4. ¿Cuánto se puede ahorrar?

- Con el jugador quieto y puertas estables: un cálculo sirve a todos los
  cazadores y a todos los turnos hasta que algo cambie.
- Con el jugador moviéndose: un cálculo por movimiento del jugador, compartido
  por todos los cazadores de ese ciclo (en vez de uno por turno de cazador).
- Con puertas inestables lejos: la invalidación fina mantiene el cálculo; la
  gruesa lo tira en cada cambio.

Lo confirma `--bench invalidacion` (ver §5.2 del Documento de Decisiones).

## R5. Alternativas consideradas

- **Recalcular siempre**: simple; costo = turnos de cazador × búsqueda.
- **Invalidación gruesa (versión global de puertas)**: un contador; cualquier
  cambio de puerta tira el cálculo.
- **Reparación incremental de distancias (tipo D\* Lite o LPA\*)**: reutiliza
  más, pero es mucho más código, difícil de probar contra el desempate y fuera
  de lo visto en el curso. Descartada.
