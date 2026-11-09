# Constitución del proyecto CRIPTA

<!--
  Borrador redactado por la Persona B a partir de la Parte II (§1.1 y §1.2)
  porque `.specify/` se inicializó sin constitución. La Persona A debe
  revisarlo y confirmarlo; cualquier cambio se hace con `/speckit.constitution`
  y en un commit propio.
-->

## Core Principles

### I. Estructuras implementadas a mano (NO NEGOCIABLE)

Las estructuras de datos de los problemas evaluados se implementan a mano.
Queda **prohibido** usar `dict` y `set` como índice, caché o tabla de búsqueda.
Quedan prohibidos `heapq`, `bisect`, `collections` (`deque`, `OrderedDict`,
`defaultdict`, `Counter`), `networkx` y cualquier biblioteca de grafos o de
búsqueda de rutas. Se permiten arreglos, listas enlazadas propias (simples y
dobles), pilas, colas propias, montículos y colas de prioridad, tablas hash
propias y búsqueda binaria propia. `list` se usa solo como almacenamiento
contiguo de bajo nivel. Cualquier plan o tarea que proponga una estructura
prohibida debe rechazarse antes de implementar.

### II. Determinismo

Misma cripta + misma semilla + mismas acciones ⇒ misma partida. Toda la
aleatoriedad usa un único generador con semilla; no se depende del reloj real
ni del orden de estructuras no ordenadas. Las salidas se recorren siempre en el
mismo orden (N, S, E, O) y las respuestas del servicio se incorporan en el
orden en que se solicitaron. El determinismo se verifica con dos corridas
idénticas.

### III. MVC sin vista en los modos no interactivos

`--replay`, `--bench` y `--verificar` **no** instancian la vista. El modelo no
conoce red, disco ni interfaz. La lógica de presentación no altera las reglas
del juego ni el estado.

### IV. Ningún dato de una cripta concreta en el código

Salas, ids, páginas, presupuestos, estadísticas y versión vienen siempre del
servicio o del paquete offline. El código no contiene constantes de una cripta
particular.

### V. Presupuesto de solicitudes

Toda consulta al servicio respeta `presupuesto_solicitudes`, incluida la
consulta de llaves. La precarga anticipada deja una reserva para lo
obligatorio. Agotar el presupuesto produce un error explícito, nunca un
resultado inventado.

### VI. Rendimiento respaldado con `--bench`

Toda afirmación de rendimiento se respalda con mediciones reproducibles:
semillas fijas, varias repeticiones y mediana o mínimo. Los límites son
configurables y no se escriben en el código. Cada decisión de estructura se
mide junto a una alternativa (idealmente la ingenua) y se compara.

### VII. La especificación precede a la implementación

Cada capacidad recorre `/speckit.specify` → `/speckit.clarify` →
`/speckit.plan` → `/speckit.tasks` → `/speckit.analyze` →
`/speckit.implement`, y su spec se confirma en Git **antes** del código. Si se
descubre que la spec estaba mal, primero se corrige la spec (commit separado) y
después el código (otro commit). Cada requisito tiene un ID estable (`FR-xxx`);
cada escenario de aceptación tiene al menos una prueba automatizada o un
`partida.log` que lo cita; cada tarea referencia sus requisitos. Un plan no
introduce reglas nuevas que no estén en la spec, y una spec no nombra
estructuras, clases ni módulos.

## Additional Constraints

- **Trazabilidad:** cada caso del Apéndice B es un escenario de aceptación y
  cada tarea de `tasks.md` referencia los `FR-xxx` que atiende.
- **Bitácora:** cada comando de spec-kit con texto propio y cada prompt
  significativo se registra en `PROMPTS_LLM.md` con el formato existente.
- **Git:** commits pequeños y atómicos (`spec(...)`, `plan(...)`, `feat(...)`,
  `test(...)`, `fix(spec): ...`). Se versionan `.specify/` y los comandos del
  agente.
- **Contratos A↔B:** los archivos marcados `[CONTRATO A↔B]` se pueden cambiar,
  pero avisando y en un commit aparte.
- **Datos de P1:** lo persistido por la Parte I se invalida por versión; un
  archivo de P1 se detecta como incompatible o se migra explícitamente, nunca
  se carga en silencio.

## Development Workflow

1. Explorar el estado del repositorio y confirmar la línea base antes de
   cambiar nada.
2. Escribir o corregir la spec y confirmarla en Git.
3. Planificar estructuras, alternativas y mediciones; rechazar las prohibidas.
4. Generar tareas pequeñas y verificables, cada una con su requisito y prueba.
5. Implementar una tarea a la vez, con su prueba, y medir mientras se
   implementa.
6. Ejecutar `--bench`, guardar los resultados y actualizar el Documento de
   Decisiones (`Decisiones_de_diseño.md`).
7. Auditar la trazabilidad requisito → escenario → tarea → código → prueba.

## Governance

Esta constitución prevalece sobre cualquier otra práctica del proyecto.
Cualquier enmienda requiere: propuesta escrita, aprobación de ambos
integrantes, actualización de la versión y registro en el commit
correspondiente. Si una enmienda cambia una regla del juego, se corrige primero
la spec afectada. Todas las revisiones verifican el cumplimiento de estos
principios; la complejidad añadida debe justificarse con mediciones.

**Version**: 1.0.0 | **Ratified**: 2026-11-09 | **Last Amended**: 2026-11-09
