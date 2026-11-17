# CRIPTA

Proyecto de Estructuras de Datos — II Ciclo 2026. Juego de mazmorra dirigido por un reloj virtual de eventos (§2.3), que se juega en la terminal o en una ventana con sprites pixel art.

## Documentos

| Documento | Qué tiene |
|---|---|
| [DECISIONES.md](DECISIONES.md) | Documento de Decisiones de Diseño (P1 §8 y P2 §7.1): qué estructura de datos usamos para cada problema, por qué y con qué mediciones |
| [PROMPTS_LLM.md](PROMPTS_LLM.md) | Bitácora de uso de LLM (§10.3), incluidos los comandos de spec-kit con texto propio |
| [PLAN_DE_TRABAJO.md](PLAN_DE_TRABAJO.md) | División del trabajo entre los integrantes y registro de los cambios grandes |
| [.specify/memory/constitution.md](.specify/memory/constitution.md) | Constitución del proyecto (principios que siguen todas las specs) |
| [specs/](specs/) | Una carpeta por capacidad con `spec.md`, `plan.md`, `research.md`, `tasks.md`: 001 terreno y cazador, 002 invalidación de rutas, 003 niebla e «ir a» (Persona A); 004 resolubilidad, 005 línea de tiempo (Persona B); 006 fin de partida en la interfaz (Persona A) |
| [docs/mediciones/](docs/mediciones/) | Salidas guardadas de `--bench` que respaldan el Documento de Decisiones |

## Desarrollo con spec-kit (Parte II)

- **Versión:** GitHub spec-kit **v1.3.2** (la misma para todo el grupo).
- **Agentes:** opencode (Persona B, specs 004 y 005) y Claude Code (Persona A, specs 001, 002 y 003). Los comandos `/speckit.*` instalados en el repositorio son los de opencode (`.opencode/commands/`); la Persona A siguió las mismas plantillas de `.specify/templates/`.
- **Instalación** (solo para volver a generar los archivos de spec-kit; el juego no la necesita):

  ```bash
  uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v1.3.2
  specify init --here --ai opencode
  ```

- **Flujo por capacidad:** `/speckit.specify` → `/speckit.clarify` → `/speckit.plan` → `/speckit.tasks` → `/speckit.analyze` → `/speckit.implement`. Cada requisito tiene un id estable (`FR-xxx`), cada caso del Apéndice B es un escenario `AC-00N-xx` y cada prueba cita el requisito que ejercita.

> **Estado:** jugable en la terminal y en una ventana (`--gui`). Por defecto usa la API del curso; con `--offline` juega sin red con los datos de `datos_ejemplo/`.

## Requisitos

- Python 3.11 o superior.
- `requests`, para la API (para jugar con `--offline` no hace falta).
- `pygame-ce`, solo para la ventana (`--gui`). La terminal, `--replay` y `--bench` funcionan sin él.

Las dos se instalan juntas con `requirements.txt`:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS
pip install -r requirements.txt
```

## Cómo jugar

```bash
python main.py                          # partida en la terminal con la API del curso
python main.py --gui                    # partida en una ventana con sprites (pygame-ce)
python main.py --gui --offline          # ventana, sin red
python main.py --cripta cripta-02       # saltar la selección de cripta (ahorra una solicitud)
python main.py --semilla 7 --nombre Ana # semilla y nombre fijos
python main.py --offline                # sin red, con datos_ejemplo/ (las 4 criptas publicadas)
python main.py --offline DIRECTORIO     # sin red, con otro paquete de respuestas guardadas
python main.py --replay ARCHIVO.log     # reproducir una partida sin interacción
python main.py --replay ARCHIVO.log --hasta 1200  # historia en el instante 1200, sin vista
python main.py --checkpoint-cada 25     # punto de control cada 25 acciones (defecto: 50)
python main.py --offline datos_ejemplo_p2 --cripta cripta-06  # cripta de referencia de la Parte II, sin red
python main.py --verificar cripta-05    # verificar resolubilidad sin iniciar partida
python main.py --cripta cripta-05 --forzar  # iniciar aunque no sea resoluble
python main.py --bench                  # mediciones por subsistema + frecuencia de operaciones
python main.py --bench resolubilidad    # incremental vs. repetido por llave
python main.py --bench timeline         # historia: tiempo y memoria para varios K
python main.py --bench agenda           # solo las mediciones que contienen "agenda"
python main.py --bench cazador          # ruta del cazador: 1 vs. muchos, rango, compartido vs. individual
python main.py --bench invalidacion     # reutilizar vs. recalcular, puertas estables e inestables
python main.py --bench ciclo            # ciclo entre decisiones (incluye la cripta de referencia, límite 20 ms)
python main.py --bench mapa_conocido    # consultas y exploración del mapa conocido
python main.py --bench ir_a             # paso de «ir a» con el mapa completo (límite 5 ms)
python main.py --cache-size 25          # fichas de catálogo en memoria
python main.py --datos DIRECTORIO       # dónde guardar caché, partidas, logs y puntajes
```

### En la terminal

Escribe la letra y presiona Enter:

| Tecla | Acción |
|---|---|
| `W` `A` `S` `D` | moverse al norte, oeste, sur y este |
| `Q` | atacar (si hay varios enemigos, pregunta a cuál; también `Q 2`) |
| `E` | recoger un objeto del suelo (también `E 2`) |
| `R` | abrir una puerta con llave (también `R D` para la del este) |
| `F` | usar, equipar o soltar el objeto que estás viendo (o `F 3`); pregunta qué hacer |
| `T` | esperar |
| `I` | ver el inventario |

Al ganar o morir, la terminal pregunta `[R] Reintentar  [S] Salir` en vez de cerrar el programa.

También hay comandos con palabras: `sig` y `ant` (mover el cursor del inventario), `ordenar peso|valor|nombre`, `retroceder`, `mapa` (mapa conocido), `ir a <sala>` (viaje automático), `historia <t>|#k`, `guardar`, `cargar`, `puntajes`, `ayuda` y `salir`.

### En la ventana (`--gui`)

Las mismas letras, sin Enter. Cuando hay que elegir (por ejemplo, a qué rata atacar), aparece un menú y una flecha amarilla señala en la sala la opción marcada. Se elige con las flechas y Enter, con el número o con un clic; Esc cancela.

| Tecla | Acción |
|---|---|
| `W` `A` `S` `D` / `Q` `E` `R` `F` `T` | igual que en la terminal |
| `Arriba` / `Abajo` | mover el cursor del inventario |
| `I` | cambiar el orden del inventario: real, peso, valor, nombre |
| `Z` | usar un pergamino de retroceso |
| `V` | ver la historia: escribe `120` o `#4` y Enter |
| `M` | ver el mapa conocido |
| `G` | «ir a»: escribe el número de una sala explorada y Enter |
| `F5` / `F9` | guardar / cargar la partida |
| `P` | tabla de puntajes |
| `L` | ver la bitácora completa (los últimos 20 mensajes) |
| `F1` | ver los controles |
| `Esc` | salir |
| Al ganar o morir | botones **Reintentar** (izquierda: otra partida en la misma cripta) y **Salir** (derecha: cierra el programa) |

Los sprites están dibujados en el código (`cripta/vista/sprites.py`): cada uno es una cuadrícula de 16 x 16 caracteres, uno por pixel. No usan imágenes ni recursos de terceros.

**Turnos en pantalla:** después de cada acción, la bitácora separa lo que hiciste (**Tu turno**) de todo lo que pasó hasta tu siguiente decisión (**Turno de los enemigos**). Por dentro, el juego sigue el reloj virtual del enunciado: un enemigo rápido puede actuar más de una vez en el turno de los enemigos.

## Terreno, cazadores, niebla de guerra e «ir a» (Parte II, Persona A)

- **Terreno:** cada salida tiene un costo (100 si el servicio no lo trae). Moverse cuesta ese costo para todos los actores: `max(1, costo * 100 // velocidad)`. La sala actual muestra el costo de cada salida.
- **Cazador:** enemigo que, en su turno, ataca si comparte sala con el jugador. Si no, calcula la ruta más barata hasta él por salidas abiertas; si no hay ruta o cuesta más que su `rango`, espera, y si no, avanza una sala (empate: la vecina de menor id). En pantalla aparece como `[cazador, rango N]` (en la ventana, con una "C" morada).
- **Niebla de guerra:** solo se muestran las salas exploradas (con nombre, salidas, costos y la puerta como se vio la última vez). Una sala avistada aparece como "sala sin explorar". Con la antorcha encendida, al entrar a una sala también quedan exploradas sus vecinas, sin despertar a sus enemigos ni activar sus trampas. Lo que se sabe del mapa se guarda con la partida, se deshace con el pergamino y aparece en `historia`.
- **`mapa`** (tecla `M`): salas exploradas, sus salidas y cuántas salas hay avistadas.
- **`ir a <sala>`** (tecla `G`): viaja por la ruta más barata **que conoces**, sin abrir puertas. Se detiene al llegar, al entrar a una sala con enemigos, al recibir daño o si ya no hay ruta conocida, y te dice por qué. Cada paso es un movimiento normal: cuenta tiempo, va al `partida.log` (la orden queda como comentario `# ir a N`) y el pergamino deshace solo el último paso.
- **Datos de la Parte II sin red:** `datos_ejemplo_p2/` tiene las respuestas reales de `cripta-05` (no resoluble) y `cripta-06` (la de referencia: 300 salas y 36 cazadores).

## Resolubilidad y llaves

Antes de iniciar una partida el juego consulta `GET /criptas/<id>/llaves`
(cuenta en `presupuesto_solicitudes` y se guarda por versión) y verifica si la
cripta puede ganarse.

- `python main.py --verificar cripta-05` imprime el reporte y sale con `0`
  (resoluble) o `3` (no resoluble); no abre la vista ni escribe `partida.log`.
- Sin `--forzar`, una cripta no resoluble **no inicia**.
- `--forzar` permite jugarla y muestra el reporte con una advertencia.
- El reporte incluye el orden de llaves, las llaves inobtenibles, la frontera
  bloqueada y el ciclo concreto cuando existe.
- `--bench resolubilidad` mide el verificador incremental contra la
  alternativa ingenua (repetir el recorrido por llave) con tamaños y cantidad
  de llaves crecientes. `CRIPTA_BENCH_SALAS`, `CRIPTA_BENCH_LLAVES`,
  `CRIPTA_BENCH_REPS` y `CRIPTA_LIMITE_VERIFICACION_MS` ajustan la medición.

## Historia de la partida

- `historia <t>` muestra el estado después de todos los eventos con tiempo ≤ t.
- `historia #k` muestra el estado justo antes de la k-ésima acción vigente.
- La consulta **no** consume reloj, **no** escribe en `partida.log` y **no**
  altera el historial de retroceso.
- Tras usar un pergamino, las acciones revertidas desaparecen y `#k` se
  renumera.
- `--replay ARCHIVO.log --hasta T` imprime el mismo resumen sin abrir la vista;
  si T es posterior al final, muestra el estado final e indica que la partida
  terminó antes.
- Los puntos de control se toman cada K acciones (`--checkpoint-cada`); el
  valor por defecto es 50 y está justificado en
  `docs/mediciones/p2_timeline.txt`.
- Guardar/cargar conserva la línea completa. Un archivo de la Parte I se rechaza
  como incompatible.
- `historia <t>` con t **entre dos decisiones** re-simula la acción anterior
  hasta t (después de todos los eventos con tiempo ≤ t).

## Pruebas

```bash
python -m unittest discover -s tests -v
```

Las pruebas de aceptación citan su requisito (`001/FR-012`, `AC-003-02`, ...). Por capacidad:

| Spec | Pruebas |
|---|---|
| 001 terreno y cazador | `python -m unittest tests.test_terreno_cazador -v` |
| 002 invalidación de rutas | `python -m unittest tests.test_invalidacion -v` |
| 003 niebla de guerra e «ir a» | `python -m unittest tests.test_niebla -v` |
| 004 resolubilidad y llaves | `python -m unittest tests.test_resolubilidad -v` |
| 005 línea de tiempo | `python -m unittest tests.test_timeline -v` |
| 006 fin de partida y cripta no resoluble en la interfaz | `python -m unittest tests.test_reintentar -v` |
| Contratos entre A y B | `python -m unittest tests.test_interfaz_a_b -v` |
| Requisitos de medición y límites de §6.1 (A) | `python -m unittest tests.test_bench_rutas -v` |
| Partidas al azar en las 6 criptas (robustez) | `python -m unittest tests.test_robustez -v` |

Las pruebas de la ventana se saltan si `pygame-ce` no está instalado.

Cada spec de la Persona A tiene su matriz de trazabilidad (requisito → escenario → tarea → código → prueba): [001](specs/001-terreno-cazador/trazabilidad.md), [002](specs/002-invalidacion-rutas/trazabilidad.md) y [003](specs/003-niebla-ir-a/trazabilidad.md).

## Archivos generados

Todos se guardan dentro de `datos_locales/` (o del directorio de `--datos`).

| Qué | Dónde |
|---|---|
| Caché persistente del catálogo | `catalogo/` (una ficha por archivo + `version.txt`) |
| Esqueleto y contenido de cada cripta | `<id de cripta>/` |
| Bitácoras de replay | `replays/partida_<cripta>_<fecha>.log` (una por partida) |
| Partida guardada (binario propio) | `partida_guardada.sav` + copia `.json` para comparar |
| Tabla de puntajes | `puntajes.json` |

## Estructura

```
main.py
cripta/
  constantes.py      reglas fijas del juego (§2)
  estructuras/       estructuras de datos propias (§7)
  modelo/            reglas del juego; no conoce red, disco ni vista
  adaptadores/       red, --offline, disco, guardado, replay, puntajes
  controlador/       orquestación, precarga, replay, argumentos
  vista/             consola y ventana (sprites en sprites.py)
  bench/             --bench
datos_ejemplo/       respuestas reales de las 4 criptas de la Parte I, para jugar y medir sin red
datos_ejemplo_p2/    respuestas reales de cripta-05 y cripta-06 (referencia de la Parte II)
specs/               specs de spec-kit (spec, plan, research, tasks) de cada capacidad
docs/mediciones/     salidas guardadas de --bench
tests/               pruebas con unittest
```
