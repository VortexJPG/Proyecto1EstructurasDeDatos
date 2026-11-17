# Feature Specification: Fin de partida y cripta no resoluble en la interfaz

**Feature Branch**: `006-fin-de-partida`

**Created**: 2026-11-17

**Status**: Clarified

**Input**: User description: "Que el juego no se cierre al ganar o morir: ofrecer reintentar la misma cripta o salir. Y que, al elegir en la lista una cripta que no se puede ganar, la interfaz muestre el reporte y deje elegir otra en lugar de cerrarse (Persona A, interfaz; complementa §3.5 y el Apéndice B)."

## Clarifications

### Session 2026-11-17

- Q: ¿Reintentar usa la misma semilla? → A: Solo si se fijó con `--semilla`; si no, cada partida elige una nueva, igual que al abrir el programa.
- Q: ¿Reintentar vuelve a preguntar el nombre? → A: No; usa el mismo nombre.
- Q: ¿Qué pasa si el jugador sale a mitad de partida? → A: El programa termina como antes, sin ofrecer reintentar: solo se ofrece al ganar o al morir.
- Q: ¿Qué pasa con una cripta no resoluble indicada con `--cripta`? → A: No hay lista a la que volver: se muestra el reporte y el programa termina con código 3 (AC-004-04 sin cambios).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Volver a intentar sin reiniciar el programa (Priority: P1)

Como jugador, cuando gano o muero quiero poder jugar otra vez la misma cripta o salir, en vez de que el programa se cierre solo.

**Why this priority**: es lo que más se nota al jugar varias partidas seguidas.

**Independent Test**: terminar una partida (victoria o derrota) en la ventana y en la terminal, y elegir cada opción.

**Acceptance Scenarios**:

1. **Given** una partida que terminó en derrota, **When** se elige «Reintentar», **Then** empieza una partida nueva en la misma cripta desde la sala inicial, con 0 acciones, sin preguntar el nombre. *(AC-006-01)*
2. **Given** una partida que terminó en victoria, **When** se elige «Salir», **Then** el programa termina. *(AC-006-02)*
3. **Given** la ventana, **When** aparece la pantalla final, **Then** hay dos botones: «Reintentar» a la izquierda y «Salir» a la derecha, que se eligen con las flechas y Enter, con un clic, con R o con Esc. *(AC-006-03)*
4. **Given** una partida en curso, **When** el jugador decide salir, **Then** el programa termina sin ofrecer reintentar. *(AC-006-04)*

---

### User Story 2 - Entender por qué una cripta no empieza (Priority: P1)

Como jugador, si elijo en la lista una cripta que no se puede ganar, quiero ver el reporte en la misma interfaz y poder elegir otra, en vez de que la ventana se cierre de golpe.

**Why this priority**: el Apéndice B pide que se muestre el reporte; antes, en la ventana, solo quedaba en la terminal de atrás y parecía que el programa se había caído.

**Independent Test**: elegir en la lista una cripta no resoluble, ver el reporte, cerrarlo y elegir otra cripta.

**Acceptance Scenarios**:

1. **Given** la lista de criptas, **When** se elige una no resoluble sin `--forzar`, **Then** la partida no inicia, se muestra el reporte (veredicto, llaves inobtenibles, frontera y ciclo) y, al cerrarlo, se vuelve a la lista. *(AC-006-05)*
2. **Given** `--cripta` con una cripta no resoluble y sin `--forzar`, **When** se inicia el programa, **Then** se muestra el reporte y el programa termina con código 3. *(AC-006-06)*

---

### Edge Cases

- Se elige otra vez la misma cripta no resoluble: se vuelve a mostrar el reporte.
- Se cierra la ventana en la pantalla final o en el reporte: el programa termina.
- Reintentar después de gastar casi todo el presupuesto: lo ya descargado sale de disco.

## Requirements *(mandatory)*

### Functional Requirements

**Fin de partida**

- **FR-001**: Al terminar una partida por victoria o derrota, la interfaz MUST ofrecer «Reintentar» o «Salir» en lugar de cerrar el programa.
- **FR-002**: «Reintentar» MUST empezar una partida nueva en la misma cripta desde su estado inicial, con el mismo nombre de jugador; la semilla es nueva salvo que se haya fijado con `--semilla`.
- **FR-003**: «Reintentar» SHOULD reutilizar los datos y el contenido ya descargados, sin volver a gastar solicitudes en lo que ya está en disco.
- **FR-004**: Cada partida MUST registrar su propio puntaje y su propio `partida.log`.
- **FR-005**: «Salir» MUST terminar el programa.
- **FR-006**: Si el jugador sale a mitad de partida, el programa MUST terminar sin ofrecer reintentar.
- **FR-007**: En la ventana, la pantalla final MUST mostrar dos botones, «Reintentar» a la izquierda y «Salir» a la derecha, que se puedan elegir con el teclado y con el ratón.
- **FR-008**: En la terminal, la interfaz MUST preguntar `[R] Reintentar  [S] Salir`.

**Cripta no resoluble**

- **FR-009**: Si una cripta elegida de la lista no es resoluble y no se usó `--forzar`, la interfaz MUST mostrar el reporte de resolubilidad (spec 004, FR-008, FR-010 y FR-013) en la misma interfaz, esperar a que el jugador lo cierre y volver a la lista; la partida MUST NOT iniciar.
- **FR-010**: Si la cripta se indicó con `--cripta`, el programa MUST mostrar el reporte y terminar con código 3.
- **FR-011**: La lista de criptas MUST pedirse al servicio una sola vez por ejecución.

**General**

- **FR-012**: Estas pantallas MUST NOT cambiar reglas, reloj ni determinismo; `--replay`, `--bench` y `--verificar` no las usan.

### Key Entities

- **Pantalla final**: resumen de la partida con la opción elegida (reintentar o salir).
- **Reporte de resolubilidad**: el de la spec 004.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Los escenarios AC-006-01 a AC-006-06 tienen pruebas automatizadas que citan su id.
- **SC-002**: Ninguna prueba existente cambia de resultado.

## Assumptions

- El reporte y el veredicto los calcula la spec 004; esta spec solo define cómo los muestra la interfaz.
- El código de salida 3 de `--cripta` con una cripta no resoluble se mantiene (spec 004).
