# CRIPTA

Proyecto de Estructuras de Datos — II Ciclo 2026. Juego de mazmorra dirigido por un reloj virtual de eventos (§2.3), que se juega en la terminal o en una ventana con sprites pixel art.

## Documentos

| Documento | Qué tiene |
|---|---|
| [Decisiones_de_diseño.md](Decisiones_de_diseño.md) | Documento de Decisiones de Diseño (§8): qué estructura de datos usamos para cada problema, por qué y con qué mediciones |
| [PROMPTS_LLM.md](PROMPTS_LLM.md) | Bitácora de uso de LLM (§10.3) |
| [PLAN_DE_TRABAJO.md](PLAN_DE_TRABAJO.md) | División del trabajo entre los integrantes y registro de los cambios grandes |

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
python main.py --verificar cripta-05    # verificar resolubilidad sin iniciar partida
python main.py --cripta cripta-05 --forzar  # iniciar aunque no sea resoluble
python main.py --bench                  # mediciones por subsistema + frecuencia de operaciones
python main.py --bench resolubilidad    # incremental vs. repetido por llave
python main.py --bench timeline         # historia: tiempo y memoria para varios K
python main.py --bench agenda           # solo las mediciones que contienen "agenda"
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

También hay comandos con palabras: `sig` y `ant` (mover el cursor del inventario), `ordenar peso|valor|nombre`, `retroceder`, `historia <t>|#k`, `guardar`, `cargar`, `puntajes`, `ayuda` y `salir`.

### En la ventana (`--gui`)

Las mismas letras, sin Enter. Cuando hay que elegir (por ejemplo, a qué rata atacar), aparece un menú y una flecha amarilla señala en la sala la opción marcada. Se elige con las flechas y Enter, con el número o con un clic; Esc cancela.

| Tecla | Acción |
|---|---|
| `W` `A` `S` `D` / `Q` `E` `R` `F` `T` | igual que en la terminal |
| `Arriba` / `Abajo` | mover el cursor del inventario |
| `I` | cambiar el orden del inventario: real, peso, valor, nombre |
| `Z` | usar un pergamino de retroceso |
| `V` | ver la historia: escribe `120` o `#4` y Enter |
| `F5` / `F9` | guardar / cargar la partida |
| `P` | tabla de puntajes |
| `L` | ver la bitácora completa (los últimos 20 mensajes) |
| `F1` | ver los controles |
| `Esc` | salir |

Los sprites están dibujados en el código (`cripta/vista/sprites.py`): cada uno es una cuadrícula de 16 x 16 caracteres, uno por pixel. No usan imágenes ni recursos de terceros.

**Turnos en pantalla:** después de cada acción, la bitácora separa lo que hiciste (**Tu turno**) de todo lo que pasó hasta tu siguiente decisión (**Turno de los enemigos**). Por dentro, el juego sigue el reloj virtual del enunciado: un enemigo rápido puede actuar más de una vez en el turno de los enemigos.

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
- `historia <t>` con t **entre dos decisiones** se rechaza con un mensaje claro
  hasta integrar `Juego.avanzar_hasta` de la Persona A; los instantes de
  decisión y `historia #k` funcionan.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

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
datos_ejemplo/       respuestas reales de las 4 criptas publicadas, para jugar y medir sin red
tests/               pruebas con unittest
```
