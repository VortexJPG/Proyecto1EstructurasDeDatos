# Implementation Plan: Niebla de guerra e «ir a»

**Branch**: `003-niebla-ir-a` | **Date**: 2026-11-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-niebla-ir-a/spec.md`

## Summary

El conocimiento del jugador se guarda en **dos arreglos de enteros pequeños**
indexados por posición: uno por sala (0 desconocida, 1 avistada, 2 explorada)
y uno por puerta (0 sin observar, 1 recuerda abierta, 2 recuerda cerrada).
Consultar es O(1). Explorar una sala cambia su casilla y marca como avistados
sus destinos todavía desconocidos: O(grado) por sala revelada, sin importar
cuánto mapa se conoce. Cada cambio de casilla se registra en el historial de
retroceso como un `CambioCasilla(arreglo, índice, valor_anterior)`, así el
pergamino lo invierte en O(1) por cambio; el conocimiento viaja en el estado
guardable (y por lo tanto en los puntos de control de la línea de tiempo)
como un texto compacto de un dígito por sala y por puerta.

«ir a» **comparte el motor de búsqueda** de la spec 001 (`BuscadorRutas`) con
otro filtro de salidas (salas exploradas y puertas recordadas abiertas) y una
instancia propia, para no pisar la caché de los cazadores. El controlador
ejecuta cada paso como un `MOVER` normal (precarga, línea de tiempo y
`partida.log` sin casos especiales) y escribe la orden como comentario.

## Technical Context

**Language/Version**: Python 3.11+.

**Primary Dependencies**: ninguna nueva.

**Storage**: campo `conocimiento` en `EstadoGuardable` (formato v3 de la
spec 005, binario y JSON).

**Testing**: `unittest`; pruebas de guardar/cargar, retroceso e `historia`
comparando el texto del conocimiento.

**Target Platform**: terminal y ventana; `--bench` sin vista.

**Performance Goals**: paso de «ir a» ≤ 5 ms con el mapa completo de la cripta
de referencia; consultas O(1).

**Constraints**: §6.2; determinismo; la vista solo muestra conocimiento.

**Scale/Scope**: hasta 10 000 salas en el bench.

## Constitution Check

| Principio | Cumplimiento | Evidencia |
|---|---|---|
| I. Estructuras a mano | PASA | Arreglos por índice; nada de `set` para "salas exploradas". |
| II. Determinismo | PASA | La exploración no usa el azar; el viaje usa el desempate de la spec 001. |
| III. MVC sin vista | PASA | El conocimiento y la ruta están en el modelo; la vista solo lee el "mapa conocido". |
| IV. Sin datos de cripta | PASA | |
| V. Presupuesto | PASA | Explorar con antorcha no pide contenido; la precarga sigue igual. |
| VI. Rendimiento con `--bench` | PASA | Consultas, exploración, retroceso y paso de «ir a» medidos. |
| VII. Spec antes que código | PASA | |

## Project Structure

```text
specs/003-niebla-ir-a/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/interfaz-a-b-conocimiento.md
├── checklists/requirements.md
└── tasks.md

cripta/
├── modelo/
│   ├── conocimiento.py   # NUEVO: ConocimientoMapa y MapaConocido (vista neutra)
│   ├── historial.py      # CambioCasilla
│   ├── juego.py          # revelar al entrar, observar puertas, antorcha,
│   │                     #   paso de «ir a», serializar/restaurar conocimiento
│   ├── efectos.py        # cerrar_puerta observa si el jugador está ahí
│   ├── guardable.py      # EstadoGuardable.conocimiento  [CONTRATO A↔B]
│   └── timeline.py       # resumen con el mapa conocido  (B, cambio acordado)
├── adaptadores/
│   ├── guardado.py       # codificar el campo conocimiento (B, cambio acordado)
│   └── bitacora_replay.py# comentario() y lectura que ignora "#" (B, cambio acordado)
├── controlador/
│   ├── comandos.py       # IR_A y MAPA            [CONTRATO A↔B]
│   └── controlador.py    # ir_a(): bucle de pasos y motivo de detención
└── vista/
    ├── base.py           # textos comunes del mapa conocido
    ├── vista_consola.py  # comandos "mapa" e "ir a N"; salidas según conocimiento
    └── vista_grafica.py  # tecla M (mapa) y G (ir a); salidas según conocimiento
cripta/bench/bench_rutas.py  # consultas al mapa conocido y paso de «ir a»
tests/test_niebla.py         # AC-003-01..06 y FR-001..FR-027
```

## Phase 0: Research

Ver [`research.md`](./research.md).

## Phase 1: Design & Contracts

- [`data-model.md`](./data-model.md).
- [`contracts/interfaz-a-b-conocimiento.md`](./contracts/interfaz-a-b-conocimiento.md):
  lo que A entrega a B (conocimiento en el estado, `serializar_conocimiento`,
  comentario en el log, `IR_A`/`MAPA`) y los cambios pequeños en archivos de B.

### Estructuras elegidas

| Problema | Estructura | Alternativa medida | Complejidad |
|---|---|---|---|
| Estado de una sala | Arreglo de enteros por `Sala.indice` | Lista de ids explorados con búsqueda lineal; `TablaOrdenada` | O(1) vs. O(k) vs. O(log k) |
| Puerta recordada | Arreglo de enteros por `Puerta.indice` | Igual que arriba | O(1) |
| Avistada | Se marca al explorar el origen (eager) | Calcularla en cada consulta mirando las entradas | O(1) consulta, O(grado) al explorar |
| Revertir | `CambioCasilla` en el historial existente | Copiar el conocimiento completo por acción | O(cambios) vs. O(V) |
| Ruta de «ir a» | `BuscadorRutas` compartido con el cazador, filtro propio, parada temprana al llegar al jugador | Búsqueda separada; Dijkstra con mínimo lineal | O((V'+E') log V') |

### Mediciones planificadas

- Consulta de estado de sala y de puerta: arreglo vs. lista lineal vs.
  `TablaOrdenada`, con 100, 1 000 y 10 000 salas conocidas.
- Explorar con antorcha: costo por sala revelada con mapa conocido pequeño y
  grande.
- Registrar y revertir la exploración de 5 salas.
- Paso de «ir a» con el mapa completo: cripta de referencia, 2 500 y 10 000
  salas (límite 5 ms), montículo vs. mínimo lineal.

## Re-evaluación de la Constitución (post-diseño)

PASA en los siete principios. Los cambios en archivos de B son mínimos y están
en el contrato.

## Complexity Tracking

Ninguna violación.

## Trazabilidad

| Requisitos | Decisión | Tareas |
|---|---|---|
| FR-001..FR-006 | R1, R2 | T004, T010, T011 |
| FR-007..FR-009 | R3 | T005, T012 |
| FR-010, FR-011 | R4 | T006, T013 |
| FR-012, FR-013 | R6 | T014, T015, T016 |
| FR-014..FR-016 | R5 | T007, T017, T018 |
| FR-017..FR-023, FR-026 | R7 | T008, T019, T020 |
| FR-024 | R8 | T009, T021 |
| FR-025 | R7 | T008 |
| FR-027 | R7 | T009 |
| NFR-001..NFR-005 | mediciones | T022, T023, T024 |
