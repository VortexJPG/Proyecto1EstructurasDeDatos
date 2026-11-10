# Estado — Persona B (CRIPTA Parte II)

> Bitácora de trabajo para retomar el contexto. Actualizar al cerrar cada fase
> y siempre que se tome una decisión que afecte a la Persona A.

## Fase actual

**Fase 7/8 — mediciones, Documento de Decisiones y cierre.** Specs 004 y 005
implementadas salvo los puntos que dependen de la Persona A.

## Avance (2026-11-10)

| Spec | Tareas hechas | Pendientes | % |
|---|---:|---:|---:|
| 004 Resolubilidad | 48 / 49 | 1 (coordinación con A) | 98.0 % |
| 005 Línea de tiempo | 49 / 56 | 7 (A) | 87.5 % |
| **Total** | **97 / 105** | **8** | **92.4 %** |

Pendientes: `T048` (acordar la interfaz con A), `T016`/`T030..T032`
(`avanzar_hasta` de A) y `T053`, `T054`, `T056` (conocimiento del mapa y caso
cruzado con A).

## Hecho

- Auditoría del repositorio de P1 completada (módulos, contratos, pruebas,
  `--bench`, Swagger).
- **spec-kit v1.3.2 instalado, verificado e inicializado:**
  `specify check` detecta `opencode (available)`; `specify init --here
  --integration opencode` creó `.specify/` y `.opencode/commands/speckit.*.md`
  sin modificar archivos existentes. La constitución quedó redactada
  (v1.0.0) con los 7 principios del documento, **pendiente de revisión por A**.
- **Spec 004 creada** en `specs/004-resolubilidad-llaves/spec.md`
  (FR-001..FR-024, NFR-001..NFR-005, SC-001..SC-007, los 4 escenarios del
  Apéndice B) y clarificada el 2026-11-09. Checklist en
  `specs/004-resolubilidad-llaves/checklists/requirements.md`.
- **Plan, research, modelo de datos, contratos, quickstart y 49 tareas**
  generados en `specs/004-resolubilidad-llaves/`; `analyze` sin huecos de
  cobertura (FR/NFR/SC mapeados).
- **Contrato de llaves implementado** (`T003..T006`, `T008`): `UbicacionLlave`
  y `RespuestaLlaves`, `FuenteDatos.llaves()`, `ClienteHTTP`, `FuenteOffline`,
  `AlmacenCripta.guardar_llaves/cargar_llaves` con validación de versión y
  pruebas de contrato/offline/almacén.
- **Preparación ligera y caché de llaves** (`T007`):
  `preparar_verificacion` carga datos + esqueleto + llaves sin catálogo,
  contenido ni precarga; `obtener_llaves` usa memoria → disco → servicio.
- **Generador sintético determinista** (`T009`, `T010`) en
  `cripta/bench/sinteticos.py`: llaves encadenadas, costos, puertas
  cambiantes, lado extra, llave en errante y variante no resoluble.
- **Oráculo ingenuo** (`T011`) en `tests/test_resolubilidad.py`, con pruebas
  de la condición estricta de `sala_salida`.
- **Costo de salida (parte B, `T046`)**: `DatosSalida.costo` se lee y se
  persiste; falta que A lo consuma en el movimiento.
- **Verificador incremental** (`T012..T029`): `cripta/modelo/verificacion.py`
  con recorrido único, orden determinista, frontera sin duplicados, llaves
  inobtenibles con ubicaciones y ciclo concreto; `--verificar` sin vista ni
  replay.
- **Bloqueo de inicio** (`T030..T034`): sin `--forzar` una cripta no resoluble
  no inicia (código 3, sin replay); con `--forzar` inicia mostrando la
  advertencia. El reporte se muestra al iniciar y queda disponible en el
  controlador. `preparar_cripta` reutiliza datos y mapa tras verificar.
- **Datos offline**: `llaves.json` agregado a las cuatro criptas de
  `datos_ejemplo/` con las ubicaciones del contenido local.
- **US4 y bench** (`T035..T045`):
  - orden válido y determinista (dos corridas idénticas, desempate por id);
  - `--bench resolubilidad` con salas y K crecientes, mediana de 7 repeticiones
    y límites configurables por entorno;
  - evidencia en `docs/mediciones/p2_resolubilidad.txt`;
  - en 5000 salas el incremental se mantiene en ~13–17 ms para K = 5..80,
    mientras el ingenuo pasa de ~11 a ~59 ms (cruce alrededor de K ≈ 20);
  - 300 salas: ~0.9 ms, muy por debajo de los 200 ms.
- **Validación contra el servicio real** (2026-11-09):
  - `cripta-02` → RESOLUBLE (bronce, negra).
  - `cripta-05` → NO RESOLUBLE con ciclo `hierro → negra → hierro`.
  - `cripta-06` (300 salas) → RESOLUBLE; verificación ≈ **1.8 ms** de mediana.
- **134/134 pruebas en verde**; el replay de la línea base sigue reproduciendo
  la misma victoria.
- **Spec 004 implementada** salvo las tareas de A (`T047..T049`).
- **Spec 005 (línea de tiempo) creada y clarificada** en
  `specs/005-linea-de-tiempo/spec.md`: 7 historias, FR-001..FR-032,
  NFR-001..NFR-005, SC-001..SC-007 y los 6 escenarios del Apéndice B
  (`AC-005-01..06`). Checklist en `checklists/requirements.md`.
- **Plan y 56 tareas de la spec 005** en `specs/005-linea-de-tiempo/`:
  reconstrucción hacia adelante desde checkpoints (≤ K acciones), búsqueda
  binaria propia, recorte por pergamino, persistencia v3 y detección de P1.
  `analyze` sin huecos de cobertura (FR/NFR/SC mapeados).
- **Base de la línea de tiempo implementada** (`T003..T015`, `T026..T029`,
  `T037..T041`): `cripta/modelo/timeline.py` con acciones, contenido nuevo,
  checkpoints cada K, búsqueda binaria del checkpoint, reconstrucción en mapa
  propio con fichas de solo lectura y resumen histórico; `--checkpoint-cada`;
  recorte por pergamino; formato binario/JSON v3 con la línea completa y
  rechazo explícito de archivos v2/P1.
- **143/143 pruebas en verde**; guardar/cargar conserva la línea y el replay
  de P1 sigue idéntico.
- **Comando `historia <t>|#k`** (`T017..T025`): el controlador reconstruye sin
  tocar la partida, la consola lo parsea y muestra el resumen; rechaza
  instantes futuros/negativos y acciones fuera de rango. **150/150 pruebas**.
- **`--replay … --hasta T`** (`T033..T036`): mismo resumen que `historia T`,
  sin vista; si T es posterior al final, muestra el final e indica el motivo.
- **Bench de la línea** (`T042..T047`): 5000 acciones, K ∈ {10, 25, 50, 100} y
  sin checkpoints. Consulta: 0.41 / 0.59 / 0.81 / 1.13 ms y **99 ms** sin
  checkpoints; memoria de checkpoints: 2.95 / 1.16 / 0.58 / 0.29 MB. **K = 50
  por defecto** (0.81 ms, 0.58 MB), muy por debajo de 50 ms. Evidencia en
  `docs/mediciones/p2_timeline.txt`.
- **156/156 pruebas en verde**.
- **Documento de Decisiones**: §5.4 (resolubilidad, incremental vs. ingenuo),
  §5.5 (línea de tiempo, K = 50) y §5.6-B (historial de retroceso antes/después)
  añadidos a `Decisiones_de_diseño.md`.
- **Trazabilidad** de FR/NFR/SC y `AC-004-01..04` / `AC-005-01..06` en
  `docs/trazabilidad-persona-b.md`.
- **Parte B de `rango`/`cazador`**: `Ficha.rango` se lee y persiste, y el
  comportamiento `cazador` se transporta; el comportamiento en sí sigue siendo
  de A.
- **Preparación de defensa** en `docs/defensa-persona-b.md`: resumen de las
  specs 004/005, recorrido de trazabilidad de dos requisitos, ensayo de cambio
  de regla y checklist §8.
- **158/158 pruebas en verde**.
- **Historia en la ventana**: tecla `V`, entrada de texto para `t` o `#k` y
  panel del resumen; **160/160 pruebas**.
- `.gitattributes` con `text=auto eol=lf` (commit `ec25931`).
- Paquete renombrado de `Cripta/` a `cripta/` para Linux/WSL (commit `6d8117b`).
- `.venv` con `requests` y `pygame-ce` 2.5.8: **91/91 pruebas en verde**.
- Línea base guardada:
  - `docs/mediciones/p1_linea_base.txt` (salida completa de `--bench`).
  - `docs/mediciones/p1_partida_cripta-02_semilla3.log` (victoria, 53
    acciones, reloj 3575; se reproduce con `--replay`).

## Decisiones de la auditoría

- Se normaliza a LF para que los commits sean atómicos (§1.4).
- El paquete se llama en minúsculas (`cripta`) porque los imports ya lo hacían
  así y el sistema de archivos de Linux distingue mayúsculas.
- Se deja `pygame-ce` instalado en `.venv`; la consola, `--replay`, `--bench`
  y `--verificar` no lo necesitan.

## Hallazgos que afectan a la Persona A

Interfaces que hay que acordar antes de implementarlas (no tocar módulos de A
sin avisar):

| Punto | Qué necesita B de A | Qué entrega B |
|---|---|---|
| Costo de salida | `Salida`/`Puerta` deben exponer `costo` y `Juego._mover` usarlo en vez de `COSTO_MOVER` | `DatosSalida.costo` leído del esqueleto (`None` → 100) |
| Enemigo cazador | `Comportamiento.desde_texto` debe aceptar `"cazador"` y la IA debe implementarlo | `Ficha.rango` leído del catálogo |
| Comando historia | La vista debe parsear `historia <t>` / `historia #k` | `TipoComando.HISTORIA` y su despacho en el controlador |
| Persistencia | `Juego.exportar_estado` / `Juego.desde_estado` deben incluir línea de tiempo y conocimiento | Formato binario v3 con detección explícita de P1 |
| Pergamino | El recorte de la línea al retroceder | Registro de deltas y puntos de control |

## Riesgos abiertos

- `Juego._mover` devuelve siempre `COSTO_MOVER = 100`: hoy el campo `costo`
  del servicio se descarta en silencio (`DatosSalida` no lo tiene).
- `Comportamiento.desde_texto("cazador")` lanza `ValueError`: cualquier ficha
  P2 con cazador rompe la carga hasta que A lo implemente.
- El guardado JSON de comparación no tiene envoltura de versión; hay que
  impedir que un archivo de P1 se cargue en silencio.
- El `--replay` actual solo conoce `version_cripta` y `version_catalogo`; no
  hay `--hasta`.
- `datos_ejemplo/` es de P1: sin `costo`, sin `rango`, sin `llaves.json`, sin
  criptas 05/06 y con versiones viejas de 02/03/04.
- `historia <t>` con t **entre dos decisiones** necesita `Juego.avanzar_hasta`
  (interfaz A); hasta entonces se rechaza en vez de devolver un estado
  incorrecto. `historia #k` y los instantes de decisión sí funcionan.
- La precarga asíncrona puede incorporar contenido en momentos distintos; el
  resumen usa salas visitadas, así que la historia jugable no cambia, pero una
  comparación byte a byte del estado completo puede diferir en
  `contenido_cargado` de salas no visitadas.

## Comandos

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python main.py --bench
.venv/bin/python main.py --offline --replay docs/mediciones/p1_partida_cripta-02_semilla3.log
```

## Siguiente

1. `T030..T032` / `AC-005-03`: instantes entre decisiones; requiere
   `Juego.avanzar_hasta(t)` (A).
2. `T053`, `T054`, `T056`: conocimiento del mapa y caso cruzado
   pergamino/antorcha (A).
3. `T048`: acordar con A la interfaz de `costo`/`rango`/`cazador`.

Todo lo demás de la Parte B está cerrado.
