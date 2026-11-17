# Feature Specification: Niebla de guerra e «ir a»

**Feature Branch**: `003-niebla-ir-a`

**Created**: 2026-11-15

**Status**: Clarified

**Input**: User description: "El jugador solo conoce la parte del mapa que ha explorado (salas exploradas, avistadas y desconocidas, con memoria de puertas y antorcha) y puede viajar automáticamente dentro de ella con «ir a <sala>» (Parte II, Persona A; §3.3, §3.4, §5.3)."

## Clarifications

### Session 2026-11-15

- Q: ¿El jugador conoce el estado de las puertas de una sala que exploró con la antorcha, si esas puertas no conectan con la sala donde está? → A: No. Sabe que la salida existe, hacia dónde va, cuánto cuesta y si tiene puerta, pero el estado de esa puerta queda "sin observar" hasta que esté en una de sus dos salas. «ir a» no usa puertas sin observar. Un pasaje sin puerta siempre se conoce como abierto.
- Q: ¿La antorcha explora las vecinas en el momento de encenderla? → A: No. La regla dice "al entrar a una sala": tiene efecto en cada entrada a una sala mientras esté encendida. La sala donde se enciende ya está explorada.
- Q: ¿Qué muestra la interfaz de una sala avistada? → A: Solo que hay una sala detrás de esa salida: ni nombre, ni id, ni contenido.
- Q: ¿Cuándo observa el jugador una puerta? → A: Al entrar a una de sus dos salas (todas las puertas de esa sala) y cada vez que una puerta de la sala donde está cambia de estado (la abre él o se cierra sola), porque la está viendo.
- Q: ¿Qué cuenta como "recibe daño" para detener el viaje? → A: Cualquier pérdida de vida entre el inicio de un paso y la siguiente decisión del jugador: ataque, trampa o veneno.
- Q: ¿Puede empezar un viaje en una sala con enemigos? → A: Sí. La condición de parada por enemigos se revisa al entrar a cada sala nueva del viaje.
- Q: ¿Qué pasa con «ir a» hacia la sala donde ya está el jugador? → A: Se informa que ya está ahí, no consume tiempo y no se registra.
- Q: ¿Qué pasa si un paso del viaje es rechazado por el juego? → A: El viaje se detiene con ese motivo; el paso rechazado no consume tiempo.
- Q: ¿Cómo se escribe el comentario de «ir a» en `partida.log`? → A: Una línea que empieza con `#` antes del primer paso (`# ir a 12`); la reproducción ignora las líneas de comentario.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver solo lo que conozco (Priority: P1)

Como jugador, quiero que la interfaz me muestre solo las salas que exploré,
las que alcanzo a ver desde ellas y el estado de las puertas tal como lo
recuerdo, para que explorar tenga sentido.

**Why this priority**: es la regla central de la niebla de guerra (§3.3).

**Independent Test**: entrar a algunas salas y comprobar el estado de cada sala
(explorada, avistada, desconocida) y de cada puerta recordada.

**Acceptance Scenarios**:

1. **Given** el inicio de la partida, **When** se consulta el mapa conocido,
   **Then** solo la sala inicial está explorada, sus destinos están avistados y
   el resto es desconocido.
2. **Given** una puerta con cierre automático que el jugador vio abierta,
   **When** se cierra mientras él está en otra parte, **Then** el mapa la sigue
   recordando abierta hasta que la vuelva a observar.
3. **Given** una sala avistada, **When** se muestra la sala actual, **Then** de
   esa salida solo se informa que hay una sala detrás (sin nombre ni id).

---

### User Story 2 - Consultar el mapa conocido (Priority: P1)

Como jugador, quiero un comando para ver el mapa que conozco: salas
exploradas, sus salidas con costo y estado recordado, y las salas avistadas.

**Why this priority**: es parte de la interfaz mínima (§7.3).

**Independent Test**: ejecutar el comando en la terminal y en la ventana
después de explorar.

**Acceptance Scenarios**:

1. **Given** tres salas exploradas, **When** se pide el mapa, **Then** se listan
   esas tres con sus salidas (dirección, costo, puerta recordada y destino si
   está explorado) y la cantidad de salas avistadas.
2. **Given** el mapa conocido, **When** se pide, **Then** no aparece ninguna
   sala desconocida ni el contenido de salas no visitadas.

---

### User Story 3 - Viajar automáticamente con «ir a» (Priority: P1)

Como jugador, quiero escribir `ir a <sala>` y que el juego me lleve por la ruta
más barata que conozco, deteniéndose si pasa algo importante, y que me diga
por qué se detuvo.

**Why this priority**: es la capacidad nueva de la interfaz (§3.4) y el 10 % de
la evaluación junto con la niebla.

**Independent Test**: viajes en criptas pequeñas con enemigos, trampas y
puertas recordadas de forma incorrecta.

**Acceptance Scenarios**:

1. **Given** una sala no explorada, **When** se ejecuta `ir a` hacia ella,
   **Then** se rechaza y no consume tiempo. *(AC-003-01)*
2. **Given** que el mapa recuerda abierta una puerta que en realidad está
   cerrada, **When** el viaje llega a una sala desde donde la observa, **Then**
   el mapa se actualiza y la ruta se recalcula; si no queda ruta, el viaje se
   detiene sin consumir tiempo adicional. *(AC-003-02)*
3. **Given** un viaje que entra a una sala con enemigos dormidos, **When** el
   jugador entra, **Then** los enemigos se activan según P1 §2.4 y el viaje se
   detiene. *(AC-003-03)*
4. **Given** un viaje, **When** el jugador recibe daño o llega al destino,
   **Then** el viaje se detiene e informa el motivo.
5. **Given** una puerta cerrada con llave en la única ruta, **When** se pide el
   viaje, **Then** no se abre la puerta aunque el jugador tenga la llave.
6. **Given** un viaje de varios pasos, **When** se revisa `partida.log`,
   **Then** cada paso es un movimiento individual y la orden aparece como
   comentario.

---

### User Story 4 - La antorcha ilumina las vecinas (Priority: P2)

Como jugador, quiero que con la antorcha encendida, al entrar a una sala,
queden exploradas sus vecinas, sin despertar a sus enemigos ni activar sus
trampas.

**Why this priority**: le da efecto a la antorcha de P1 §2.7; depende de US1.

**Independent Test**: encender la antorcha, entrar a una sala y revisar el
estado de las vecinas, la vida y los enemigos.

**Acceptance Scenarios**:

1. **Given** la antorcha encendida, **When** el jugador entra a una sala,
   **Then** sus vecinas (por cualquier salida, abierta o cerrada) quedan
   exploradas sin activar sus enemigos ni sus trampas. *(AC-003-04)*
2. **Given** una entrada con antorcha encendida, **When** se usa un pergamino,
   **Then** las salas exploradas por la antorcha vuelven a su estado anterior.
   *(AC-003-05)*

---

### User Story 5 - El conocimiento es parte de la partida (Priority: P1)

Como jugador, quiero que lo que sé del mapa se guarde con la partida, se
deshaga con el pergamino y aparezca en la historia.

**Why this priority**: lo exige §3.3 y lo necesitan la línea de tiempo y el
guardado (spec 005).

**Independent Test**: guardar, cargar, retroceder y consultar `historia`
comparando el mapa conocido.

**Acceptance Scenarios**:

1. **Given** un viaje de varios pasos, **When** se usa un pergamino, **Then**
   solo se revierte el último paso y el viaje no continúa. *(AC-003-06)*
2. **Given** una partida con salas exploradas, **When** se guarda y se carga,
   **Then** el mapa conocido es el mismo.
3. **Given** una partida avanzada, **When** se consulta `historia #k`, **Then**
   el mapa conocido mostrado es el que tenía el jugador antes de la acción k.

---

### Edge Cases

- `ir a` con un id que no existe, con texto que no es número o sin argumento.
- `ir a` hacia la sala actual.
- Sala explorada pero sin ruta conocida (todas las puertas recordadas cerradas
  o sin observar).
- Puerta sin observar en una sala explorada por antorcha.
- Dos salidas desde la misma sala hacia la misma vecina con costos distintos.
- La partida termina (victoria o derrota) en medio de un viaje.
- Un enemigo entra a la sala del jugador entre pasos sin hacerle daño: el viaje
  sigue (la regla solo detiene al entrar a una sala con enemigos o al recibir
  daño).
- Antorcha que se apaga en medio de un viaje: las entradas siguientes ya no
  exploran vecinas.
- Retroceso que deshace la entrada a una sala explorada por primera vez.
- Archivo de partida guardado antes de esta capacidad: lo detecta la spec 005.

## Requirements *(mandatory)*

### Functional Requirements

**Conocimiento del mapa**

- **FR-001**: Para el jugador, cada sala MUST estar en uno de tres estados:
  explorada, avistada o desconocida.
- **FR-002**: La sala inicial MUST estar explorada desde el instante 0.
- **FR-003**: Una sala MUST quedar explorada cuando el jugador entra a ella al
  menos una vez (o cuando la explora la antorcha, FR-010).
- **FR-004**: Una sala MUST estar avistada si no está explorada y es destino de
  una salida de una sala explorada; si no, MUST ser desconocida.
- **FR-005**: De una sala explorada, el jugador MUST conocer nombre, salidas,
  costo de cada salida y el estado de sus puertas según la última observación.
- **FR-006**: De una sala avistada, el jugador MUST conocer solo que existe una
  sala detrás de esa salida.
- **FR-007**: El jugador MUST observar una puerta cuando está en cualquiera de
  las dos salas que conecta: al entrar a la sala y cada vez que esa puerta
  cambia de estado mientras él está allí.
- **FR-008**: El mapa MUST recordar el estado de cada puerta tal como estaba en
  su última observación, aunque haya cambiado después.
- **FR-009**: Una puerta nunca observada MUST figurar como "sin observar".
- **FR-010**: Mientras la antorcha esté encendida, al entrar a una sala MUST
  quedar exploradas también todas sus vecinas, a través de cualquier salida,
  abierta o cerrada.
- **FR-011**: Explorar una vecina con la antorcha MUST revelar su nombre y sus
  salidas, no su contenido, y MUST NOT activar sus enemigos ni sus trampas.
- **FR-012**: Todo lo que la vista muestra del mapa y todo lo que usa «ir a»
  MUST derivarse exclusivamente del conocimiento del jugador. La precarga MAY
  usar el esqueleto completo.
- **FR-013**: La interfaz MUST ofrecer un comando para ver el mapa conocido:
  salas exploradas, sus salidas (dirección, costo, puerta recordada y destino
  si está explorado) y las salas avistadas.
- **FR-014**: El conocimiento del jugador MUST guardarse en el archivo de
  partida y restaurarse al cargar.
- **FR-015**: El pergamino de retroceso MUST revertir el conocimiento junto con
  la acción, incluida la exploración hecha por la antorcha.
- **FR-016**: El conocimiento MUST formar parte de la línea de tiempo:
  `historia` muestra el mapa conocido de ese instante.

**«ir a»**

- **FR-017**: El comando `ir a <sala>` MUST llevar al jugador a una sala
  explorada mediante una secuencia de movimientos ordinarios.
- **FR-018**: Si la sala pedida no está explorada (o no existe, o el argumento
  no es válido), el comando MUST rechazarse sin consumir tiempo. Si es la sala
  actual, MUST informarse sin consumir tiempo.
- **FR-019**: La ruta MUST calcularse solo con el conocimiento del jugador:
  únicamente salas exploradas y salidas que el mapa recuerda abiertas (las
  puertas recordadas cerradas o sin observar no se usan). MUST minimizar la
  suma de costos y desempatar como el cazador: primer paso hacia la vecina de
  menor id (y, hacia la misma vecina, la primera salida en N, S, E, O).
- **FR-020**: Cada paso MUST ser una acción completa del jugador: consume
  tiempo según el costo de la salida (spec 001) y entre paso y paso ocurren
  normalmente los eventos del reloj.
- **FR-021**: La ruta MUST recalcularse antes de cada paso con el conocimiento
  vigente.
- **FR-022**: El viaje MUST detenerse cuando: el jugador llega al destino; entra
  a una sala que contiene enemigos, activos o dormidos; recibe daño; deja de
  existir una ruta conocida; la partida termina; o un paso es rechazado.
- **FR-023**: El viaje MUST NOT abrir puertas aunque el jugador tenga la llave.
- **FR-024**: En `partida.log`, cada paso MUST registrarse como un movimiento
  individual y la orden `ir a` MUST registrarse además como comentario; la
  reproducción MUST ignorar los comentarios.
- **FR-025**: El pergamino de retroceso MUST revertir únicamente el último paso
  del viaje, y el viaje MUST NOT continuar.
- **FR-026**: La interfaz MUST mostrar cuántos pasos se dieron y por qué se
  detuvo el viaje.
- **FR-027**: Misma cripta, semilla y órdenes MUST producir el mismo viaje y el
  mismo `partida.log`.

### Performance Requirements

- **NFR-001**: El cálculo de un paso de «ir a» MUST tomar **≤ 5 ms** con el mapa
  conocido completo de la cripta de referencia.
- **NFR-002**: Consultar si una sala está explorada, avistada o desconocida y el
  estado recordado de una puerta MUST costar lo mismo sin importar cuánto mapa
  se conoce.
- **NFR-003**: Explorar nuevas salas MUST costar en proporción a las salas
  reveladas, no al tamaño del mapa conocido.
- **NFR-004**: Registrar e invertir los cambios del conocimiento MUST costar en
  proporción a lo que cambió en esa acción.
- **NFR-005**: `--bench` MUST medir las consultas al mapa conocido y el cálculo
  de «ir a», sin instanciar la vista.

### Key Entities

- **Conocimiento del jugador**: estado de cada sala (explorada, avistada,
  desconocida) y estado recordado de cada puerta.
- **Puerta recordada**: abierta, cerrada o sin observar, según la última
  observación.
- **Viaje**: orden `ir a` con su destino, los pasos dados y el motivo de la
  detención.
- **Mapa conocido**: vista del conocimiento para la interfaz y para `historia`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Los seis casos del Apéndice B de esta spec (AC-003-01 a AC-003-06)
  quedan cubiertos por pruebas automatizadas que citan su ID.
- **SC-002**: Guardar y cargar, retroceder y reconstruir con `historia`
  conservan exactamente el conocimiento en el 100 % de las pruebas.
- **SC-003**: El cálculo de un paso de «ir a» con el mapa completo de la cripta
  de referencia tarda ≤ 5 ms.
- **SC-004**: Las consultas al conocimiento mantienen el mismo costo al crecer
  el mapa conocido (medido con `--bench`).
- **SC-005**: Un `partida.log` con viajes se reproduce con el mismo resultado.

## Assumptions

- La antorcha, el pergamino y la activación de enemigos son los de la Parte I.
- El formato de guardado y la línea de tiempo los define la spec 005; esta spec
  define qué conocimiento hay que guardar y reconstruir.
- El contenido de la sala actual (enemigos, objetos, trampas) se sigue
  mostrando como en la Parte I; la niebla limita lo que se sabe del mapa.
- El costo de moverse es el de la spec 001.
