# Feature Specification: Terreno y cazador

**Feature Branch**: `001-terreno-cazador`

**Created**: 2026-11-15

**Status**: Clarified

**Input**: User description: "Las salidas tienen costo de tránsito y aparece un enemigo, el cazador, que calcula la ruta más barata hacia el jugador dentro de su rango, con desempate por menor id (Parte II, Persona A; §3.1, §3.2, §5.1)."

## Clarifications

### Session 2026-11-15

- Q: ¿Qué costo vale si los dos sentidos de un mismo pasaje declaran costos distintos? → A: El costo es uno solo para el pasaje. Si solo un sentido lo declara, vale para los dos; si los dos lo declaran con valores distintos, vale el del primer sentido en el orden del esqueleto (orden de las salas y, dentro de la sala, N, S, E, O). Así el resultado es determinista y no depende de cuál página llegó primero.
- Q: ¿Qué pasa si una salida trae un `costo` que no es un entero mayor o igual que 1? → A: El esqueleto es inválido: se informa el error con la sala y la dirección, y la cripta no se juega. No se corrige en silencio.
- Q: ¿Qué pasa si un enemigo `cazador` no trae `rango` o trae un valor menor que 1? → A: La ficha es inválida: se informa el error y no se inventa un rango.
- Q: ¿El cazador se mueve cuando el costo mínimo es exactamente igual a su rango? → A: Sí. Espera solo si no hay ruta o si el costo mínimo es **mayor** que el rango.
- Q: ¿Qué hace el cazador si desde su sala hay dos salidas distintas hacia la misma vecina y las dos empiezan una ruta de costo mínimo? → A: Va a esa vecina por la primera de esas salidas en el orden N, S, E, O; el costo de su acción es el costo de esa salida.
- Q: ¿Un cazador dormido calcula rutas? → A: No. Como todo enemigo, empieza a actuar cuando el jugador entra a su sala (P1 §2.4); su primera acción cuesta 100.
- Q: ¿Los demás actores bloquean la ruta del cazador? → A: No. Los actores no ocupan casillas: solo cuentan las salidas y el estado de sus puertas.
- Q: ¿El costo de la salida cambia el costo de atacar o esperar? → A: No. Solo cambia el costo de moverse; atacar y esperar siguen costando 100 para todos los actores.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Moverse cuesta según el terreno (Priority: P1)

Como jugador, quiero que cruzar un pasaje largo o difícil tarde más que cruzar
uno corto, y que la misma regla valga para todos los actores, para que el mapa
importe al decidir por dónde ir.

**Why this priority**: es la regla base de la Parte II; el cazador, «ir a» y
las mediciones dependen de ella.

**Independent Test**: moverse por salidas con costos distintos (y por una sin
costo declarado) y comprobar el instante del siguiente turno del jugador y de
un enemigo errante.

**Acceptance Scenarios**:

1. **Given** una salida con costo 250 y un jugador de velocidad 100, **When**
   el jugador la cruza en t=0, **Then** su siguiente turno es en t=250.
2. **Given** una salida sin costo declarado, **When** cualquier actor la cruza,
   **Then** el movimiento cuesta 100.
3. **Given** un actor de velocidad 200 que cruza una salida de costo 1,
   **When** se programa su siguiente turno, **Then** el intervalo es 1 (nunca
   0). *(AC-001-05)*
4. **Given** un actor que cruzó una salida de costo 300 con velocidad 100 en
   t=0 (próximo turno en t=300), **When** en t=100 su velocidad pasa a 200,
   **Then** el tiempo restante se escala según P1 §2.3 y su próximo turno queda
   en t=200. *(AC-001-06)*
5. **Given** un errante o un rastreador, **When** se mueve, **Then** decide
   igual que en la Parte I y solo cambia lo que tarda: el costo de la salida
   que cruzó.

---

### User Story 2 - El cazador persigue por la ruta más barata (Priority: P1)

Como jugador, quiero que exista un enemigo que me persiga por el camino más
barato cuando estoy dentro de su alcance, para que esconderse detrás de
pasajes caros o puertas cerradas sea una estrategia real.

**Why this priority**: es el comportamiento nuevo que más peso tiene en la
evaluación (20 %) y el que usa las rutas ponderadas.

**Independent Test**: colocar un cazador activo en criptas pequeñas con costos
elegidos a mano y comprobar, turno a turno, si ataca, espera o hacia dónde se
mueve.

**Acceptance Scenarios**:

1. **Given** un cazador activo sin ninguna ruta abierta hacia la sala del
   jugador, **When** le toca actuar, **Then** espera con costo 100.
   *(AC-001-01)*
2. **Given** un cazador cuya ruta más barata hacia el jugador cuesta más que su
   rango, **When** le toca actuar, **Then** espera con costo 100.
   *(AC-001-02)*
3. **Given** una ruta de menos salas pero mayor costo y otra de más salas y
   menor costo, **When** el cazador actúa, **Then** sigue la de menor costo.
   *(AC-001-03)*
4. **Given** un cazador en la misma sala que el jugador, **When** le toca
   actuar, **Then** ataca y no se mueve.
5. **Given** un cazador con ruta de costo d ≤ rango, **When** se mueve, **Then**
   avanza una sola sala y la acción cuesta el costo de la salida que cruzó.
6. **Given** una sala cuyo contenido aún no se descargó, **When** el cazador
   calcula su ruta, **Then** la decisión es la misma que si el contenido ya
   estuviera cargado.

---

### User Story 3 - Desempate reproducible (Priority: P1)

Como jugador (y como evaluador), quiero que, cuando hay varias rutas igual de
baratas, el cazador siempre escoja la misma, para que dos programas distintos
den la misma partida.

**Why this priority**: sin desempate fijo no hay determinismo ni replay fiel.

**Independent Test**: criptas con varias rutas de igual costo (cuadrículas con
todos los costos iguales) y comparación contra un cálculo de referencia hecho
desde cero.

**Acceptance Scenarios**:

1. **Given** dos vecinas de la sala del cazador que inician rutas de costo
   mínimo, **When** el cazador se mueve, **Then** va a la de menor id.
   *(AC-001-04)*
2. **Given** muchas rutas de igual costo, **When** se repite la misma partida,
   **Then** el cazador hace exactamente los mismos movimientos.

---

### User Story 4 - Decenas de cazadores sin trabarse (Priority: P2)

Como jugador, quiero que la partida responda igual de rápido aunque haya
decenas de cazadores activos persiguiéndome.

**Why this priority**: es un límite de rendimiento de la evaluación (§6.1),
pero depende de las historias anteriores.

**Independent Test**: la cripta de referencia con todos sus cazadores activos y
la medición del ciclo entre dos decisiones del jugador.

**Acceptance Scenarios**:

1. **Given** la cripta de referencia con decenas de cazadores activos, **When**
   se resuelve el ciclo de eventos entre dos decisiones, **Then** tarda como
   máximo 20 ms.
2. **Given** un cazador de rango pequeño en una cripta muy grande, **When**
   decide, **Then** su costo depende de la región dentro de su rango y no del
   tamaño total de la cripta.

---

### User Story 5 - Ver el terreno y reconocer a los cazadores (Priority: P2)

Como jugador, quiero ver cuánto cuesta cada salida de mi sala y distinguir a
los cazadores de los demás enemigos, para planear mi ruta.

**Why this priority**: es parte de la interfaz mínima (§7.3); no cambia reglas.

**Independent Test**: mostrar una sala con salidas de costos distintos y un
cazador junto a otro enemigo, en la terminal y en la ventana.

**Acceptance Scenarios**:

1. **Given** una sala con salidas de costo 20, 100 y 300, **When** se muestra
   la sala, **Then** se ve el costo de cada salida.
2. **Given** una sala con un cazador y una rata, **When** se muestra la sala,
   **Then** el cazador aparece marcado como cazador (con su rango).

---

### Edge Cases

- Salida sin `costo`: vale 100.
- `costo` igual a 1 con un actor muy rápido: el intervalo nunca baja de 1.
- Costos distintos en los dos sentidos de un pasaje: vale el primero en el orden
  del esqueleto.
- `costo` inválido (0, negativo, texto): error explícito al construir el mapa.
- Cazador sin `rango` o con `rango` < 1: ficha inválida, error explícito.
- Ruta de costo exactamente igual al rango: el cazador se mueve.
- El jugador está detrás de una puerta cerrada: el cazador no la abre; si no hay
  otra ruta, espera.
- Varias salidas desde la sala del cazador hacia la misma vecina: vale la
  primera en N, S, E, O que inicia una ruta de costo mínimo.
- Salida de un solo sentido (sin regreso): se respeta su sentido; el cazador
  solo puede cruzarla en el sentido declarado.
- El jugador cambia de sala, se abre o cierra una puerta, otro actor se mueve o
  muere entre dos turnos de un cazador: la decisión siempre es la de un cálculo
  desde cero (detalle en la spec 002).
- Cazador dormido: no calcula ni se mueve hasta activarse.
- Pergamino de retroceso: después de retroceder, la siguiente decisión del
  cazador es la de un cálculo desde cero con el estado restaurado.

## Requirements *(mandatory)*

### Functional Requirements

**Terreno**

- **FR-001**: Cada salida MAY declarar un `costo` entero ≥ 1. Si no lo
  declara, su costo MUST ser 100.
- **FR-002**: El costo de un pasaje MUST ser el mismo en ambos sentidos. Si solo
  un sentido lo declara, MUST valer para los dos; si los dos lo declaran con
  valores distintos, MUST valer el del primer sentido en el orden del esqueleto.
- **FR-003**: Un `costo` que no sea entero ≥ 1 MUST rechazarse como esqueleto
  inválido, con un mensaje que indique la sala y la dirección.
- **FR-004**: Moverse a través de una salida MUST ser una acción cuyo costo base
  es el costo de esa salida, y el intervalo MUST calcularse como
  `max(1, costo_salida * 100 // velocidad)`.
- **FR-005**: La regla de FR-004 MUST aplicarse a todos los actores (jugador,
  errantes, rastreadores y cazadores). Errantes y rastreadores MUST conservar
  sus reglas de decisión de la Parte I.
- **FR-006**: El costo de atacar, esperar y las demás acciones MUST NOT cambiar.
- **FR-007**: Si cambia la velocidad de un actor con un turno pendiente, el
  tiempo restante MUST escalarse con la regla de P1 §2.3, también cuando el
  turno pendiente viene de cruzar una salida costosa.

**Cazador**

- **FR-008**: Debe existir un cuarto comportamiento de enemigo, `cazador`, cuya
  ficha incluye `rango`, un entero ≥ 1 en unidades de costo. Una ficha de
  cazador sin `rango` válido MUST rechazarse.
- **FR-009**: En su turno, si el cazador comparte sala con el jugador, MUST
  atacar (P1 §2.8) con costo 100.
- **FR-010**: Si no comparte sala, MUST considerar el costo mínimo `d` de llegar
  desde su sala hasta la sala actual del jugador, sumando el costo de cada
  salida recorrida y usando únicamente salidas abiertas en ese instante.
- **FR-011**: Si no existe ruta, o si `d > rango`, el cazador MUST esperar con
  costo 100.
- **FR-012**: Si existe ruta y `d ≤ rango`, el cazador MUST moverse una sala por
  una ruta de costo `d`; el costo de esa acción MUST ser el costo de la salida
  que atraviesa.
- **FR-013**: Entre las vecinas `v` de la sala `u` del cazador tales que
  `costo(u, v) + dist(v, jugador) = d`, el cazador MUST moverse a la de menor
  id. Si varias salidas de `u` llevan a esa vecina y cumplen la condición, MUST
  usar la primera en el orden N, S, E, O.
- **FR-014**: El cálculo del cazador MUST depender solo del esqueleto completo
  (con el costo de cada salida) y del estado actual de las puertas; MUST NOT
  depender de la niebla de guerra del jugador ni de si el contenido de una sala
  ya fue descargado. El cazador MUST NOT abrir puertas.
- **FR-015**: La decisión del cazador en cada turno MUST ser idéntica a la que
  se obtendría calculando la ruta desde cero en ese instante (equivalencia
  observable; la reutilización de cálculos se especifica en la spec 002).
- **FR-016**: Un cazador dormido MUST NOT decidir ni moverse; se activa como
  cualquier enemigo (P1 §2.4).
- **FR-017**: La decisión del cazador MUST NOT consumir el generador aleatorio
  de la partida ni depender del reloj real; misma cripta, semilla y acciones
  MUST producir los mismos movimientos.
- **FR-018**: Los costos y los rangos MUST venir del servicio (o del paquete
  offline); el código MUST NOT contener datos de una cripta concreta.

**Interfaz y medición**

- **FR-019**: La vista MUST mostrar el costo de cada salida de la sala actual.
- **FR-020**: La vista MUST distinguir a los cazadores de los demás enemigos.
- **FR-021**: `--bench` MUST medir un cazador frente a muchos, rango pequeño
  frente a rango grande, y cálculo compartido frente a cálculo individual, sin
  instanciar la vista.

### Performance Requirements

- **NFR-001**: El ciclo de eventos entre dos decisiones del jugador MUST
  resolverse en **≤ 20 ms** en la cripta de referencia con decenas de
  cazadores activos, medido sin red ni renderizado.
- **NFR-002**: La decisión de un cazador de rango pequeño MUST costar en
  proporción a la región que queda dentro de su rango, no al tamaño de la
  cripta.
- **NFR-003**: Se MUST medir si conviene un cálculo por cazador o un cálculo
  compartido, y documentar bajo qué condiciones cambia la respuesta.
- **NFR-004**: Las mediciones MUST usar criptas deterministas por semilla,
  varias repeticiones y reportar mediana (y peor caso cuando aplique).

### Key Entities

- **Salida**: conexión desde una sala hacia otra en una dirección, con su
  costo de tránsito y, si la tiene, una puerta.
- **Pasaje**: las dos salidas (ida y vuelta) entre dos salas; comparten costo y
  puerta.
- **Cazador**: enemigo con comportamiento `cazador` y `rango`.
- **Ruta**: secuencia de salidas abiertas desde una sala hasta otra; su costo es
  la suma de los costos.
- **Distancia al jugador**: costo mínimo de una ruta desde una sala hasta la
  sala actual del jugador.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Los seis casos del Apéndice B de esta spec (AC-001-01 a AC-001-06)
  quedan cubiertos por pruebas automatizadas que citan su ID.
- **SC-002**: En cientos de situaciones aleatorias deterministas (costos, puertas
  y posiciones), la decisión del cazador coincide en el 100 % de los turnos con
  un cálculo de referencia hecho desde cero.
- **SC-003**: El peor ciclo entre dos decisiones en la cripta de referencia con
  todos sus cazadores activos es ≤ 20 ms.
- **SC-004**: El tiempo de decisión de un cazador de rango pequeño se mantiene
  aproximadamente constante al multiplicar el tamaño de la cripta.
- **SC-005**: Dos ejecuciones con la misma cripta, semilla y acciones producen
  el mismo estado final y el mismo `partida.log`.

## Assumptions

- La lectura de `costo` en el esqueleto y de `rango` y `comportamiento` en el
  catálogo la entrega la Persona B (punto 1 de contacto); esta spec define qué
  significan para el juego.
- La cripta de referencia del curso es la publicada como «Cripta de
  referencia» (hoy 300 salas y decenas de cazadores).
- Las puertas con cierre automático se cierran por su evento, igual que en la
  Parte I; el cazador las ve tal como están en cada instante.
- La invalidación y reutilización de cálculos entre turnos se especifica en la
  spec 002; la niebla de guerra y «ir a», en la spec 003.
