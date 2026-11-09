# Feature Specification: Línea de tiempo e historia de la partida

**Feature Branch**: `005-linea-de-tiempo`

**Created**: 2026-11-09

**Status**: Clarified

**Input**: User description: "Consulta del estado de la partida en un instante pasado (`historia <t>` / `historia #k`), reconstrucción con puntos de control, recorte al usar un pergamino, reproducción `--replay … --hasta` y persistencia de la línea completa (Parte II, Persona B; §3.6, §5.5, §7.3)."

## Clarifications

### Session 2026-11-09

- Q: ¿Cómo se numeran las acciones `#k` después de usar un pergamino? → A: Se renumeran sobre la línea vigente: las acciones revertidas dejan de existir, así que la primera acción que queda es `#1`.
- Q: ¿Qué pasa con `historia #k` si k supera las acciones realizadas? → A: Se rechaza con un mensaje claro, igual que `historia <t>` con t posterior al reloj.
- Q: ¿Qué muestra `--hasta t` si t es posterior al final de la partida? → A: Muestra el estado final e indica que la partida terminó antes, con el motivo (victoria o derrota).
- Q: ¿Qué se ve del mapa conocido en un instante anterior a la primera exploración? → A: Solo lo conocido en ese instante; en `t = 0`, la sala inicial, sin salas exploradas de más.
- Q: ¿Los enemigos que se muestran son solo los vivos? → A: Se muestran los enemigos presentes en esa sala en ese instante, con su vida y si están activos o dormidos.
- Q: ¿El valor por defecto de K se fija en la spec? → A: No; se fija en el plan con mediciones de `--bench` y debe quedar justificado. La spec solo exige que sea configurable y que una consulta no aplique ni deshaga más de K acciones.
- Q: ¿Qué pasa con los puntos de control posteriores a un recorte por pergamino? → A: Se descartan; la línea vigente termina en el punto restaurado y los puntos posteriores ya no representan nada.
- Q: ¿Un archivo de partida de P1 puede cargarse? → A: No en silencio: se detecta como incompatible o se migra de forma explícita y avisada.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar el pasado de la partida (Priority: P1)

Como jugador, quiero escribir `historia <t>` o `historia #k` para ver cómo estaba la
partida en ese instante, sin alterar nada.

**Why this priority**: es la capacidad central y la base de los seis escenarios
del Apéndice B.

**Independent Test**: jugar unas acciones, consultar un instante anterior y
comprobar que se muestra el estado de ese momento; después verificar que el
reloj, la partida y el historial de retroceso no cambiaron.

**Acceptance Scenarios**:

1. **Given** una partida en curso, **When** se escribe `historia <t>` con un
   instante ya ocurrido, **Then** se muestra el estado después de todos los
   eventos con tiempo ≤ t.
2. **Given** una partida en curso, **When** se escribe `historia #k`, **Then**
   se muestra el estado justo antes de la acción número k del jugador.
3. **Given** una consulta, **When** termina, **Then** no consumió tiempo
   virtual, no se registró como acción y no cambió el historial de retroceso.

---

### User Story 2 - Rechazar consultas imposibles (Priority: P1)

Como jugador, quiero que se rechace una consulta a un instante futuro o a una
acción que no existe, para no obtener un estado inventado.

**Why this priority**: sin esta validación el resto de la línea no es confiable.

**Independent Test**: pedir `historia` con t mayor que el reloj y con `#k`
mayor que las acciones realizadas.

**Acceptance Scenarios**:

1. **Given** una partida con reloj R, **When** se pide `historia` con t > R,
   **Then** se rechaza con un mensaje claro. *(AC-005-01)*
2. **Given** una partida con n acciones, **When** se pide `historia #k` con
   k > n, **Then** se rechaza con un mensaje claro.

---

### User Story 3 - La línea respeta el pergamino (Priority: P1)

Como jugador, después de usar un pergamino quiero que las acciones revertidas
desaparezcan de la historia, para que la línea refleje la partida real.

**Why this priority**: una línea que muestre acciones revertidas contradice la
regla del retroceso y confunde al jugador.

**Independent Test**: realizar acciones, usar un pergamino y consultar el
pasado; las acciones revertidas no deben aparecer.

**Acceptance Scenarios**:

1. **Given** una partida con un pergamino usado, **When** se consulta
   `historia`, **Then** no aparecen las acciones revertidas. *(AC-005-02)*
2. **Given** la misma partida, **When** se pide un instante posterior al reloj
   actual, **Then** se rechaza. *(AC-005-01)*

---

### User Story 4 - Varios eventos en el mismo instante (Priority: P1)

Como jugador, quiero que `historia <t>` muestre el estado **después de todos**
los eventos de ese instante, no uno intermedio.

**Why this priority**: el reloj virtual puede ejecutar varios eventos con el
mismo tiempo; mostrar uno intermedio sería incorrecto.

**Independent Test**: construir una partida con varios eventos en el mismo
instante y consultarlo.

**Acceptance Scenarios**:

1. **Given** varios eventos con tiempo t, **When** se consulta `historia <t>`,
   **Then** se muestra el estado después de todos ellos. *(AC-005-03)*

---

### User Story 5 - Reproducir hasta un instante sin vista (Priority: P1)

Como revisor, quiero `--replay partida.log --hasta <t>` para obtener el mismo
resumen sin abrir la vista.

**Why this priority**: permite auditar una partida y comparar con la consulta
en vivo.

**Independent Test**: reproducir un log con y sin `--hasta`, comparar el
resumen con el de `historia <t>`.

**Acceptance Scenarios**:

1. **Given** un log de partida, **When** se ejecuta `--replay … --hasta t`,
   **Then** se imprime el mismo resumen que `historia <t>` y no se instancia la
   vista.
2. **Given** un t posterior al final del log, **When** se ejecuta `--hasta`,
   **Then** se muestra el estado final e indica que la partida terminó antes.
   *(AC-005-05)*

---

### User Story 6 - Guardar y cargar la línea (Priority: P1)

Como jugador, quiero que guardar y cargar conserve toda la línea de tiempo, y
que un archivo de la Parte I se detecte como incompatible.

**Why this priority**: sin persistencia la línea se pierde y la Parte II exige
no cargar archivos viejos en silencio.

**Independent Test**: guardar una partida con línea, cargarla y consultar
instantes anteriores; probar además un `.sav` de P1.

**Acceptance Scenarios**:

1. **Given** una partida guardada, **When** se carga, **Then** las consultas
   históricas siguen funcionando igual que antes de guardar.
2. **Given** un archivo de partida de P1, **When** se intenta cargar, **Then**
   se reporta incompatibilidad o se migra explícitamente; nunca se carga en
   silencio. *(AC-005-06)*

---

### User Story 7 - Puntos de control y rendimiento (Priority: P2)

Como responsable del rendimiento, quiero elegir K con mediciones para que una
consulta no aplique ni deshaga más de K acciones.

**Why this priority**: sostiene el límite de 50 ms y la memoria acotada.

**Independent Test**: medir consultas con ≥ 3 valores de K y sin puntos de
control; comparar memoria y tiempo.

**Acceptance Scenarios**:

1. **Given** una partida de 5000 acciones, **When** se consulta `historia` con
   el K por defecto, **Then** responde en ≤ 50 ms.
2. **Given** varios valores de K, **When** se comparan memoria y tiempo,
   **Then** el K por defecto queda justificado con datos.

---

### Edge Cases

- `historia 0` muestra el estado inicial (sala inicial, reloj 0).
- `historia` con t negativo se rechaza.
- Consulta en una partida terminada: se permite el pasado; el futuro se
  rechaza.
- Evento programado exactamente en t que es una decisión del jugador: se
  muestra el estado justo antes de la decisión.
- Acciones revertidas: no aparecen ni en `#k` ni en `<t>`.
- Puntos de control posteriores al recorte: se descartan.
- Carga de una partida con línea: se conserva y se puede seguir consultando.
- Presupuesto o red: una consulta histórica no hace solicitudes.
- Vista: `--replay --hasta` y las consultas históricas no instancian la vista.

## Requirements *(mandatory)*

### Functional Requirements

**Semántica de la línea**

- **FR-001**: La línea de tiempo MUST ser independiente del límite de 5
  acciones del pergamino y MUST NOT modificar la partida.
- **FR-002**: El estado en un instante t MUST ser el estado después de ejecutar
  todos los eventos con tiempo ≤ t.
- **FR-003**: Si a t le corresponde una decisión del jugador, el estado
  MOSTRADO MUST ser el de justo antes de tomarla.
- **FR-004**: `historia <t>` MUST mostrar el estado en t y `historia #k` el
  estado justo antes de la k-ésima acción del jugador.
- **FR-005**: La consulta MUST mostrar, como mínimo: reloj, sala del jugador,
  vida y estadísticas, inventario, efectos activos, enemigos de esa sala con su
  vida y el mapa conocido en ese instante.
- **FR-006**: Una consulta MUST NOT consumir tiempo virtual.
- **FR-007**: Una consulta MUST NOT registrarse como acción ni escribirse en la
  bitácora de partida.
- **FR-008**: Una consulta MUST NOT alterar el estado de la partida ni el
  historial de retroceso.
- **FR-009**: Se MUST rechazar `historia <t>` con t posterior al reloj actual o
  negativo, y `historia #k` con k fuera del rango de acciones vigentes.
- **FR-010**: La consulta MUST funcionar también con la partida terminada,
  siempre que el instante sea pasado.

**Pergamino y recorte**

- **FR-011**: Las acciones revertidas por un pergamino MUST dejar de existir en
  la línea.
- **FR-012**: Tras un recorte, las acciones vigentes MUST renumerarse desde 1.
- **FR-013**: Los puntos de control posteriores al recorte MUST descartarse.
- **FR-014**: Consultar un instante posterior al reloj actual tras un recorte
  MUST rechazarse.

**Puntos de control y reconstrucción**

- **FR-015**: Se MUST guardar como máximo un punto de control cada K acciones
  del jugador; K MUST configurarse con `--checkpoint-cada K`.
- **FR-016**: Una consulta MUST NOT requerir aplicar ni deshacer más de K
  acciones.
- **FR-017**: Fuera de los puntos de control solo se MUST almacenar la
  información necesaria para reconstruir los cambios (deltas).
- **FR-018**: El punto de control MUST incluir el estado del generador aleatorio
  si la reconstrucción vuelve a simular.
- **FR-019**: La decisión de reconstruir hacia adelante (re-simular) o hacia
  atrás (invertir) MUST documentarse con evidencia.
- **FR-020**: La memoria total MUST ser proporcional a los cambios registrados
  más un punto de control cada K acciones; MUST NOT ser
  acciones × tamaño del estado.
- **FR-021**: El valor por defecto de K MUST justificarse con mediciones de
  memoria y tiempo para al menos 3 valores de K y para la alternativa sin
  puntos de control.

**Consulta sin interacción**

- **FR-022**: `--replay partida.log --hasta <t>` MUST reproducir hasta t e
  imprimir el mismo resumen que la consulta en vivo `historia <t>`.
- **FR-023**: `--replay … --hasta` MUST NOT instanciar la vista.
- **FR-024**: Si t es posterior al final del log, se MUST mostrar el estado
  final e indicar que la partida terminó antes, con el motivo.

**Persistencia**

- **FR-025**: Guardar y cargar MUST conservar la línea completa, incluidos
  puntos de control y deltas.
- **FR-026**: El formato binario MUST llevar una versión de formato.
- **FR-027**: Un archivo de partida de la Parte I MUST detectarse como
  incompatible o migrarse de forma explícita y avisada; MUST NOT cargarse en
  silencio.
- **FR-028**: La copia JSON de comparación MUST llevar también la versión de
  formato y la misma detección de incompatibilidad.
- **FR-029**: Una partida cargada MUST poder seguir registrando y consultando
  su línea desde el punto cargado.

**Conocimiento y determinismo**

- **FR-030**: El estado mostrado MUST incluir el conocimiento del jugador
  (mapa conocido) en ese instante, usando la interfaz acordada con la Persona A.
- **FR-031**: La línea MUST ser determinista: mismas acciones y semilla ⇒ misma
  historia y mismos estados reconstruidos.
- **FR-032**: La línea MUST registrar también lo que ocurre entre decisiones
  (turnos enemigos, efectos, eventos) para que el estado en t sea exacto.

### Performance Requirements

- **NFR-001**: Una consulta `historia` MUST responder en **≤ 50 ms** con una
  partida de ≥ 5000 acciones del jugador y el K por defecto.
- **NFR-002**: La memoria MUST cumplir FR-020.
- **NFR-003**: Se MUST medir con al menos 3 valores de K y con la alternativa
  sin puntos de control, con semillas fijas y varias repeticiones.
- **NFR-004**: Los límites y tamaños de las mediciones MUST ser configurables.
- **NFR-005**: Para muchos valores de t y de K, el estado reconstruido por
  `historia t` MUST ser idéntico al obtenido re-simulando desde cero hasta t
  (oráculo).

### Key Entities

- **Evento**: algo que ocurre en un instante del reloj virtual; varios pueden
  compartir tiempo.
- **Acción del jugador**: decisión que avanza la partida; se numera en la línea
  vigente.
- **Estado**: reloj, jugador, sala, vida, estadísticas, inventario, efectos,
  enemigos presentes y conocimiento del mapa.
- **Cambio (delta)**: información mínima para aplicar o invertir una mutación
  entre dos estados.
- **Punto de control**: copia completa del estado en una acción múltiplo de K,
  con el estado del generador aleatorio.
- **Línea de tiempo**: secuencia vigente de acciones, cambios y puntos de
  control, recortable por el pergamino.
- **Resumen histórico**: lo que se imprime para `historia` y `--hasta`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Los seis escenarios del Apéndice B (AC-005-01 a AC-005-06) quedan
  cubiertos por pruebas automatizadas o por un `partida.log` que los cita.
- **SC-002**: `historia` no consume reloj, no escribe en `partida.log` y no
  modifica el historial de retroceso; se comprueba comparando el estado
  completo antes y después.
- **SC-003**: El estado reconstruido coincide con el oráculo de re-simulación
  para muchos valores de t y de K.
- **SC-004**: La consulta de 5000 acciones responde en ≤ 50 ms con el K por
  defecto, o la desviación se documenta con mediciones.
- **SC-005**: La memoria sigue la forma de FR-020 y se compara contra la
  alternativa sin puntos de control.
- **SC-006**: `--replay … --hasta` imprime el mismo resumen que `historia` y no
  abre la vista.
- **SC-007**: Un archivo de P1 no se carga en silencio y lo persistido se
  invalida por versión.

## Assumptions

- La Persona A entrega el registro e inversión de los cambios de conocimiento
  del mapa y su serialización; hasta entonces se usa la interfaz mínima con un
  doble de prueba.
- El reloj virtual y la agenda de eventos existentes son la fuente de verdad de
  los instantes.
- Los deltas cubren todas las mutaciones registradas en el historial de
  retroceso, más el conocimiento del jugador.
- El formato de partida actual es v2; la Parte II sube a v3 y un archivo v2 se
  reporta incompatible (o se migra explícitamente).
- Las mediciones se hacen con criptas sintéticas deterministas y sin red.
- La vista solo imprime el resumen; no calcula la reconstrucción.
