# Plan de trabajo — CRIPTA

El trabajo se divide en dos mitades con **poco acoplamiento** entre ellas. Se tocan solo en unos pocos archivos de *contrato* que ya están definidos en el esqueleto.

| | **Persona A — Motor del juego** | **Persona B — Datos, red y persistencia** |
|---|---|---|
| Idea | Todo lo que pasa *dentro* de la partida | Todo lo que entra y sale de la partida |
| Capas MVC | Modelo + Vista | Adaptadores + Controlador |
| Enunciado | §2 completo, §4.1, §4.5, §4.6, §4.7, §4.8, §5.2, §10.2 | §3, §4.2, §4.3, §4.4, §4.9, §4.10, §4.11, §5.1, §5.3, §6, §10.1 |
| Rúbrica (§11) | Juego funcional (20 %), retroceso, rendimiento del ciclo | Cliente y presupuesto de red (25 %), caché, persistencia, mediciones |
| Documento de Decisiones | Secciones §4.1, §4.5, §4.6, §4.7, §4.8 | Secciones §4.2, §4.3, §4.4, §4.9, §4.10, §4.11 |

Cada archivo dice en su primera línea quién es el responsable: `[Persona A]`, `[Persona B]` o `[CONTRATO A↔B]`.

---

## Persona A — Motor del juego

**Estructuras propias**
- `estructuras/monticulo.py`: `MonticuloMin` (agenda de eventos).
- `estructuras/lista_doble.py`: `ListaDoble` (inventario, enemigos y objetos de cada sala).
- `estructuras/buffer_circular.py`: `BufferCircular` (últimos 20 mensajes y últimos 5 intervalos de retroceso).

**Modelo**
- `modelo/eventos.py`: `Agenda` con cancelación y reprogramación.
- `modelo/actores.py`, `modelo/objetos.py`, `modelo/mapa.py`: jugador, enemigos, objetos, trampas, salas, puertas y rastro.
- `modelo/inventario.py`: cursor, soltar en O(1), mover al frente y vistas ordenadas.
- `modelo/efectos.py`: veneno, velocidad, antorcha, regeneración, trampas y cierre de puertas.
- `modelo/comportamiento.py`: guardián, errante y rastreador.
- `modelo/historial.py`: pergaminos de retroceso (bitácora de deshacer).
- `modelo/mensajes.py`: bitácora en pantalla.
- `modelo/juego.py`: la fachada y el bucle de eventos.
- `constantes.indice_direccion`.

**Otros**
- `vista/vista_consola.py`: la interfaz de consola.
- `bench/bench_modelo.py`: agenda, ciclo de §5.2 (< 20 ms), inventario, historial, rastreadores y bitácora.

## Persona B — Datos, red y persistencia

**Estructuras propias**
- `estructuras/tabla_ordenada.py`: `TablaOrdenada` y `ConjuntoOrdenado` (arreglo ordenado + búsqueda binaria), el reemplazo de `dict` en todo el proyecto. Reemplazó a `TablaHash` el 2026-10-15 (ver la última sección).
- `estructuras/cola.py`: `ColaEnlazada` (BFS de precarga y solicitudes pendientes en orden).
- `estructuras/ordenamiento.py`: inserción, mezcla, selector automático y búsqueda binaria.
- `estructuras/lru.py`: `CacheAcotada` con desalojo y fijado.

**Contratos (la parte de B)**
- `modelo/datos.py`: todos los `desde_json`.
- `modelo/acciones.py`: `a_linea` y `desde_linea`.

**Adaptadores**
- `adaptadores/fuente_datos.py`, `cliente_http.py`, `fuente_offline.py`: red con `X-Cripta-Client-Id`, manejo de 429 y presupuesto, y modo `--offline`.
- `adaptadores/almacen_disco.py`, `cache_catalogo.py`: caché persistente y resolución de catálogo por lotes.
- `adaptadores/guardado.py`: guardado binario propio, con JSON para comparar.
- `adaptadores/bitacora_replay.py`, `puntajes.py`.

**Controlador**
- `controlador/precarga.py`: precarga por lotes con orden determinista.
- `controlador/controlador.py`, `replay.py`, `aplicacion.py`: orquestación, `--replay` y banderas.

**Otros**
- `bench/runner.py`, `bench/sinteticos.py`, `bench/bench_datos.py`.
- `README.md`.

## Los dos
- `PROMPTS_LLM.md`: cada quien agrega sus prompts.
- Revisar las secciones del Documento que escribió el otro. En la defensa **cualquiera** puede tener que explicar **cualquier** decisión (§9).
- Pruebas de sus propias estructuras (se recomienda una carpeta `tests/` con `unittest`).

> Si una mitad avanza más rápido, la pieza más fácil de mover es la **vista de consola**: puede pasar de A a B sin tocar nada más.

---

## Orden sugerido

| Fase | Persona A | Persona B |
|---|---|---|
| **0. Arranque** (juntos) | Crear el repo en GitHub, subir este esqueleto y leer juntos los archivos `[CONTRATO]` | ← |
| **1. Estructuras base** + pruebas | `MonticuloMin`, `ListaDoble`, `BufferCircular`, `indice_direccion` | `TablaHash`, `ConjuntoHash`, `ColaEnlazada`, los `desde_json` de `datos.py` y `FichasEnMemoria` |
| **2. Núcleo por separado** | `Agenda`, `Mapa`, actores, `Juego` (mover, atacar, esperar y bucle), IA, rastro y vista mínima. Se prueba con `datos_ejemplo/` + `FichasEnMemoria`, sin red | `ClienteHTTP` (429 y presupuesto), `FuenteOffline`, almacenes, `CacheAcotada`, `CacheCatalogo`, `ordenamiento` y `aplicacion.py` |
| **3. Integración** | Atender lo que pida B en `Mapa.vecinos`, `incorporar_contenido` y la API de `Juego` | `Controlador`, `PlanificadorPrecarga` y `EscritorReplay`. Meta: jugar cripta-01 de punta a punta |
| **4. Completar** | Inventario completo con vistas ordenadas, efectos, historial/retroceso y `exportar_estado` / `desde_estado` | Guardado binario + JSON, `ReproductorReplay`, puntajes, `runner` y `sinteticos.generar_cripta` |
| **5. Evidencia** | `bench_modelo` + sus secciones del Documento | `bench_datos` + sus secciones del Documento + README |

### Qué necesita cada uno del otro (y cuándo)

| Quién lo necesita | Qué | Fase |
|---|---|---|
| A ← B | `TablaHash` (el modelo no puede usar `dict`) | 1 |
| A ← B | `desde_json` de `datos.py` y `FichasEnMemoria`, para probar con `datos_ejemplo/` | 1 |
| A ← B | `ordenamiento.ordenar` (vistas del inventario y orden de activación de enemigos) | 2 |
| B ← A | `ListaDoble` (la usa `CacheAcotada`) | 1 |
| B ← A | `Mapa.construir`, `Mapa.vecinos`, `Mapa.incorporar_contenido` y `Juego.ejecutar_accion` | 3 |
| B ← A | `Juego.exportar_estado` y `Juego.desde_estado` | 4 |

---

## Puntos de integración delicados

1. **Antes de mover.** El controlador pregunta `juego.sala_destino(dir)` y llama a `precarga.asegurar(sala)`, que trae el contenido y resuelve sus fichas. Recién entonces llama a `juego.ejecutar_accion`. Si el modelo responde `requiere_sala`, se asegura esa sala y se reintenta.
2. **Fijar y liberar fichas.** A decide *cuándo* (entrar o salir de una sala, recoger, soltar, morir, retroceder) y B decide *cómo* (`CacheCatalogo.fijar` / `liberar`). Si esto queda incoherente, la caché desaloja fichas en uso.
3. **Retroceso.** Toda mutación del estado del juego pasa por `Juego._asignar` (u otro helper que registre un `Cambio`). Los pergaminos y la caché quedan fuera.
4. **Determinismo**, sin el cual el replay deja de funcionar:
   - Toda aleatoriedad usa `juego.azar` (`random.Random(semilla)`).
   - Las salidas se recorren siempre en el orden N, S, E, O.
   - El juego decide recorriendo sus propias listas (salidas, enemigos de la sala, esqueleto), no las tablas de búsqueda. Las tablas (`TablaOrdenada`) igual se recorren siempre en el mismo orden, porque están ordenadas por clave.
   - Las respuestas HTTP se incorporan en el orden en que se solicitaron, y la incorporación no consume azar ni números de secuencia.
   - Los ids de los objetos se generan de forma determinista.
5. **Contratos.** Los archivos `[CONTRATO A↔B]` (`datos.py`, `acciones.py`, `puertos.py`, `guardable.py`, `comandos.py` y `constantes.py`) se pueden cambiar, pero **avisando** y en un commit aparte.

## Reglas para todo el código (§7, §9)

- Solo estructuras vistas en el curso: arreglos, listas enlazadas (también dobles), pilas, colas, montículo binario y colas de prioridad.
- Nada de `dict` como índice, caché o tabla de búsqueda: se usa `TablaOrdenada` / `ConjuntoOrdenado`. Leer el resultado de `respuesta.json()` sí está permitido.
- Nada de `sorted()` ni `list.sort()`: se usa `estructuras.ordenamiento.ordenar`.
- No se escriben en el código salas, ids, páginas, presupuestos ni estadísticas de una cripta.
- El modelo no importa `requests`, `json` ni `os`, no usa `open()` y no conoce la vista.
- Cada decisión de estructura se mide con `--bench` **mientras se implementa**, no al final. Eso es lo que pide el Documento de Decisiones (§8), incluida al menos una alternativa descartada medida.

## Hallazgos del API real (revisado 2026-10-02)

- Por ahora solo está publicada `cripta-01`, con 6 salas, presupuesto 9 e inventario de 10. Sus respuestas están en `datos_ejemplo/cripta-01/`.
- Las salidas son **dirigidas**: `2 →E→ 5` está cerrada con llave, pero `5 →O→ 2` no declara cierre. Hay que decidir si la puerta se comparte entre los dos sentidos (ver `modelo/mapa.py`).
- El enemigo `e-401` viene sin `vida`, así que se usa `vida_max`.
- Los objetos del contenido son solo ids de tipo. El modelo genera los ids de instancia.
- `abre` de una llave (`"puerta_2_7"`) no coincide con las salas. La regla del juego es `salida.llave == id de la llave`.
- El esquema de fichas **no** tiene veneno ni regeneración (`additionalProperties: false`), aunque §2.10 los menciona. Se leen como opcionales.
- Sin el encabezado `X-Cripta-Client-Id`, el servidor responde **400**.

## Avance de Persona A (2026-10-05)

La parte de Persona A está implementada: estructuras, modelo, vista de consola, `bench_modelo.py` y las pruebas en `tests/`. Se probó con versiones temporales de las piezas de B, que no forman parte del repositorio. Las decisiones de diseño están explicadas en el docstring de cada archivo.

**Para que funcione, se necesita de Persona B:** `TablaHash`, `ordenamiento.ordenar`, los `desde_json` de `datos.py` (para `tests/test_modelo.py`) y `runner` + `sinteticos.FichasEnMemoria` (para `bench_modelo`). Hasta entonces, `tests/test_modelo.py` falla con `NotImplementedError`. `tests/test_estructuras_a.py` ya pasa.

**Cambios en contratos:**
- `guardable.EstadoGuardable` tiene un campo nuevo al final: `objetos_generados: int = 0`. Hay que guardarlo y cargarlo en el formato binario y en el JSON.
- Se eliminó `TipoEvento.FIN_VENENO`, porque el veneno es una cadena de pulsos.
- `ListaDoble` tiene métodos nuevos que la LRU puede aprovechar: `mover_despues`, `siguiente`, `anterior`, `nodos`, `reenlazar_despues` y `esta_enlazado`.

**Cómo usar el modelo desde el controlador:**
- `mapa.incorporar_contenido(contenido, cache)` se puede llamar en cualquier momento entre decisiones. Es idempotente y no consume azar ni secuencias.
- Cuando muere un enemigo, el modelo crea los objetos de su campo `suelta` y pide sus fichas. Por eso, al resolver la ficha de un enemigo, **también hay que resolver los ids de su `suelta`**.
- Vistas ordenadas: `juego.vista_inventario("peso" | "valor" | "nombre")` y después `vista.mostrar_inventario(juego, lista, criterio)`. El cursor se mueve con `juego.jugador.inventario.avanzar()` / `retroceder()`.
- `RETROCEDER` entra por `juego.ejecutar_accion` igual que las demás acciones. Una acción rechazada no cambia nada del estado.
- Para cargar: `Juego.desde_estado(estado, datos, Mapa.construir(...), cache)`. Antes deben estar resueltas las fichas de **todos** los tipos del estado. Las salas con `contenido_cargado=True` no se vuelven a incorporar.
- `estado_azar` es la tupla de `random.Random.getstate()`. `desde_estado` también acepta listas, por si se guardó en JSON.
- Fijar y liberar: el modelo siempre llama `fijar` / `liberar` en pares coherentes (nunca libera algo que no fijó) y las recalcula después de retroceder o de cargar.

## Fusión A + B (2026-10-15)

Se unió el repositorio de Persona B (`ProjectoEstructurasDeDatos-main`) con la parte de Persona A. Los archivos de B se copiaron tal cual y después se corrigió lo necesario para que las dos mitades se comuniquen. Todo está probado en `tests/test_integracion.py`.

**Errores de integración corregidos:**
- `controlador.py`: `precarga.planificar` recibía el objeto `Sala` en vez de su id. El error quedaba tapado por un `except: pass`, así que nunca se precargaba nada después del inicio.
- `controlador.py`: los comandos de cursor (`sig`/`ant`) y de vista ordenada no hacían nada. Además, cargar una partida no resolvía las fichas del estado, no liberaba las fichas fijadas por la partida anterior y no reiniciaba la precarga.
- `aplicacion.py`: el modo interactivo creaba el controlador sin vista, e importaba `requests` aunque se jugara sin red.
- `lru.py` / `cache_catalogo.py`: con la caché llena de fichas fijadas, `fijar` insertaba la ficha y la misma inserción la desalojaba; el `fijar` siguiente fallaba con `KeyError`. Se agregó `CacheAcotada.insertar_fijada`.
- `bitacora_replay.py`: el log se abría en modo `"a"`, así que dos partidas en el mismo archivo lo corrompían. Ahora cada partida crea su propio archivo en `replays/`.
- `precarga.py`: no se resolvían las fichas del campo `suelta` de los enemigos, y el contenido traído por red no se guardaba en disco.
- `guardado.py`: no guardaba `objetos_generados` (formato subido a versión 2). `cargar_sala` ahora usa `busqueda_binaria` sobre el índice.
- `puntajes.py`: una partida sin terminar se registraba como "en_curso"; ahora queda como "abandono".

**Reglas de §6/§7 corregidas:**
- `set` y `dict` usados como tablas de búsqueda (`cache_catalogo`, `fuente_offline`, `puntajes`, `bitacora_replay`, `datos.DatosSala.desde_json`) se cambiaron por `TablaHash` / `ConjuntoHash`.
- `modelo/datos.py` importaba `json`: `Ficha.a_json()` pasó a ser `Ficha.a_dict()` y es el adaptador de disco el que escribe el JSON.

**Decisiones nuevas:**
- `python main.py` usa la API; `--offline` (sin directorio) juega con `datos_ejemplo/`. Ver la sección siguiente.
- Combate "por turnos" solo en la pantalla: la bitácora muestra "Tu turno" y "Turno de los enemigos", pero las reglas siguen el reloj virtual de §2.3.
- Al cargar una partida se cierra la bitácora de replay de la sesión, porque un log siempre empieza en t=0 con su semilla.

**Pendiente para Persona B** (actualizado el 2026-10-16):
- Registrar sus prompts en `PROMPTS_LLM.md` (§10.3). Si no usó ningún LLM, la bitácora tiene que decirlo.
- Repasar todo antes de la defensa (§9: cualquiera puede tener que explicar cualquier decisión), sobre todo lo que cambió en su parte: `tabla_ordenada.py` (reemplazó a la tabla hash), la caché LRU y `gc.freeze()` en el controlador. Ver las secciones del 2026-10-15 y 2026-10-16 de este plan y el Documento de Decisiones completo.
- (Ya hecho: los restos sin usar de `ordenamiento.py` y los umbrales medidos de §4.9.)

## API activada (2026-10-15)

- Se instaló `requests` y `python main.py` usa la API por defecto (§3.4: `--offline` es la alternativa).
- `cliente_http.py`: revisar el presupuesto y contar la solicitud se hace con un candado (`threading.Lock`). La precarga pide contenido desde otro hilo y, sin el candado, el contador podía fallar.
- `fuente_offline.py`: cada cripta lee solo su carpeta (antes, con varias criptas en el paquete, se mezclaban salas y contenido).
- `precarga.py`: cuando hace falta una sala que no se pidió, se pide junto con sus vecinas no pedidas (mismo costo, §3.4). Si la red falla, el error se informa una vez, en vez de reintentar hasta agotar el presupuesto.
- Probado contra la API real con un bot explorador y caché vacía: cripta-01 6/9 solicitudes, cripta-02 8/23, cripta-03 10/42, cripta-04 12/52, sin errores. El replay de una partida en línea da el mismo resultado en línea y con `--offline`. Las 11 fichas del catálogo son las mismas en las 4 criptas.
- Pruebas sin red del cliente en `tests/test_red.py` (encabezado, 429, presupuesto, dos hilos, errores) y de la separación de criptas en `FuenteOffline`.

## Documento de Decisiones y mediciones (2026-10-15)

- Documento de Decisiones (hoy `Decisiones_de_diseño.md`; antes era `DOCUMENTO_DE_DECISIONES.md`): una sección por cada problema de §4 (4.1 a 4.11), con números de `--bench`. **Los dos deben leerlo completo** (§9: cualquiera puede tener que explicar cualquier decisión).
- `--bench` ahora también mide: frecuencia real de operaciones (`bench/frecuencias.py`, con el bot de `bench/bot.py`), LRU vs FIFO vs LFU, recuperar fichas de disco, precarga, guardado con estados reales y ordenamiento con claves costosas. `--bench FILTRO` corre solo una parte.
- `datos_ejemplo/` tiene las respuestas reales de las 4 criptas publicadas (se descargaron una vez).
- Cambios en el código de B que salieron de medir:
  - `ordenamiento.py` calcula la clave una sola vez por elemento (hasta 37 veces más rápido con claves costosas) y usa umbrales medidos: inserción hasta 32 elementos o con como mucho 2·log₂(n) bajadas.
  - `precarga.py` deja de planificar cuando ya pidió todo (antes recorría el mapa completo en cada decisión).
- Limpieza: se quitaron restos sin usar (alias de `TablaHash`, funciones viejas de `ordenamiento`, métodos sin llamar) y cada archivo de B volvió a tener un comentario inicial con sus decisiones.
- Nueva prueba con un esqueleto de 3 páginas (`tests/test_integracion.py`).

## Ventana con sprites (2026-10-15)

- `python main.py --gui` abre el juego en una ventana con sprites pixel art (pygame-ce). Sin `--gui` todo sigue igual, en la terminal. `pygame-ce` está en `requirements.txt`. Si no está instalado, `--gui` lo dice con un mensaje y la terminal, `--replay` y `--bench` funcionan igual.
- Se usa `pygame-ce` y no `pygame` porque el `pygame` clásico todavía no tiene versión para Python 3.14. Se programa igual (`import pygame`).
- Es otra **vista** del MVC: el modelo no cambió y el controlador casi nada (solo el mensaje de inicio, que ahora no nombra el comando "ayuda" de la consola).
- `vista/base.py`: lo que comparten las dos vistas (a quién atacar, qué recoger, qué puerta abrir, el menú de F y la bitácora con "Tu turno" / "Turno de los enemigos"). Antes estaba dentro de `vista_consola.py`. Así las dos vistas arman exactamente los mismos comandos, y el replay no depende de la vista.
- `vista/sprites.py`: los sprites son cuadrículas de texto de 16 x 16 (los íconos, de 8 x 8) con una paleta de colores. No hay archivos de imagen. Qué sprite le toca a cada enemigo u objeto se decide por palabras del id o del nombre ("rata", "daga", "negra"...). Si no coincide ninguna, se usa uno genérico, así una cripta nueva también se dibuja.
- `vista/vista_grafica.py`: la sala dibujada con sus puertas (cada una con su tecla W/A/S/D), los enemigos con barra de vida y número, el panel del jugador, el inventario, la bitácora, menús y avisos. Además: números de daño, destellos, la calavera de un enemigo derrotado y un destello morado al usar un pergamino.
- Decisión: la ventana consulta cada ficha del catálogo **una vez por tipo** y guarda lo que necesita en su propia tabla (hoy `TablaOrdenada`). La pantalla se redibuja 30 veces por segundo, y consultar la caché en cada cuadro inflaría sus estadísticas (§5.1) y cambiaría el orden de la LRU (§4.4). Hay una prueba que lo verifica.
- Las teclas pasan por una `ColaEnlazada`, de la que también leen los menús. Si alguien aprieta "Q" y "2" muy rápido, el "2" le llega al menú que abrió la "Q".
- Pruebas en `tests/test_vista_grafica.py`: los sprites (tamaños, colores y qué sprite le toca a cada ficha real) y la ventana con el "driver" de video `dummy`, que no abre nada en la pantalla. Incluye una partida completa con el controlador (elegir cripta, nombre, moverse, salir). Si pygame no está instalado, las pruebas de la ventana se saltan.

## Solo estructuras vistas en el curso (2026-10-15)

El grupo decidió usar solo estructuras que ya vimos en el curso: arreglos, listas enlazadas (también dobles), pilas, colas, montículo binario y colas de prioridad. Se revisó todo el código y hubo que cambiar dos cosas:

- **La tabla hash** (`TablaHash` / `ConjuntoHash`) → **`TablaOrdenada` / `ConjuntoOrdenado`** (`estructuras/tabla_ordenada.py`). Son dos arreglos ordenados por clave (claves y valores) y se busca con búsqueda binaria, O(log n). Para borrar se usa borrado perezoso, igual que en la agenda: se marca la casilla y no se corre nada. Tiene los mismos métodos que la tabla hash, así que el resto del código solo cambió el `import`. La tabla hash se **eliminó** del proyecto (código, mediciones y pruebas); la alternativa descartada que se mide en §4.3 es la lista sin ordenar.
- **La lista doble** dejó de ser circular con centinela: ahora es la lista doble "de libro", con punteros al primero y al último. Cada nodo sabe en qué lista está, así se comprueba en O(1) que un nodo es de esa lista (el retroceso lo usa).

Lo demás ya era de la lista: el montículo (cola de prioridad de la agenda), las colas enlazadas, el buffer circular (una cola de tamaño fijo sobre un arreglo, no una lista circular), la pila de cambios del retroceso y los arreglos.

Medido con `--bench` (detalles en el Documento de Decisiones, §4.3 y §4.5):
- Buscar: con 5000 claves el arreglo ordenado tarda 1.25 µs y la lista sin ordenar 49 µs. En una partida se hacen 21–33 búsquedas por decisión (~30 µs en total).
- El ciclo de §5.2 sigue por debajo de 20 ms (peor caso 7.1 ms con 900 salas y 500 enemigos): los turnos de los enemigos no usan tablas.
- Inventario: soltar un objeto cuesta lo mismo esté al inicio, en el medio o al final (7.2 / 8.0 / 8.3 µs con 10 000 objetos; la `list` va de 3.0 a 0.06 µs según la posición).
- Recolector de basura: una corrida dio 21 ms en el peor ciclo con 400 salas. Midiendo, unos 8 ms del peor ciclo eran pausas del recolector de basura de Python revisando el mapa completo. Ahora el controlador llama `gc.freeze()` después de cargar la cripta (y al cargar una partida), y el peor caso con 900 salas bajó de 11–16 ms a unos 7 ms.
- Los números del Documento de Decisiones son la mediana de 3 corridas completas de `--bench`.
- La partida da exactamente el mismo resultado con distintos `PYTHONHASHSEED`, y todas las pruebas pasan (88), incluidas las de retroceso al azar y replay.

**Para Persona B:** la tabla hash y la caché eran tu parte. La caché LRU no cambió: solo usa la tabla nueva en lugar de la hash, que ya no está en el proyecto. Conviene que revises `tabla_ordenada.py` y la sección §4.3 del Documento de Decisiones, porque te pueden preguntar por ellas en la defensa.

## Revisión antes de entregar (2026-10-16)

Se revisó todo el proyecto contra el enunciado. Cambios:

- **Ventana (§10.2):** la bitácora del panel solo mostraba unos 10 mensajes. Ahora la tecla **L** abre la bitácora completa con los últimos 20 (con prueba).
- **Nada de ids de criptas en el código (§9):** el bench ya no tiene escritos `"cripta-04"`, `"ent_rata_gigante"`, etc. Las criptas salen de `datos_ejemplo/criptas.json`, la partida para medir el guardado se juega en la cripta más grande que haya ahí, y las fichas para medir la caché son las que pidió el juego al jugar.
- **Reserva de presupuesto (§5.1):** la precarga anticipada nunca usa las últimas 2 solicitudes; quedan para lo obligatorio (con prueba). En las criptas publicadas no cambia nada: siguen siendo 12 solicitudes de contenido.
- **Limpieza:**
  - Se borraron `Plan_de_trabajo_CRIPTA.pdf` (versión vieja del plan, del 2 de octubre) y los `criptas.json` de `datos_ejemplo/cripta-02`, `cripta-03` y `cripta-04` (repetían el de la raíz y listaban criptas que no estaban en su carpeta).
  - Se quitaron 12 funciones que nada usaba (entre ellas `sinteticos.generar_cripta`, que tenía ids reales escritos) y los `import` que quedaron sin usar.
- **README:** tabla con los documentos de la entrega y la tecla L.
- **Prueba desde un entorno limpio (§10.1):** copia del proyecto sin `datos_locales/` ni cachés, entorno de Python nuevo y `pip install -r requirements.txt`. Resultados:
  - las 91 pruebas pasan;
  - una partida sin red se juega y su replay da lo mismo;
  - `--bench` corre;
  - con la API del curso arranca bien (usó 2 de 9 solicitudes porque aprovechó lo que la partida anterior dejó en disco).

**Falta (lo hacen los integrantes):** los prompts de Persona B en la bitácora, que Persona B repase todo para la defensa y subir el proyecto a GitHub.

