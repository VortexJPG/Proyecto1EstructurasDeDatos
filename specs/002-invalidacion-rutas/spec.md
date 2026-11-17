# Feature Specification: Invalidación de rutas

**Feature Branch**: `002-invalidacion-rutas`

**Created**: 2026-11-15

**Status**: Clarified

**Input**: User description: "Entre dos turnos de un cazador pueden abrirse o cerrarse puertas, moverse el jugador y otros actores o cambiar velocidades. La decisión debe ser siempre la de un cálculo desde cero; reutilizar un cálculo anterior solo vale si no cambia la respuesta. Hay que medir cuánto se ahorra frente a recalcular siempre (Parte II, Persona A; §3.2 equivalencia observable, §5.2)."

## Clarifications

### Session 2026-11-15

- Q: ¿Qué cuenta como "la región que cubrió el cálculo anterior"? → A: Las salas cuyo costo mínimo hacia el jugador quedó determinado y no supera el alcance usado en ese cálculo. Una puerta "toca" la región si al menos una de sus dos salas pertenece a ella.
- Q: ¿Una puerta que se abre o se cierra fuera de esa región obliga a recalcular? → A: No. Ninguna ruta de costo dentro del alcance pasa por salas fuera de la región, así que la respuesta no cambia. Sí obliga si toca la región.
- Q: ¿El cálculo reutilizable es estado del juego? → A: No. Es información derivada: no se guarda en el archivo de partida, no se registra en el historial de retroceso ni en la línea de tiempo. Después de retroceder, cargar una partida o reconstruir un instante para `historia`, la siguiente decisión se calcula desde cero o se valida contra el estado restaurado.
- Q: ¿Un cazador que se activa con un rango mayor que el alcance usado invalida el cálculo? → A: Sí, para ese cazador: el cálculo anterior no alcanza y se rehace con un alcance suficiente. Uno con rango menor o igual lo puede reutilizar.
- Q: ¿Hace falta conservar el modo "recalcular siempre"? → A: Sí, como alternativa medible; debe producir exactamente la misma partida.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Decisiones siempre correctas aunque el mapa cambie (Priority: P1)

Como jugador, quiero que el cazador reaccione de inmediato cuando cierro una
puerta, me muevo o una puerta se cierra sola, sin seguir una ruta vieja.

**Why this priority**: es la regla de equivalencia observable de §3.2; una
decisión distinta a la de un cálculo desde cero es un error del juego.

**Independent Test**: simulaciones deterministas con puertas que cambian al
azar, comparando cada decisión con un cálculo de referencia desde cero.

**Acceptance Scenarios**:

1. **Given** un cazador siguiendo una ruta, **When** una puerta de esa ruta se
   cierra entre dos de sus turnos, **Then** en el turno siguiente decide como si
   calculara desde cero (otra ruta, o esperar si no queda ninguna).
   *(AC-002-01)*
2. **Given** un cazador persiguiendo al jugador, **When** el jugador cambia de
   sala, **Then** la siguiente decisión del cazador apunta a la sala nueva.
3. **Given** que se abrió una puerta que acortaba la ruta, **When** un pergamino
   revierte esa apertura, **Then** la siguiente decisión del cazador es la de un
   cálculo desde cero con la puerta otra vez cerrada.

---

### User Story 2 - No repetir trabajo que no cambia la respuesta (Priority: P1)

Como responsable del rendimiento, quiero reutilizar el cálculo de rutas entre
cazadores y entre turnos mientras nada relevante cambie, para que decenas de
cazadores quepan en el presupuesto de 20 ms.

**Why this priority**: sin reutilización, el costo crece con la cantidad de
cazadores y con los turnos; es la pregunta central de §5.2.

**Independent Test**: contar cuántos cálculos completos se hacen y cuántas
salas se examinan con puertas estables y con puertas inestables.

**Acceptance Scenarios**:

1. **Given** una puerta con cierre automático que se cierra lejos de todos los
   cazadores (fuera de la región del cálculo), **When** los cazadores vuelven a
   decidir, **Then** sus decisiones son las mismas y no se rehace el cálculo.
   *(AC-002-02)*
2. **Given** el jugador quieto y las puertas estables, **When** varios cazadores
   deciden en el mismo ciclo y en ciclos siguientes, **Then** se reutiliza un
   solo cálculo.
3. **Given** otros actores que se mueven, mueren o cambian de velocidad,
   **When** el cazador vuelve a decidir, **Then** no hace falta rehacer el
   cálculo (esos eventos no cambian las rutas).

---

### User Story 3 - Medir cuánto se ahorra de verdad (Priority: P2)

Como equipo, queremos comparar con datos la reutilización contra recalcular
siempre, con puertas que cambian mucho y con puertas que casi nunca cambian.

**Why this priority**: lo exige §5.2 y §6.3; sostiene la decisión en el
Documento de Decisiones.

**Independent Test**: `--bench` con los dos escenarios y las alternativas,
partidas idénticas en todos los modos.

**Acceptance Scenarios**:

1. **Given** la misma cripta, semilla y acciones, **When** se juega con
   reutilización y con "recalcular siempre", **Then** el estado final y el
   `partida.log` son idénticos. *(AC-002-03)*
2. **Given** un escenario de puertas estables y otro de puertas inestables,
   **When** se ejecuta `--bench`, **Then** se reportan tiempo, cálculos hechos,
   cálculos reutilizados y salas examinadas de cada alternativa.

---

### Edge Cases

- El jugador se mueve y vuelve a la misma sala dentro de un mismo ciclo.
- Se cierra una puerta que estaba en la región pero no en ninguna ruta usada:
  se acepta rehacer el cálculo (la regla es conservadora, nunca optimista).
- Una puerta se abre y se cierra en el mismo instante.
- Retroceso con un pergamino que restaura puertas y la sala del jugador.
- Cargar una partida guardada o reconstruir un instante para `historia`.
- Un cazador muere o se activa en medio de un ciclo.
- Cambio de velocidad de un cazador: cambia cuándo actúa, no hacia dónde.
- Cripta sin cazadores: no se hace ningún cálculo de rutas.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La decisión de cada cazador en cada turno MUST ser idéntica a la
  que daría un cálculo desde cero con el estado de ese instante.
- **FR-002**: Reutilizar un cálculo anterior MUST hacerse solo cuando los
  eventos ocurridos desde entonces no pueden cambiar la respuesta.
- **FR-003**: Los eventos que pueden cambiar la respuesta MUST invalidar lo que
  afectan: cambio de sala del jugador (todo el cálculo); apertura o cierre de
  una puerta que toca la región del cálculo; un cazador cuyo rango supera el
  alcance usado (solo para ese cazador).
- **FR-004**: Los movimientos y muertes de otros actores, los cambios de
  velocidad y el paso del tiempo sin cambios de puertas MUST NOT cambiar la
  decisión de un cazador más allá de su propia posición, y SHOULD NOT obligar a
  rehacer el cálculo.
- **FR-005**: La apertura o cierre de una puerta cuyas dos salas están fuera de
  la región del cálculo SHOULD NOT obligar a rehacerlo.
- **FR-006**: El cálculo reutilizable MUST NOT formar parte del estado del
  juego: no se guarda, no se revierte y no entra en la línea de tiempo. Tras un
  retroceso, una carga o una reconstrucción, la siguiente decisión MUST seguir
  cumpliendo FR-001.
- **FR-007**: La reutilización MUST NOT alterar el determinismo: la partida, el
  `partida.log` y el uso del generador aleatorio MUST ser idénticos con y sin
  reutilización.
- **FR-008**: Debe existir, para medir, la alternativa "recalcular siempre", y
  MUST producir exactamente la misma partida.
- **FR-009**: `--bench` MUST incluir un escenario donde las puertas cambian con
  frecuencia y otro donde casi nunca cambian, comparando reutilización contra
  recalcular siempre.
- **FR-010**: Las mediciones MUST reportar cuánto trabajo se ahorra: cálculos
  hechos, cálculos reutilizados y salas examinadas, además del tiempo.
- **FR-011**: Una cripta sin cazadores activos MUST NOT hacer cálculos de rutas.

### Performance Requirements

- **NFR-001**: El ciclo de eventos entre dos decisiones MUST quedar en
  **≤ 20 ms** en la cripta de referencia con decenas de cazadores (compartido
  con la spec 001).
- **NFR-002**: Con puertas estables, la reutilización MUST examinar menos salas
  que recalcular siempre; la diferencia se reporta con mediciones.
- **NFR-003**: Las mediciones MUST ser deterministas por semilla y reportar
  mediana.

### Key Entities

- **Cálculo de rutas**: costos mínimos hacia la sala del jugador para las salas
  dentro de un alcance, junto con el estado con el que se hizo.
- **Región del cálculo**: salas cuyo costo mínimo quedó determinado dentro del
  alcance.
- **Evento invalidante**: cambio que puede alterar una decisión (sala del
  jugador, puerta que toca la región, rango mayor que el alcance).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Los escenarios AC-002-01 a AC-002-03 quedan cubiertos por
  pruebas automatizadas que citan su ID.
- **SC-002**: En simulaciones aleatorias con puertas que cambian, el 100 % de
  las decisiones coincide con el cálculo desde cero en todas las alternativas.
- **SC-003**: Con puertas estables y el jugador quieto, la reutilización hace a
  lo sumo un cálculo por cambio relevante, y `--bench` muestra la reducción de
  salas examinadas frente a recalcular siempre.
- **SC-004**: El Documento de Decisiones incluye la tabla evento → información
  invalidada y las mediciones de los dos escenarios.

## Assumptions

- El comportamiento del cazador y el desempate son los de la spec 001.
- Las puertas solo cambian por las reglas del juego (abrir con llave, cierre
  automático) o por retroceso, carga o reconstrucción.
- Los actores no bloquean salidas, así que sus movimientos no cambian rutas.
