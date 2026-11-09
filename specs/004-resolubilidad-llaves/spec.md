# Feature Specification: Resolubilidad y llaves

**Feature Branch**: `004-resolubilidad-llaves`

**Created**: 2026-11-09

**Status**: Clarified

**Input**: User description: "Verificación de resolubilidad de una cripta antes de iniciar la partida, reporte de bloqueos y consulta de la ubicación de llaves mediante el servicio (Parte II, Persona B; §3.5, §4.2, §5.4)."

## Clarifications

### Session 2026-11-09

- Q: ¿Qué ocurre si el mismo id de llave aparece en dos ubicaciones? → A: La llave es obtenible si al menos una ubicación es alcanzable; la ubicación reportada se elige de forma determinista (menor sala).
- Q: ¿Qué se hace si una puerta requiere una llave que no aparece en la consulta, o si falta `llave_salida`? → A: Se reporta como no obtenible y la cripta como no resoluble, indicando la llave faltante y la puerta.
- Q: ¿Qué pasa si la sala inicial de un enemigo que porta una llave es inalcanzable? → A: La llave no es obtenible; se reporta el enemigo y su sala inicial.
- Q: ¿«Llegar a `sala_salida` por una puerta que la requiere» exige una entrada con llave? → A: Sí, la condición es estricta: debe existir una salida hacia `sala_salida` que requiera `llave_salida`; llegar por una salida libre no basta.
- Q: ¿En qué orden se consulta el servicio y qué pasa si se agota el presupuesto? → A: Primero se obtienen los datos generales (que fijan el presupuesto) y después las llaves; si se agota, se informa un error claro y no se emite veredicto.
- Q: ¿Cómo se comporta `--forzar` y qué pasa con un cierre automático sin llave? → A: `--forzar` inicia la partida y mantiene el reporte disponible; un cierre automático sin llave no bloquea la verificación.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Verificar una cripta sin jugarla (Priority: P1)

Como jugador, quiero ejecutar `--verificar <cripta>` y obtener un veredicto
claro sobre si la cripta puede ganarse, sin entrar a la partida ni perder
tiempo explorando.

**Why this priority**: es la forma directa de comprobar una cripta publicada y
la base de la revisión del Apéndice B. Sin esto, el jugador descubre que la
cripta es imposible solo después de jugarla.

**Independent Test**: ejecutar el comando sobre una cripta conocida (resoluble
y no resoluble) y comprobar que imprime el veredicto y que no se abre ninguna
interfaz interactiva.

**Acceptance Scenarios**:

1. **Given** una cripta resoluble, **When** se ejecuta `--verificar <cripta>`,
   **Then** se informa "resoluble" junto con un orden de obtención de llaves.
2. **Given** una cripta no resoluble, **When** se ejecuta `--verificar
   <cripta>`, **Then** se informa "no resoluble" con el reporte de bloqueos.
3. **Given** cualquier cripta, **When** se ejecuta `--verificar`, **Then** no
   se instancia la vista y no se escribe en la bitácora de partida.

---

### User Story 2 - No iniciar una partida imposible (Priority: P1)

Como jugador, si la cripta no es resoluble quiero que la partida **no inicie**
y ver el reporte, salvo que use `--forzar`.

**Why this priority**: evita partidas condenadas y cumple la regla de §3.5.

**Independent Test**: iniciar una partida sobre una cripta no resoluble con y
sin `--forzar`, y comprobar que sin la bandera no se crea la partida.

**Acceptance Scenarios**:

1. **Given** una cripta no resoluble, **When** se inicia una partida sin
   `--forzar`, **Then** la partida no inicia y se muestra el reporte.
   *(AC-004-04)*
2. **Given** la misma cripta, **When** se inicia con `--forzar`, **Then** la
   partida inicia y el reporte sigue disponible.

---

### User Story 3 - Entender por qué una cripta no se puede ganar (Priority: P1)

Como autor de criptas, cuando una cripta no es resoluble quiero ver qué llaves
no pueden obtenerse, qué puertas forman la frontera bloqueada y, si existe, el
ciclo concreto de dependencias.

**Why this priority**: el reporte es lo que permite corregir el contenido y es
la evidencia exigida por el Apéndice B.

**Independent Test**: verificar una cripta construida con una llave detrás de
su propia puerta y comprobar que el reporte nombra el ciclo.

**Acceptance Scenarios**:

1. **Given** una cripta donde `llave_salida` está detrás de la única puerta
   que ella misma abre, **When** se verifica, **Then** el veredicto es no
   resoluble y el reporte **señala el ciclo concreto**. *(AC-004-01)*
2. **Given** una cripta no resoluble, **When** se verifica, **Then** el reporte
   lista las llaves inobtenibles, las puertas de la frontera bloqueada con su
   llave, y la ubicación de cada llave inobtenible.

---

### User Story 4 - Obtener un orden de llaves reproducible (Priority: P2)

Como jugador, cuando la cripta es resoluble quiero un orden de obtención donde
cada llave aparezca después de las necesarias para alcanzarla, y que dos
ejecuciones produzcan el mismo orden.

**Why this priority**: da una guía útil y garantiza el determinismo exigido;
puede entregarse después de las historias P1.

**Independent Test**: verificar dos veces la misma cripta con varios órdenes
válidos y comparar las salidas.

**Acceptance Scenarios**:

1. **Given** una cripta con más de un orden válido, **When** se verifica dos
   veces con las mismas entradas, **Then** las dos ejecuciones producen el
   mismo orden. *(AC-004-03)*

---

### User Story 5 - Conocer dónde está cada llave (Priority: P1)

Como cliente del servicio, quiero consultar la ubicación de las llaves de una
cripta para poder verificar su resolubilidad, respetando el presupuesto de
solicitudes y la versión de la cripta.

**Why this priority**: sin la ubicación de llaves no se puede verificar nada;
además, la consulta cuenta en el presupuesto.

**Independent Test**: consultar las llaves de una cripta publicada y comprobar
que se obtiene una ubicación por llave, incluidas las que suelta un enemigo.

**Acceptance Scenarios**:

1. **Given** una llave en el campo `suelta` de un enemigo errante que inicia en
   la sala X, **When** se consulta la ubicación de llaves, **Then** la llave se
   ubica en la **sala inicial del enemigo** (X). *(AC-004-02)*
2. **Given** una cripta con versión nueva, **When** cambia la versión, **Then**
   la respuesta de llaves guardada deja de usarse y se vuelve a consultar.

---

### Edge Cases

- Llave duplicada: el mismo id aparece en dos salas. ¿Vale con que una sea
  alcanzable? (Decisión: sí.)
- Puerta cerrada que requiere una llave que no aparece en la consulta de
  llaves: se considera no obtenible y la cripta no resoluble.
- Llave que suelta un enemigo cuya sala inicial es inalcanzable: la llave no es
  obtenible; se reporta el enemigo y su sala inicial.
- `llave_salida` no aparece en la consulta de llaves: la cripta es no
  resoluble, con motivo explícito.
- Salida con `llave` pero que empieza abierta: se considera abierta; la llave
  solo importa si la puerta empieza cerrada.
- Trampas y cierres automáticos: no bloquean la verificación porque la puerta
  puede reabrirse con la misma llave.
- Presupuesto agotado antes de consultar las llaves: se informa un error
  explícito, no un veredicto.
- Verificación sin red (`--offline`): funciona si el paquete local incluye la
  información de llaves.
- `--verificar` sin id de cripta: es un error de uso.

## Requirements *(mandatory)*

### Functional Requirements

**Verificación**

- **FR-001**: El sistema MUST determinar si una cripta es resoluble antes de
  iniciar una partida, usando el esqueleto y la ubicación de sus llaves.
- **FR-002**: La verificación MUST permitir atravesar cualquier salida abierta
  y cualquier salida cerrada cuya llave ya se haya obtenido.
- **FR-003**: La verificación MUST asumir que las llaves no se consumen, que
  todo enemigo puede ser derrotado y que una llave soltada por un enemigo es
  obtenible en la sala donde ese enemigo inicia.
- **FR-004**: La verificación MUST asumir que trampas y cierres automáticos no
  bloquean, porque la puerta puede reabrirse con la misma llave.
- **FR-005**: Una cripta MUST considerarse resoluble solo si, partiendo de la
  sala inicial, se puede obtener `llave_salida` y llegar a `sala_salida` por
  una puerta que requiera `llave_salida`. Llegar por una salida libre no
  satisface esta condición.
- **FR-006**: Si la cripta es resoluble, el sistema MUST devolver un orden de
  obtención de llaves donde cada llave aparezca después de todas las
  necesarias para alcanzarla.
- **FR-007**: El orden de obtención MUST ser determinista para las mismas
  entradas.
- **FR-008**: Si la cripta no es resoluble, el reporte MUST incluir las llaves
  inobtenibles, las puertas cerradas de la frontera bloqueada con la llave que
  requiere cada una, y la ubicación de cada llave inobtenible.
- **FR-009**: Si una llave está detrás de puertas que solo ella abre,
  directamente o por cadena de llaves, el reporte MUST señalar el ciclo
  concreto.
- **FR-010**: Una cripta no resoluble MUST impedir el inicio de la partida,
  salvo que se use `--forzar`.
- **FR-011**: `--forzar` MUST permitir iniciar la partida y conservar
  accesible el reporte de no resolubilidad.
- **FR-012**: `--verificar <cripta>` MUST ejecutar solo la verificación,
  imprimir el reporte y no instanciar la vista ni escribir en la bitácora de
  partida.
- **FR-013**: El resultado de la verificación MUST mostrarse al iniciar la
  partida.
- **FR-014**: El veredicto y el orden MUST NOT depender de datos de una cripta
  concreta escritos en el código.
- **FR-015**: La verificación MUST poder ejecutarse sin red cuando el paquete
  local contiene la información de llaves.

**Llaves y servicio**

- **FR-016**: El sistema MUST obtener la ubicación de las llaves desde el
  servicio, con una entrada por llave que indique `id`, `sala` y, si aplica,
  `enemigo`.
- **FR-017**: Si la ubicación incluye `enemigo`, el sistema MUST interpretar
  que la llave está en el campo `suelta` de esa instancia y que `sala` es la
  sala inicial del enemigo.
- **FR-018**: La información de llaves persistida MUST invalidarse cuando
  cambie la versión de la cripta, usando la validación de versión existente.
- **FR-019**: La consulta de llaves MUST contar dentro de
  `presupuesto_solicitudes`.
- **FR-020**: Si el presupuesto se agota, el sistema MUST informar un error
  explícito y MUST NOT emitir un veredicto.
- **FR-021**: La respuesta de llaves MAY persistirse y reutilizarse mientras
  coincida la versión de la cripta.
- **FR-022**: Si una puerta requiere una llave que no aparece en la respuesta,
  el sistema MUST reportarla como no obtenible y la cripta como no resoluble.
- **FR-023**: Si `llave_salida` no aparece en la respuesta, el sistema MUST
  reportar la cripta como no resoluble con ese motivo.
- **FR-024**: Si una llave aparece en varias ubicaciones, el sistema MUST
  considerarla obtenible cuando al menos una ubicación sea alcanzable, y MUST
  elegir la ubicación reportada de forma determinista.

### Key Entities

- **Cripta**: definición publicada con versión; contiene salas, una sala
  inicial, una sala de salida, la llave de salida y un presupuesto de
  solicitudes.
- **Sala**: espacio identificado por un número, con salidas hacia otras salas.
- **Salida**: conexión dirigida entre dos salas; puede empezar cerrada, exigir
  una llave y cerrarse sola tras abrirse.
- **Llave**: objeto identificado por un tipo; abre una o más puertas y no se
  consume.
- **Ubicación de llave**: sala donde se puede obtener una llave; si la suelta
  un enemigo, se indica la instancia y vale la sala inicial de ese enemigo.
- **Reporte de resolubilidad**: veredicto, orden de llaves si es resoluble, y
  para el caso negativo las llaves inobtenibles, la frontera bloqueada, las
  ubicaciones y el ciclo concreto cuando exista.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Los cuatro escenarios del Apéndice B (AC-004-01 a AC-004-04)
  quedan cubiertos por pruebas automatizadas que citan su ID.
- **SC-002**: Dos verificaciones de la misma cripta y versión producen el mismo
  veredicto y el mismo orden de llaves en el 100 % de las ejecuciones.
- **SC-003**: El reporte de no resolubilidad incluye siempre frontera, llaves
  inobtenibles, ubicaciones y ciclo concreto cuando aplica.
- **SC-004**: La verificación de la cripta publicada más grande (hoy 300 salas)
  termina en **≤ 200 ms** en el equipo de referencia, o la desviación queda
  documentada con mediciones.
- **SC-005**: El veredicto y el conjunto de llaves obtenibles coinciden con una
  verificación ingenua en criptas sintéticas pequeñas deterministas.
- **SC-006**: `--verificar` no abre interfaz interactiva y no añade líneas a la
  bitácora de partida.
- **SC-007**: Ninguna consulta excede `presupuesto_solicitudes`, incluida la de
  llaves.

## Assumptions

- La consulta de llaves se hace después de conocer los datos generales de la
  cripta, porque de ahí sale el presupuesto.
- La verificación usa el estado inicial del esqueleto (qué puertas empiezan
  cerradas), no el estado de una partida en curso.
- El servicio es la fuente autoritativa del contrato; no se inventan campos ni
  rutas.
- Las criptas de la Parte II tienen versiones nuevas; lo persistido por la
  Parte I se invalida por versión.
- El campo `costo` de las salidas y la ficha de enemigo con `rango` pertenecen
  a la spec 001 de la Persona A; esta spec solo consume `/llaves`.
- El comportamiento del enemigo cazador y la ruta más barata quedan fuera de
  esta capacidad.
- El equipo dispone de un paquete local actualizado para probar `--offline`.
