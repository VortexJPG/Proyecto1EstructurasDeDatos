# Bitácora de uso de LLM (§10.3)

Cada entrada: fecha aproximada, herramienta o modelo, prompt textual y para qué se usó la respuesta.

---

### 1

- **Fecha:** 2026-10-02
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt** (se adjuntó el enunciado completo `Proyecto_CRIPTA_Estructuras_de_Datos_II_2026.md`):

  > Estoy haciendo un proyecto de estructura de datos con un compañero, necesitamos hacer un codigo de acuerdo al documento que te adjunto, quiero que lo leas completo y analizalo bien.
  >
  > No quiero que hagas el codigo de primeras, quiero que nos dividas el trabajo en 2 para poder hacer la mitad yo y la otra mitad mi compañero, adicionalmente quiero que hagas la base para que empecemos a programar, crea las clases y las funciones (Sin programar)
  >
  > Ten en cuenta que mas adelante tendremos que hacer una bitacora diciendo que estructuras de datos utilizamos y porque (En el documento salen cuales son las que se pueden usar), no quiero que hagas la bitacora solo ten en cuenta eso

- **Uso:** dividir el trabajo en dos mitades y generar el esqueleto de clases y funciones, sin implementación.

### 2

- **Fecha:** 2026-10-02
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > pregunta, como armaste la base, la idea de la base es que se haga en terminal el juego o con interfaz?

- **Uso:** decidir si la vista del juego será de consola o gráfica.

### 3

- **Fecha:** 2026-10-05
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt** (se adjuntaron el enunciado, `PLAN_DE_TRABAJO.md` y esta bitácora):

  > Estoy haciendo un proyecto para mi materia de estructuras de datos, anteriormente te habia enviado unos prompts con las instrucciones, sin embargo, la conversacion no se guardo, te adjunto las instrucciones de nuevo para que las veas, para que tengas mas contexto, en el archivo de PROMPTS_LLM es una bitacora que contiene los prompts que te envie en la conversacion anterior, quiero que sigas registrando en este archivo los prompts que te mande para continuar el proyecto, el proyecto se esta trabajando en Usuarios>Kevin>Codes>Cripta, anteriormente te pedi que me hicieras una base.
  >
  > En plan de trabajo. es la guia que me hiciste, ya que lo voy a hacer con un compañero, yo voy a hacer persona A, quiero que hagas todo el codigo que le toca a la persona A, cuando vayas a usar estructuras de datos, usa solo las que se especifican en el documento, para entender todo el codigo, te diria que analices todos los archivos que estan en la carpeta de Cripta en codes.

- **Uso:** retomar el proyecto (la conversación anterior se perdió), seguir registrando los prompts en esta bitácora e implementar la parte de Persona A (estructuras, modelo, vista de consola, `bench_modelo.py` y pruebas en `tests/`).

### 4

- **Fecha:** 2026-10-05
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > Quiero que me expliques que estructuras de datos usaste y porque escogiste esas y no otras, en temas de efectividad, rapidez y algo mas que tenga que tener en cuenta

- **Uso:** entender y justificar las estructuras de Persona A para el Documento de Decisiones y la defensa.

### 5

- **Fecha:** 2026-10-06
- **Integrante:** Brandon
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > Buenas, me toca la parte de datos, red y persistencia del proyecto de Cripta (soy la persona B). Ya esta el esqueleto que armamos. Puedes leer los archivos que dicen Contrato A↔B y decirme que me toca implementar a mi y en que orden, para empezar por lo que mi compañero necesita primero.

- **Uso:** entender el contrato entre A y B y priorizar las estructuras que bloqueaban a la Persona A (`TablaHash` y los `desde_json`).

### 6

- **Fecha:** 2026-10-06
- **Integrante:** Brandon
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > ok, arranquemos con la tabla hash. Resuelve las colisiones con encadenamiento y que se agrande sola cuando pase cierto factor de carga. Con poner, obtener, contiene y eliminar basta, y tambien un conjunto con las mismas operaciones. Hazle pruebas con claves repetidas y forzando colisiones, y ojo que el hash de los textos no puede cambiar entre ejecuciones porque despues guardamos cosas en disco.

- **Uso:** `estructuras/tabla_hash.py` (`TablaHash` y `ConjuntoHash`) con encadenamiento, redimensionado y pruebas de colisiones y claves repetidas.

### 7

- **Fecha:** 2026-10-07
- **Integrante:** Brandon
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > ahora la cola con nodos enlazados (encolar, desencolar y ver el frente en O(1)), la voy a usar despues en el recorrido en anchura de la precarga. Y pasame tambien los desde_json de modelo/datos.py: hay campos que no siempre vienen, por ejemplo el enemigo viene sin vida y el esquema no trae veneno ni regeneracion, asi que leelos como opcionales y usa vida_max cuando no venga vida. Pruebalo con lo que hay en datos_ejemplo.

- **Uso:** `ColaEnlazada` y todos los `desde_json` de `datos.py`, tolerando los campos opcionales (enemigo sin `vida`, fichas sin veneno ni regeneración).

### 8

- **Fecha:** 2026-10-08
- **Integrante:** Brandon
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > ahora el cliente http, que es lo mas delicado. Tiene que mandar un uuid en X-Cripta-Client-Id generado una sola vez por ejecucion y reutilizarlo en todas las solicitudes (tambien en los reintentos), y cuando el api conteste 429 leer el reintentar_en y esperar antes de reintentar sin que el programa se caiga. Los reintentos cuentan en el presupuesto, asi que lleva un contador y nunca lo pases; si se va a pasar, avisa con un mensaje claro. Ponle timeout a cada request. Despues hazme la fuente offline, que lea las respuestas guardadas y tenga la misma interfaz, para poder probar sin gastar solicitudes y que el modelo no tenga if por todos lados.

- **Uso:** `ClienteHTTP` (encabezado obligatorio, 429 con espera, contador contra `presupuesto_solicitudes`) y `FuenteOffline` intercambiable por el mismo puerto.

### 9

- **Fecha:** 2026-10-09
- **Integrante:** Brandon
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > pasame al ordenamiento. Necesito insercion y mezcla, y una funcion ordenar() que elija sola cual usar segun que tan grande y desordenada este la lista. Nada de sorted(), .sort() ni heapq. Agrega tambien la busqueda binaria. Deja los dos algoritmos separados y con un contador de comparaciones, que los tengo que medir despues en el bench.

- **Uso:** `estructuras/ordenamiento.py` con inserción, mezcla, selector automático y búsqueda binaria, con umbrales pensados para medirse (§4.9).

### 10

- **Fecha:** 2026-10-09
- **Integrante:** Brandon
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > ahora la cache de fichas. Consultar si una ficha esta tiene que ser O(1): usa la tabla que hicimos y la lista doble de mi compañero. Politica LRU. Necesito poder fijar una ficha en uso para que nunca se desaloje, con un contador de referencias, y llevar cuenta de aciertos y fallos para el reporte final. Y una duda, que se hace si estan todas fijadas y llega una ficha nueva?

- **Uso:** `CacheAcotada` con LRU, `fijar`/`liberar` por contador de referencias y contadores de aciertos y fallos. Ante la duda se decidió crecer temporalmente y avisar.

### 11

- **Fecha:** 2026-10-10
- **Integrante:** Brandon
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > sigamos con el cache_catalogo. Cuando falte una ficha, primero busca en memoria, si no esta en disco (eso no gasta solicitudes) y solo las que de verdad no esten las pides al api en lotes de 10. Un id que ya esta no se puede volver a pedir. Lo nuevo se guarda en disco y en memoria, y la cache no puede perderse al cerrar el programa. Guarda tambien la version de la cripta y la del catalogo para saber si lo que hay en disco sigue sirviendo.

- **Uso:** `CacheCatalogo` (memoria → disco → red en lotes de 10, sin repetir ids) y `AlmacenDisco` validado por versión de cripta y de catálogo.

### 12

- **Fecha:** 2026-10-12
- **Integrante:** Brandon
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > me falta la parte que junta todo. Antes de dejar mover al jugador el contenido de la sala destino tiene que estar cargado. Quiero ir pidiendo por adelantado las salas mas cercanas (recorrido en anchura desde donde estoy) en lotes de 10, y que las respuestas se usen en el orden en que se pidieron, no en el orden en que lleguen, para que el replay salga igual siempre. Cuidado con el presupuesto, no lo puedo pasar. Y guarda la partida en un archivo de solo agregar, una linea por accion con el formato de acciones.py, con un encabezado de cripta, versiones y semilla.

- **Uso:** `PlanificadorPrecarga` (BFS por cercanía, lotes de 10, incorporación en orden determinista) y `EscritorReplay` con `a_linea`/`desde_linea`.

### 13

- **Fecha:** 2026-10-13
- **Integrante:** Brandon
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > ahora el guardado. Quiero un formato binario propio con struct (nada de pickle) con una cabecera: marca, version del formato, semilla y versiones de la cripta y del catalogo, y que si la version del formato no coincide lo diga claro en vez de cargar mal. Adentro un indice por sala con desplazamientos para poder cargar una sola sala sin leer todo el archivo. Guarda tambien el mismo estado en json para comparar tamaño y tiempo. Y la tabla de puntajes local, ordenada con nuestro ordenar().

- **Uso:** `guardado.py` binario (cabecera + índice por sala con `seek`) con versión de formato y su versión JSON, más `puntajes.py` (§4.11).

### 14

- **Fecha:** 2026-10-14
- **Integrante:** Brandon
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > ya casi termino. Necesito el bench de mi parte: aciertos y fallos de la cache con tamaños distintos, insercion vs mezcla, guardado binario vs json y la tabla hash contra la alternativa que descartamos, asi se puede medir la que no usamos. Con esos numeros arma las secciones 4.2, 4.3, 4.4, 4.9, 4.10 y 4.11 del documento de decisiones, con la estructura que pide el profe (problema, alternativas, decision, complejidad, evidencia y limites). Y el README con los comandos y donde quedan los archivos que se generan.

- **Uso:** `bench/bench_datos.py` + `runner.py` con las mediciones de la parte B, las secciones §4.2–§4.4 y §4.9–§4.11 del Documento de Decisiones, y el README.

### 15

- **Fecha:** 2026-10-15
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > Mira en descargas el archivo ProjectoEstructurasDeDatosMain (el que no esta en un zip), esa es la parte que hizo mi compañero (persona B) quiero que fusiones los archivos de ProjectoEstructurasDeDatosMain en Cripta, verifica que todo encaje correctamente, que todos los archivos se puedan comunicar correctamente, adicionalmente el juego quiero que corra en terminal (por el momento), el tema de la API lo agregare despues.
  >
  > El tipo de combate quiero que sea por turnos para simplificar el sistema y no hacerlo muy complejo

- **Uso:** fusionar la parte de Persona B con la de Persona A, corregir la integración y dejar el juego jugable en la terminal. Ante la pregunta del asistente, se eligió mostrar el combate "por turnos" en la pantalla, manteniendo el reloj virtual del enunciado (§2.3).

### 16

- **Fecha:** 2026-10-15
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > dime que hace falta añadir para correr bien el codigo contando la API

- **Uso:** saber qué faltaba para que el juego funcionara completo con la API del curso.

### 17

- **Fecha:** 2026-10-15
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > 3 preguntas, 1, puedes instalar tu mismo requests o lo tengo que hacer yo? y 2, puedes configurar lo de la API tu o lo tengo que hacer yo manual? y 3, la API se encuentra en los documentos que te envie al inicio?

- **Uso:** aclarar quién instalaba `requests` y configuraba la API, y confirmar que la dirección de la API venía en el enunciado.

### 18

- **Fecha:** 2026-10-15
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > Instala requests

- **Uso:** instalar la dependencia `requests` para poder usar la API.

### 19

- **Fecha:** 2026-10-15
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > ok, que mas haria falta

- **Uso:** revisar qué le faltaba al proyecto después de activar la API (Documento de Decisiones, mediciones pendientes y limpieza del código).

### 20

- **Fecha:** 2026-10-15
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt** (los números se refieren a la lista de pendientes de la respuesta anterior):

  > ok mira, haz los puntos 1 2 y 5, del github me encargo yo

- **Uso:** escribir el Documento de Decisiones de Diseño con una sección por cada problema de §4 (1), agregar las mediciones que faltaban en `--bench`, incluida la frecuencia real de las operaciones con un bot que juega las criptas (2), y limpiar el código y corregir detalles menores (5).

### 21

- **Fecha:** 2026-10-15
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > haz el documento de decisiones en word, pero conserva el .md

- **Uso:** generar la versión en Word (`.docx`) del Documento de Decisiones de Diseño.

### 22

- **Fecha:** 2026-10-15
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > Cambios
  > Quiero que moverse se utilice WASD, w norte, a oeste, s sur, d este
  > para atacar quiero que se use la Q
  > para esperar la T
  > para abrir la R
  > para recoger E
  > Soltar, USAR y Equipar F
  >
  > EL inventario la I

- **Uso:** cambiar los controles de la consola a teclas (WASD para moverse, Q, T, R, E, F e I).

### 23

- **Fecha:** 2026-10-15
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > ok, que tan complicado seria usar MVC y crear una interfaz grafica? siento que con texto cuesta un poco distiguir la situacion

- **Uso:** comparar opciones de interfaz gráfica (consola mejorada, Tkinter o Pygame) y cuánto trabajo llevaría cada una con el MVC que ya tenía el proyecto.

### 24

- **Fecha:** 2026-10-15
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > ok si te pidiera por ejemplo que hicieras sprites tipo pixel art para el juego cual de las opciones seria, y pregunta, si yo instalo pygame y lo que le envio al profe es el github, y el profe descarga el codigo, tendria que instalar pygame o no?

- **Uso:** escoger la opción para sprites pixel art (Pygame; en Python 3.14, pygame-ce) y saber si el profesor tendría que instalarlo (sí, con `requirements.txt`).

### 25

- **Fecha:** 2026-10-15
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > ok pero pygame es tipo una extencion aparte, una aplicacion o solo es una linea de codigo que necesito poner?

- **Uso:** entender qué es pygame (una librería de Python que se instala con `pip`) y cómo se usa en el código.

### 26

- **Fecha:** 2026-10-15
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt** (la "opción 3" era Pygame, de una lista de opciones de interfaz gráfica que había dado el asistente):

  > Haz la opcion 3, haz los sprites tipo pixel art

- **Uso:** agregar una ventana opcional (`python main.py --gui`) con sprites pixel art dibujados en el código (`cripta/vista/sprites.py`), usando pygame-ce. El juego en la terminal sigue igual.

### 27

- **Fecha:** 2026-10-15
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > ok, entonces para correrlo con la API como seria

- **Uso:** saber cómo correr el juego (en la terminal y en la ventana) usando la API del curso.

### 28

- **Fecha:** 2026-10-15
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > pregunta las 4 criptas son siempre las mismas?

- **Uso:** entender que las criptas publicadas pueden cambiar de versión y cómo lo maneja el programa (valida la versión y descarta lo guardado si cambió).

### 29

- **Fecha:** 2026-10-15
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > ok, hazme un repaso general de las estructuras de datos que apararecen en el codigo

- **Uso:** repasar todas las estructuras de datos del proyecto (de Persona A y de Persona B), dónde se usan y por qué, para preparar la defensa.

### 30

- **Fecha:** 2026-10-15
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt** (se adjuntó de nuevo el enunciado):

  > en el documento del inicio (te lo adjunto de nuevo) se mencionan esas bases de datos?

- **Uso:** verificar si el enunciado nombra las estructuras de datos que hay que usar (no las nombra: describe las propiedades que deben cumplir y prohíbe `dict`, `sorted()` y `.sort()`).

### 31

- **Fecha:** 2026-10-15
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > ok, puedes nombrarme todas o la mayoria de estructuras de datos que hay (en general no en el proyecto)

- **Uso:** repasar las estructuras de datos que existen en general y cuáles aparecen en el proyecto.

### 32

- **Fecha:** 2026-10-15
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > Verifica que las bases de datos usadas sean Arrays, listas enlazadas (tambien doble), pilas, colas, monticulo binario y colas de prioridad, en caso que hayas usado otra, cambiala y acopla alguna de las que te mencione al codigo

- **Uso:** dejar el proyecto solo con estructuras vistas en el curso: la tabla hash se cambió por un arreglo ordenado con búsqueda binaria y la lista doble dejó de ser circular.

### 33

- **Fecha:** 2026-10-15
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > cambia el word

- **Uso:** reemplazar el Word del Documento de Decisiones por la versión actualizada con el cambio de estructuras.

### 34

- **Fecha:** 2026-10-15
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > pero quita lo que se descarto, no lo dejes

- **Uso:** eliminar del proyecto la tabla hash descartada (código, mediciones, pruebas y Documento de Decisiones).

### 35

- **Fecha:** 2026-10-15
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > revisa de nuevo el word y dime como lo ves

- **Uso:** revisar el Documento de Decisiones en Word. Salieron varios puntos a corregir: páginas casi vacías, una aclaración en §4.3 y números de corridas distintas del `--bench`.

### 36

- **Fecha:** 2026-10-16
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt** (los números se refieren a los puntos de la revisión anterior):

  > ok mira, para el 1 trata de corregirlo para que no hayan espacios en blanco, el 3 corrigelo, el 4 corrigelo

- **Uso:** corregir el Word: quitar las páginas casi vacías (1), aclarar en §4.3 que insertar en la lista sin ordenar también cuesta O(n) porque hay que revisar que la clave no esté repetida (3) y actualizar todos los números con una sola medición, que terminó siendo la mediana de 3 corridas del `--bench` (4). Al medir apareció un pico de 21 ms en el ciclo de §5.2; se agregó `gc.freeze()` en el controlador y el peor caso bajó a unos 7 ms.

### 37

- **Fecha:** 2026-10-16
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > ok dime, hace falta algo mas en general? analiza todo

- **Uso:** revisar el proyecto completo contra el enunciado para ver qué falta antes de entregar.

### 38

- **Fecha:** 2026-10-16
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > Dime que mas hace falta, y que archivos sobran

- **Uso:** revisar qué falta para entregar y qué archivos de la carpeta del proyecto no hacen falta.

### 39

- **Fecha:** 2026-10-16
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt** (los números se refieren a la lista de la respuesta anterior):

  > Ok haz los pasos 1,2,3,4,5 y 6

- **Uso:** ver los 20 mensajes en la ventana, sacar los ids de criptas reales del código del bench, dejar una reserva de solicitudes en la precarga, borrar archivos y código que sobraban, actualizar README y plan de trabajo, y probar la instalación desde un entorno limpio.

### 40

- **Fecha:** 2026-10-17
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > En descargas, estan los archivos de PROMPTS_LLM y Decisiones_de_diseño actualizados, pasalos a la carpeta de Cripta y elimina los desactualizados

- **Uso:** reemplazar la bitácora y el Documento de Decisiones por las versiones revisadas a mano y actualizar los enlaces del README y del plan de trabajo.

### 41

- **Fecha:** 2026-10-17
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt:**

  > Pasa el documento de decisiones de cripta a .md y elimina el word

- **Uso:** convertir `Decisiones_de_diseño.docx` a `Decisiones_de_diseño.md` (mismo texto, con índice que enlaza a cada sección) y dejar solo la versión en Markdown.

### 42

- **Fecha:** 2026-10-17
- **Integrante:** Kevin
- **Herramienta / modelo:** Claude Code (Claude Opus 5.5)
- **Prompt** (se adjuntó otra vez el enunciado):

  > ok asi como esta la carpeta de cripta, podria subirlo a un github y enviarle el link al profesor, de acuerdo al documento que te envie claro, por si acaso te lo vuelvo a adjuntar

- **Uso:** revisar contra el enunciado si la carpeta está lista para subirla a GitHub y entregarla.
