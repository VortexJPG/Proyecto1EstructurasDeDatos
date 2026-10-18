# Decisiones de Diseño

CRIPTA · Proyecto de Estructuras de Datos

**Integrantes:** Kevin Pérez Arce y Brandon Bejarano Moya

**Profesor:** Jose Calvo Suarez

Universidad Nacional (UNA) · II Ciclo 2026

## Contenido

- [Introducción](#introducción)
- [4.1 Qué ocurre a continuación (la agenda de eventos)](#41-qué-ocurre-a-continuación-la-agenda-de-eventos)
- [4.2 Traer el contenido antes de que haga falta (precarga)](#42-traer-el-contenido-antes-de-que-haga-falta-precarga)
- [4.3 Resolución de referencias del catálogo](#43-resolución-de-referencias-del-catálogo)
- [4.4 Reutilización y caché persistente](#44-reutilización-y-caché-persistente)
- [4.5 Inventario](#45-inventario)
- [4.6 Pergaminos de retroceso (historial)](#46-pergaminos-de-retroceso-historial)
- [4.7 El rastro del jugador](#47-el-rastro-del-jugador)
- [4.8 Bitácora en pantalla](#48-bitácora-en-pantalla)
- [4.9 Ordenamiento](#49-ordenamiento)
- [4.10 Guardado binario de la partida](#410-guardado-binario-de-la-partida)
- [4.11 Bitácora de partida y reproducción (replay)](#411-bitácora-de-partida-y-reproducción-replay)

## Introducción

Aquí explicamos qué estructura de datos usamos para cada problema, por qué la escogimos y qué medimos para comprobarlo:

1.  El problema (y cuántas veces pasa de verdad).
2.  Qué opciones pensamos.
3.  Qué escogimos.
4.  Cuánto cuesta (complejidad).
5.  Lo que medimos.
6.  Cuando dejaría de servir.

### Qué estructuras usamos

Decidimos usar: arreglos, listas enlazadas (también dobles), pilas, colas, montículo binario y colas de prioridad. Para buscar por id usamos un arreglo ordenado con búsqueda binaria.

| Estructura | Dónde se usa |
|----|----|
| Arreglo (`list` de Python) | Las 4 salidas de cada sala, el montículo, el buffer circular, las tablas ordenadas |
| Arreglo ordenado + búsqueda binaria (`TablaOrdenada`) | Buscar por id: salas, enemigos, puertas, fichas de la caché, objetos del inventario, salas ya pedidas; el índice del archivo de guardado |
| Lista doblemente enlazada | Inventario, enemigos y objetos de cada sala, orden de uso de la caché (LRU) |
| Pila | Los cambios de cada acción, para deshacerlos al revés (retroceso) |
| Cola con nodos enlazados | Recorrido en anchura (BFS) de la precarga, ids pendientes del catálogo, teclas de la ventana |
| Cola de tamaño fijo sobre un arreglo (buffer circular) | Los últimos 20 mensajes y los últimos 5 retrocesos |
| Montículo binario = cola de prioridad | La agenda de eventos |

### Cómo medimos

- Todos los tiempos salen de `python main.py --bench` (o `--bench agenda`, `--bench cache`, etc. para medir solo una parte).
- Los medimos en la computadora de Kevin: Windows 11, Python 3.14, procesador AMD. Entre una corrida y otra cambian un poco (hasta un 10–20 %, o más si la computadora está ocupada con otra cosa), pero las diferencias grandes se mantienen. Por eso corrimos el `--bench` completo 3 veces y cada número de este documento es la mediana (el valor del medio de las tres), así un pico ocasional no cambia las conclusiones.
- µs = microsegundo (una millonésima de segundo). ms = milisegundo (una milésima). 1 ms = 1000 µs.
- Para saber cuántas veces se usa cada operación, `--bench` pone a jugar un *bot* (que se encarga de explorar, pelear, recoger cosas y abrir puertas) en las 4 criptas reales del servidor, sin red, y cuenta las llamadas. También juega una cripta sintética grande: 900 salas y 500 enemigos despiertos, todos moviéndose a la vez. Esa tabla aparece al final del `--bench`; aquí copiamos las partes que importan.
- “Por decisión” quiere decir “cada vez que el jugador hace una acción” (moverse, atacar, esperar…).

## 4.1 Qué ocurre a continuación (la agenda de eventos)

### 1. El problema

El juego no va por rondas. Hay un reloj y todo lo que va a pasar es un *evento* con una hora: el turno de cada enemigo, cada pulso de veneno, cuando se rearma una trampa, cuando se cierra una puerta, el turno del jugador. En cada paso hay que sacar el evento con la hora más baja; si dos tienen la misma hora, sale el que se programó primero (por eso cada evento tiene un número de secuencia).

Además, hay que poder cancelar eventos (un enemigo que muere, un antídoto que corta el veneno) y cambiarles la hora (una poción de velocidad).

Cuántas veces pasa (medido):

|  | Criptas reales (02–04) | Sintética (900 salas, 500 enemigos) |
|----|----|----|
| Sacar el siguiente evento, por decisión | 1.4 – 1.7 | 654 |
| Programar un evento, por decisión | 1.6 – 1.9 | 654 |
| Cancelar, por decisión | 0.1 – 0.2 | casi nunca |
| Máximo de eventos esperando a la vez | 4 | 668 |

Las criptas publicadas son chicas y hay pocos enemigos despiertos a la vez. La de la revisión puede ser mucho más grande, por eso medimos también la sintética.

### 2. Opciones

- **Lista sin ordenar:** agregar es rápido, pero para saber cuál sigue hay que revisar todos los eventos.
- **Lista ordenada:** el siguiente siempre está al inicio, pero cada evento nuevo hay que meterlo en su lugar y correr los demás. Aquí se agrega tanto como se saca, así que no sirve.
- **Montículo binario de mínimos:** el menor siempre está en la raíz. Agregar y sacar cuestan O(log n).
- Para cancelar dentro del montículo: un montículo indexado (cada evento sabe su posición y se saca de ahí) o el borrado perezoso (marcar el evento como cancelado y botarlo cuando llegue a la raíz).

### 3. Qué escogimos

Montículo binario de mínimos guardado en una `list` (los hijos de la posición `i` están en `2i+1` y `2i+2`), ordenado por (hora, número de secuencia). Es la cola de prioridad de la agenda: la prioridad es la hora. Para cancelar usamos borrado perezoso: el evento se marca como cancelado y, cuando llega arriba, se bota sin ejecutarlo. Para que la basura no crezca sin control, si los cancelados llegan a ser más que los vivos, el montículo se reconstruye solo con los vivos.

Cambiar la hora de un evento (velocidad) es cancelar el viejo y programar uno nuevo con un número de secuencia nuevo, como dice el 2.3.

Descartamos el montículo indexado porque cada intercambio tendría que actualizar la posición guardada en el evento: más código y más lento. Con el borrado perezoso cancelar es O(1), y además el retroceso (4.6) queda más simple: “des-cancelar” es quitar la marca.

### 4. Complejidad

| Operación          | Montículo (lo nuestro) | Lista sin ordenar          |
|--------------------|------------------------|----------------------------|
| Programar          | O(log n)               | O(1)                       |
| Sacar el siguiente | O(log n)               | **O(n)**                   |
| Cancelar           | O(1)                   | O(n) (hay que encontrarlo) |

### 5. Lo que medimos

Costo de una operación (sacar + reprogramar, y de vez en cuando cancelar), con n eventos esperando:

| Eventos esperando | Montículo | Lista sin ordenar (descartada) |
|-------------------|-----------|--------------------------------|
| 100               | 2.8 µs    | 10.5 µs                        |
| 500               | 3.5 µs    | 51.2 µs                        |
| 2000              | 4.0 µs    | 211.0 µs                       |

El montículo casi no cambia de 100 a 2000 eventos; la lista se vuelve 20 veces más lenta.

**Requisito de 5.2 (menos de 20 ms entre dos decisiones del jugador):**

| Cripta sintética                  | Promedio por decisión | Peor decisión |
|-----------------------------------|-----------------------|---------------|
| 100 salas, 50 enemigos despiertos | 0.42 ms               | 0.54 ms       |
| 400 salas, 200 enemigos           | 1.8 ms                | 2.7 ms        |
| 900 salas, 500 enemigos           | 4.9 ms                | 7.1 ms        |

**Algo que encontramos midiendo:** antes, el peor caso cambiaba mucho de una corrida a otra (con 900 salas, entre 11 y 16 ms, y una vez llegó a 21 ms con 400). Midiendo las pausas del *recolector de basura* de Python (la parte de Python que libera la memoria que ya no se usa), vimos que unos 8 ms del peor caso eran esa pausa: cada tanto revisa todos los objetos, incluidos el mapa y las salas, que nunca se descartan. Ahora, después de cargar la cripta, el controlador le pide a Python que deje fuera de esas revisiones lo que ya está cargado (`gc.freeze()`). Con eso el peor caso con 900 salas bajó a unos 7 ms, lejos de los 20 ms.

### 6. Cuándo dejaría de servir

- Si casi todos los eventos se cancelaran, habría mucha basura; la reconstrucción lo controla, pero cuesta O(n) cuando pasa.
- Con muchos más de 500 enemigos despiertos a la vez nos acercaríamos a los 20 ms. El tiempo no se va en la agenda sino en todo lo que hace cada enemigo en su turno.

## 4.2 Traer el contenido antes de que haga falta (precarga)

### 1. El problema

Antes de entrar a una sala hay que tener su contenido (enemigos, objetos, trampas). Pedirlo al servidor tarda unos 400 ms, cuesta lo mismo pedir 1 sala que 10, y cada cripta tiene un presupuesto máximo de solicitudes. Si pedimos cada sala justo al entrar, el jugador espera en cada puerta.

Cuántas veces pasa: el jugador se mueve más o menos en 1 de cada 2 decisiones (en `cripta-04`, 42 movimientos en 93 decisiones), y la planificación corre 1 vez por decisión.

### 2. Opciones

- **Pedir cada sala al entrar:** una solicitud por sala y 400 ms de espera en cada puerta.
- **Pedir todo al empezar:** sirve si el presupuesto alcanza, pero gasta solicitudes en salas que quizá nunca se visitan y hace esperar al inicio.
- **Recorrido en anchura (BFS) desde la sala actual:** pedir en lotes de 10 las salas más cercanas que todavía no se han pedido, en segundo plano.

### 3. Qué escogimos

El BFS desde la sala actual, con una `ColaEnlazada`, y un `ConjuntoOrdenado` (un arreglo ordenado con búsqueda binaria, ver 4.3) para recordar qué salas ya se pidieron o ya están cargadas. La solicitud corre en otro hilo (otra “línea de ejecución”), así el juego no se congela mientras llega la respuesta. Además:

- Si al moverse falta la sala, se pide en ese momento junto con sus vecinas que no se han pedido (cuesta lo mismo).
- Cuando ya no queda nada por pedir, se deja de planificar.
- Lo que llega del servidor se guarda en disco: la próxima partida no gasta solicitudes en eso.
- La precarga anticipada nunca usa las últimas 2 solicitudes del presupuesto: quedan de reserva para lo obligatorio (el contenido de la sala a la que el jugador de verdad se mueve y sus fichas).
- Para que el replay funcione: las respuestas se meten al juego en el orden en que se pidieron y solo entre decisiones del jugador. Meter contenido no usa el azar ni números de secuencia, así que da igual en qué momento exacto llegue la respuesta.

### 4. Complejidad

- Saber si una sala ya se pidió: O(log n) (búsqueda binaria).
- Elegir el lote: el BFS se detiene apenas junta 10 salas. En el peor caso recorre todo el mapa, O(salas + salidas), pero eso solo pasa al final, cuando ya casi todo está pedido.

### 5. Lo que medimos

| Medición | Resultado |
|----|----|
| Elegir el lote, cripta de 100 / 2500 / 10 000 salas | 67 / 78 / 83 µs (con 100 veces más salas, solo un 23 % más: lo único que crece es la búsqueda binaria) |
| Solicitudes de contenido en las 4 criptas | **12 por lotes** contra **99** pidiendo cada sala visitada |
| Salas que ya estaban pedidas al momento de moverse | **95 de 99**. Las 4 que no son la sala inicial de cada cripta |
| Presupuesto usado con la API real, caché vacía | cripta-01 6/9, cripta-02 8/23, cripta-03 10/42, cripta-04 12/52 |
| Presupuesto usado si la caché en disco ya tiene todo | 3 solicitudes (lista, datos y versión del catálogo) |

Algo que encontramos midiendo: al principio el BFS recorría el mapa completo en cada decisión aun cuando ya no quedaba nada por pedir. Las búsquedas por id que se hacían en cada decisión crecían con el tamaño de la cripta (48 en la cripta de 6 salas, 269 en la de 50). Al agregar “si ya no hay nada que pedir, no planificar”, bajaron a 21–33 en todas.

### 6. Cuándo dejaría de servir

- La precarga trae también salas que el jugador nunca visita (en `cripta-04` trajo las 50 y visitó 42). Con un presupuesto muy justo convendría pedir solo las vecinas inmediatas; por ahora lo único que se protege es la reserva de 2 solicitudes.
- Con una red muy lenta y un jugador muy rápido, igual podría tocar esperar alguna vez. Nunca se entra a una sala sin contenido: en ese caso se espera.

## 4.3 Resolución de referencias del catálogo

### 1. El problema

El contenido de una sala no trae los datos de los enemigos u objetos, solo su id de tipo (por ejemplo, `ent_rata_gigante`). Antes de usarlos hay que conseguir su ficha (vida, ataque, peso…). Los id aparecen en desorden, se repiten entre salas y entre criptas, y no se puede pedir dos veces una ficha que ya tenemos.

Cuántas veces pasa: en todo el catálogo real hay 11 fichas distintas. Por partida, el programa hizo de 2 a 4 solicitudes de catálogo.

Además, para saber si una ficha ya la tenemos hay que buscar por id, y eso mismo se hace en todo el programa: encontrar una sala por su número, un enemigo por su id, un objeto del inventario por su id. Durante una partida real se hacen 21 a 33 búsquedas por decisión y unas 8 a 13 inserciones. Es lo que más se repite fuera de la agenda.

### 2. Opciones

- **Pedir cada ficha cuando hace falta**: 11 solicitudes por partida, cada una de 400 ms.
- **Juntar los id que faltan y pedirlos en lotes de 10**.
- Para buscar por id:
  - **Lista sin ordenar:** agregar al final es O(1), pero buscar obliga a recorrerla, O(n). Y como una tabla no puede tener claves repetidas, antes de agregar también hay que recorrerla para ver si la clave ya está.
  - **Arreglo ordenado con búsqueda binaria:** buscar es O(log n), pero agregar una clave nueva obliga a correr los elementos que van después.

### 3. Qué escogimos

Juntar los id que faltan y pedirlos en lotes de 10. Los pendientes van en un `ConjuntoOrdenado` (para no repetir) y en una `ColaEnlazada` (para mantener el orden). Antes de pedir uno se mira primero en memoria y después en disco. También se piden las fichas de lo que sueltan los enemigos al morir, porque esos objetos aparecen a mitad de la partida.

Para buscar por id usamos nuestra `TablaOrdenada`: dos arreglos, uno con las claves ordenadas y otro con el valor de cada clave en la misma posición.

- **Buscar:** búsqueda binaria. Se mira la clave del medio y se descarta la mitad donde no puede estar. Con 25 fichas son unas 5 comparaciones; con 1000 salas, unas 10.
- **Eliminar:** borrado perezoso, igual que en la agenda (4.1). La casilla se marca como borrada y no se corre nada. Cuando las casillas borradas son más que las vivas, el arreglo se compacta una vez.
- **Insertar:** si la clave ya estuvo (por ejemplo, soltar y volver a recoger el mismo objeto), se reutiliza su casilla. Si al lado de donde va hay una casilla borrada, también se reutiliza. Si no, hay que correr una casilla los elementos que siguen, como en cualquier arreglo.

¿Por qué no la lista sin ordenar? Agregar al final parece más barato, pero antes hay que revisar que la clave no esté, y eso obliga a recorrer la lista igual que al buscar. Así que en la lista buscar e insertar cuestan O(n), mientras que en el arreglo ordenado buscar es O(log n) e insertar corre elementos, cosa que Python hace muy rápido (en C). Además, en el juego se busca más de lo que se inserta (21–33 búsquedas contra 8–13 inserciones por decisión). De paso, recorrer la tabla da siempre las claves en el mismo orden, lo que ayuda al replay.

### 4. Complejidad

| Operación | Arreglo ordenado (lo nuestro) | Lista sin ordenar (descartada) |
|----|----|----|
| Buscar | O(log n) | O(n) |
| Eliminar | O(log n) (borrado perezoso) | O(n) (buscarla y correr los que siguen) |
| Insertar una clave que ya estuvo | O(log n) | O(n) (hay que buscarla para no repetirla) |
| Insertar una clave nueva | O(n) (correr el arreglo) | O(n) (recorrerla para no repetir la clave; agregarla al final es O(1)) |
| Recorrer en orden de clave | O(n), ya está ordenado | habría que ordenarla: O(n log n) |

Armar los lotes del catálogo: O(k), con k = ids pendientes.

### 5. Lo que medimos

| Claves guardadas | Buscar: arreglo ordenado | Buscar: lista sin ordenar (descartada) | Insertar: arreglo ordenado | Insertar: lista, sin repetir (descartada) |
|----|----|----|----|----|
| 25 (el tope de la caché) | 0.51 µs | 0.26 µs | 0.57 µs | 0.27 µs |
| 100 | 0.63 µs | 0.96 µs | 0.72 µs | 0.99 µs |
| 1000 | 0.99 µs | 9.5 µs | 1.14 µs | 9.7 µs |
| 5000 | 1.20 µs | 48.1 µs | 1.80 µs | 49.1 µs |

- Con 25 claves la lista es un poco más rápida, para buscar y para insertar, porque son muy pocas. Desde 100 claves gana el arreglo ordenado, y con 5000 es unas 40 veces más rápido para buscar y 27 veces para insertar: en la lista el costo crece igual que la cantidad de claves y en el arreglo ordenado casi no cambia.
- Con 21–33 búsquedas por decisión, todas juntas cuestan unos 30 µs, contra los 20 000 µs (20 ms) que permite el 5.2.
- Catálogo: de 2 a 4 solicitudes por partida, contra 11 pidiendo una por una. En la segunda partida, 0, porque todo sale de disco.

### 6. Cuándo dejaría de servir

- Si una cripta tuviera cientos de tipos distintos en las primeras salas, igual se pedirían en lotes de 10, pero habría más solicitudes al inicio.
- Con tablas de cientos de miles de claves y muchas claves nuevas todo el tiempo, correr el arreglo en cada inserción se notaría. En el juego se busca bastante más de lo que se inserta.
- Si se borra mucho y casi no se vuelve a insertar, la compactación cuesta O(n) cada vez que pasa (igual que la reconstrucción de la agenda).

## 4.4 Reutilización y caché persistente

### 1. El problema

En memoria solo caben 25 fichas (o lo que diga `--cache-size`). Cuando se llena, hay que soltar alguna. Las que están en uso (enemigo vivo, objeto en el inventario o en el suelo de la sala actual, trampa de la sala actual) no se pueden soltar. Lo que se suelta debe seguir en disco, y la caché tiene que sobrevivir al cerrar el programa.

Cuántas veces pasa (por decisión): ~1.2 búsquedas de ficha, ~0.7 “fijar” (una ficha empieza a estar en uso) y ~0.6 “liberar”. Buscar es lo más frecuente.

### 2. Opciones para decidir cuál soltar

- **LRU:** la que hace más tiempo que no se usa.
- **FIFO:** la que entró primero, aunque se use mucho.
- **LFU:** la que se ha usado menos veces.

### 3. Qué escogimos

LRU con “fijado”:

- Una `TablaOrdenada` va de la clave a la entrada. Buscar es una búsqueda binaria: con 25 fichas, unas 5 comparaciones.
- Una lista doblemente enlazada guarda solo las fichas que no están en uso, de la más reciente a la más vieja. Soltar es quitar la última, O(1).
- Cada entrada tiene un contador de referencias: `fijar` suma uno y la saca de la lista de candidatas; `liberar` resta uno y, si llega a 0, vuelve a ser candidata.

En disco va un archivo JSON por ficha y un `version.txt` con la versión del catálogo; si la versión cambia, se borra todo. El orden de búsqueda es memoria → disco → red.

### 4. Complejidad

Las tres políticas usan la misma tabla ordenada para buscar, así que solo cambia cómo eligen cuál soltar:

|  | LRU (lo nuestro) | FIFO | LFU |
|----|----|----|----|
| Buscar | O(log n) | O(log n) | O(log n) |
| Marcar como usada | O(1) (mover el nodo al frente de la lista doble) | no hace falta | O(1) |
| Elegir cuál soltar | O(1) (el último de la lista doble) | O(1) (el frente de una cola) | O(capacidad) en nuestra versión simple (O(log n) con un montículo) |

### 5. Lo que medimos

Porcentaje de aciertos (la ficha estaba en memoria) con la secuencia real de fichas que pidió el juego en las 4 criptas, y con una secuencia sintética de un catálogo grande (58 tipos, salas vecinas que comparten tipos):

| Caso                        | Capacidad | LRU        | FIFO   | LFU    |
|-----------------------------|-----------|------------|--------|--------|
| 4 criptas reales (11 tipos) | 2         | 68.3 %     | 67.0 % | 68.7 % |
| 4 criptas reales (11 tipos) | 4         | 78.9 %     | 78.0 % | 78.3 % |
| 4 criptas reales (11 tipos) | 6         | 82.7 %     | 81.8 % | 83.8 % |
| Catálogo grande (58 tipos)  | 10        | **92.1 %** | 88.8 % | 88.4 % |
| Catálogo grande (58 tipos)  | 25        | **98.5 %** | 98.0 % | 97.0 % |

| Recuperar una ficha          | Tiempo                                   |
|------------------------------|------------------------------------------|
| Desde memoria                | 0.78 µs                                  |
| Desde disco (ficha liberada) | 128 µs                                   |
| Desde la red                 | ~400 000 µs (400 ms, según el enunciado) |

Siendo honestos: con el catálogo real (solo 11 tipos) las tres políticas dan casi lo mismo, y con el tope por defecto de 25 la caché nunca se llenó (0 desalojos en las partidas medidas). La LRU se nota cuando el catálogo es más grande que la caché, como podría pasar con la cripta de la revisión, y además marcar y elegir cuál soltar son O(1). También probamos con una caché de solo 2 y 3 fichas que nunca se suelte una ficha en uso (`tests/test_integracion.py`).

### 6. Cuándo dejaría de servir

- Si todas las fichas en memoria están en uso, la caché se pasa del tope por un rato, porque no se puede soltar nada.
- Si el juego pidiera fichas totalmente al azar, sin repetir salas ni tipos, ninguna política ayudaría mucho.

## 4.5 Inventario

### 1. El problema

El inventario tiene que permitir:

- recorrerlo hacia adelante y hacia atrás desde un “cursor” (el objeto que se está viendo);
- soltar el objeto que se ve, esté donde esté, sin que el costo dependa de su posición;
- al equipar algo, moverlo al frente;
- mostrar vistas ordenadas por peso, valor o nombre sin cambiar el orden real;
- respetar el máximo `inventario_max`.

Además, el replay identifica los objetos por id, no por posición.

Cuántas veces pasa: el bot agregó de 0.1 a 0.3 objetos por decisión y movió al frente casi nunca. Es una estructura chica (máximo 10 objetos en todas las criptas) y se usa poco.

### 2. Opciones

- **`list` de Python:** soltar en la posición i y mover al frente corren los demás elementos, O(n).
- **Lista simple enlazada:** no se puede ir hacia atrás, y para quitar un nodo hay que encontrar el anterior, O(n).
- **Lista doblemente enlazada + tabla id → nodo.**

### 3. Qué escogimos

La lista doblemente enlazada “de libro”: cada nodo apunta al anterior y al siguiente, y la lista guarda un puntero al primero y otro al último (el primero no tiene anterior y el último no tiene siguiente). Al lado va una `TablaOrdenada` que lleva del id del objeto a su nodo, y un nodo cursor que marca el objeto que se está viendo.

Para soltar o equipar un objeto por su id, primero se encuentra su nodo con búsqueda binaria y después se desengancha o se mueve al frente cambiando solo unos pocos enlaces. Cada nodo además sabe en qué lista está, así se comprueba en O(1) que el nodo es de esta lista antes de tocarlo.

Las vistas ordenadas copian la lista y la ordenan con nuestro `ordenar`; el orden real no se toca.

### 4. Complejidad

| Operación | Lista doble + tabla ordenada | `list` |
|----|----|----|
| Soltar por id | O(log n) para encontrar el nodo + O(1) para desengancharlo | O(n) para encontrarlo + O(n) para correr los que siguen |
| Equipar (mover al frente) | O(log n) + O(1) | O(n) |
| Avanzar / retroceder el cursor | O(1) | O(1) |
| Vista ordenada | O(n log n) sobre una copia | igual |

Lo importante: en la lista doble ninguna de esas operaciones depende de la posición del objeto. Lo único que crece con el tamaño es la búsqueda binaria del id.

### 5. Lo que medimos

Soltar y volver a recoger, y mover al frente, en posiciones al azar:

| Objetos | Lista doble | `list` (descartada) |
|---------|-------------|---------------------|
| 10      | 1.6 µs      | 0.08 µs             |
| 1000    | 3.1 µs      | 0.23 µs             |
| 10 000  | 4.0 µs      | 1.6 µs              |
| 100 000 | 5.0 µs      | 15.8 µs             |

Y lo que pide el enunciado directamente: soltar el objeto que está en una posición y volver a ponerlo ahí, con 10 000 objetos:

| Posición del objeto | Lista doble | `list` (descartada) |
|---------------------|-------------|---------------------|
| Al inicio           | 7.2 µs      | 3.0 µs              |
| En el medio         | 8.0 µs      | 1.5 µs              |
| Al final            | 8.3 µs      | 0.06 µs             |

Hay que decirlo claro: con 10 objetos la `list` es más rápida, porque mover elementos lo hace en C, mientras que nuestra lista está escrita en Python. Escogimos la lista doble porque el enunciado pide que el costo no dependa de la posición, y eso muestra la segunda tabla: en la lista doble cuesta casi lo mismo en cualquier posición, mientras que en la `list` soltar el primero cuesta 50 veces más que soltar el último. Con 100 000 objetos la `list` ya es 3 veces más lenta.

Una nota: la primera versión del arreglo ordenado corría los elementos al borrar y con 10 000 objetos el costo cambiaba según el id (7 µs a 15 µs). Por eso le pusimos borrado perezoso: al soltar y volver a recoger el mismo objeto, su casilla se reutiliza y no se corre nada.

### 6. Cuándo dejaría de servir

- Con inventarios tan chicos, si solo importara la velocidad, la `list` ganaría.
- La lista doble usa más memoria por objeto: cada nodo guarda dos enlaces y la lista a la que pertenece.
- Encontrar el nodo por id cuesta O(log n): crece un poco con el tamaño del inventario, aunque no con la posición.

## 4.6 Pergaminos de retroceso (historial)

### 1. El problema

Un pergamino deshace la última acción del jugador y todo lo que pasó después hasta su siguiente decisión: ataques de enemigos, veneno, el reloj, los eventos, el rastro, la vida, el inventario, el suelo, las puertas, las trampas… Se pueden deshacer como máximo 5 acciones. Está prohibido guardar copias completas del estado, y la cantidad de pergaminos no se revierte.

Cuántas veces pasa: en las partidas reales se registran unos 14–15 cambios por decisión; en la cripta sintética grande, unos 3359. Deshacer solo pasa cuando se usa un pergamino (poco).

### 2. Opciones

- **Copia completa del estado en cada decisión:** prohibida, pero la medimos para comparar.
- **Volver a jugar desde el inicio** con el replay hasta la acción anterior: cada retroceso costaría tanto como toda la partida.
- **Bitácora de deshacer:** guardar solo cómo deshacer cada cambio.

### 3. Qué escogimos

La bitácora de deshacer. Cada vez que el juego cambia algo, registra un “cambio” chiquito:

- “el atributo `vida` de este enemigo valía 12”;
- “se programó este evento” / “se sacó” / “se canceló”;
- “este nodo se quitó de la lista y estaba después de este otro”;
- “este objeto salió del inventario”.

Los cambios de una decisión forman un intervalo, y dentro del intervalo funcionan como una pila: retroceder es sacarlos del último al primero, deshaciendo cada uno. Los últimos 5 intervalos se guardan en un `BufferCircular` de 5: al agregar el sexto, se pierde el más viejo.

Detalles:

- Los nodos de las listas se vuelven a enganchar en su posición exacta, en O(1).
- Los pergaminos y la caché no se registran. Las fichas en uso se recalculan después de retroceder.
- También se restaura el estado del generador de azar, así repetir la misma acción da el mismo resultado.

### 4. Complejidad

- Registrar un cambio: O(1).
- Deshacer: O(cambios del intervalo), sin importar el tamaño de la cripta.
- Memoria: solo los cambios de las últimas 5 acciones.

### 5. Lo que medimos

| Caso | Costo |
|----|----|
| Registrar y deshacer, por cambio (10 / 100 / 1000 cambios por intervalo) | 0.38 / 0.32 / 0.32 µs |
| Una decisión típica de una partida real (~15 cambios) | ~5 µs |
| Copia completa por decisión (prohibida), 100 salas | 208 µs |
| Copia completa por decisión (prohibida), 900 salas | 2053 µs |

Además, una prueba automática juega cientos de partidas al azar y, después de cada acción, deshace y comprueba que el estado quede idéntico al de antes (`tests/test_modelo.py`).

### 6. Cuándo dejaría de servir

Si una sola acción cambiara casi todo el estado (por ejemplo, 500 enemigos actuando a la vez), la bitácora quedaría casi del tamaño de una copia. En la cripta sintética grande ya pasa algo así: 3359 cambios cuestan ~1.1 ms, cerca de la copia completa (2.1 ms), aunque la copia igual estaría prohibida y ocuparía 5 veces más memoria.

## 4.7 El rastro del jugador

### 1. El problema

Un enemigo rastreador mira solo las salas vecinas a la suya y se mueve hacia la que tenga el rastro del jugador más fresco, siempre que tenga menos de 400 unidades de antigüedad. Si empatan, va a la de menor id. Su decisión debe costar según las salidas de su sala, no según el tamaño de la cripta ni lo largo del recorrido del jugador.

Cuántas veces pasa: en la cripta sintética, unas 251 decisiones de rastreador por decisión del jugador. En las partidas reales del bot fueron 0. El bot siempre pelea primero, los rastreadores atacan cuando están con el jugador, y los de otras salas siguen dormidos hasta que uno entra.

### 2. Opciones

- **Guardar el recorrido del jugador** como una lista de (sala, tiempo) y buscar ahí el rastro de cada vecina.
- **Que cada sala guarde un solo número:** la última vez que el jugador estuvo ahí.
- Para el rastro viejo: borrarlo activamente (con un evento por sala) o revisarlo al consultarlo.

### 3. Qué escogimos

Cada sala guarda un entero con su último rastro. El rastreador revisa sus como mucho 4 vecinas. El rastro viejo no se borra: al consultarlo se revisa si `reloj - rastro < 400`. Borrarlo activamente agregaría un evento por cada sala visitada (más trabajo para la agenda y para el retroceso) y no cambiaría ninguna decisión.

### 4. Complejidad

- Lo nuestro: O(salidas de la sala) = O(4).
- Con la lista del recorrido: O(largo del recorrido).

### 5. Lo que medimos

| Decisión de un rastreador                    | Tiempo  |
|----------------------------------------------|---------|
| Cripta de 100 salas                          | 0.61 µs |
| Cripta de 2500 salas                         | 0.66 µs |
| Cripta de 10 000 salas                       | 0.67 µs |
| Recorrido como lista (descartada), 100 pasos | 9.4 µs  |
| Recorrido como lista, 1000 pasos             | 92 µs   |
| Recorrido como lista, 10 000 pasos           | 929 µs  |

Con varios rastreadores, el trabajo crece igual que la cantidad de rastreadores que actúan, porque cada uno cuesta lo mismo.

### 6. Cuándo dejaría de servir

Funciona con cualquier tamaño de cripta. Solo dejaría de servir si las reglas pidieran que el rastreador conozca el mapa completo y busque rutas, cosa que el enunciado prohíbe.

## 4.8 Bitácora en pantalla

### 1. El problema

En pantalla se muestran solo los últimos 20 mensajes. La memoria tiene que quedar fija toda la partida, y agregar un mensaje no puede correr los 19 anteriores.

Cuántas veces pasa: unos 2 mensajes por decisión en las criptas reales, y 6.5 en la sintética.

### 2. Opciones

- **`list` con `append` + `pop(0)`:** corre todos los mensajes cada vez, justo lo que se prohíbe.
- **`ColaEnlazada`:** crea un nodo por mensaje, así que la memoria no queda fija.
- **Buffer circular.**

### 3. Qué escogimos

**Un buffer circular:** un arreglo de 20 espacios que se crea una sola vez, más el índice del mensaje más viejo. Cuando está lleno, el mensaje nuevo ocupa el lugar del más viejo y el índice avanza “dando la vuelta” (con `% 20`). Es una cola hecha sobre un arreglo, no una lista enlazada circular: lo “circular” es solo cómo se mueve el índice. Cada mensaje lleva un número correlativo; con eso la pantalla separa “Tu turno” de “Turno de los enemigos” sin guardar nada extra.

### 4. Complejidad

Agregar: O(1). Memoria: siempre 20 espacios.

### 5. Lo que medimos

| Capacidad | Buffer circular | `list` + `pop(0)` (descartada) |
|-----------|-----------------|----------------------------------|
| 20        | 0.19 µs         | 0.08 µs                          |
| 2000      | 0.21 µs         | 0.24 µs                          |
| 20 000    | 0.21 µs         | 1.64 µs                          |

Con 20 mensajes la `list` es más rápida (otra vez, porque corre los elementos en C), pero sí corre los 19 anteriores, y eso lo prohíbe el enunciado. El buffer cuesta lo mismo sin importar la capacidad.

### 6. Cuándo dejaría de servir

Solo si hubiera que guardar todos los mensajes de la partida; para eso ya existe la bitácora de replay (4.11).

## 4.9 Ordenamiento

### 1. El problema

El programa ordena en varios lugares:

- la tabla de puntajes;
- las vistas del inventario (por peso, valor o nombre);
- el índice del archivo de guardado (salas por id);
- el orden en que se activan los enemigos (por id).

Hay que tener al menos dos algoritmos distintos y que el programa escoja solo cuál usar, sin `sorted()` ni `.sort()`.

Cuántas veces pasa: en el juego normal, unas 0.3 ordenaciones por decisión, de listas chiquitas (de 1 a 3 elementos en promedio). Las listas más grandes son el índice del guardado (una entrada por sala) y la tabla de puntajes (crece con cada partida y casi siempre está casi ordenada).

### 2. Opciones

- **Inserción:** muy rápida con pocos elementos o con datos casi ordenados, pero O(n²) en el peor caso (datos al revés).
- **Mezcla (merge sort):** siempre O(n log n), pero hace más trabajo con listas chicas.
- **Quicksort:** lo descartamos porque no es *estable* (si dos elementos empatan, puede cambiarlos de orden). Necesitamos estabilidad para que las vistas y la activación de enemigos salgan siempre iguales.

### 3. Qué escogimos

Inserción y mezcla, las dos estables, con un selector automático que mira dos cosas que se pueden medir:

- **Tamaño:** con 32 elementos o menos, inserción.
- **Desorden:** con más de 32, se cuentan las “bajadas” (vecinos que están al revés). Si hay como mucho 2 log₂(n) bajadas, la lista está casi ordenada y va inserción; si no, mezcla. La idea: cada bajada le puede costar a la inserción mover hasta n elementos, y la mezcla cuesta más o menos n log₂(n) siempre.

Otra decisión importante: la clave se calcula una sola vez por elemento. Primero se arma una lista de pares (clave, elemento) y después se ordena comparando las claves ya calculadas.

La versión original del grupo usaba como límite 64 elementos, aceptaba hasta un 10 % de bajadas y calculaba la clave en cada comparación. Las mediciones nos hicieron cambiar las tres cosas.

### 4. Complejidad

|  | Mejor caso | Peor caso | Memoria extra |
|----|----|----|----|
| Inserción | O(n) (ya ordenada) | O(n²) | O(1) además de la copia |
| Mezcla | O(n log n) | O(n log n) | O(n) |
| Selector (contar bajadas + decorar) | O(n) extra | O(n) extra | O(n) |

### 5. Lo que medimos

Tiempo de una ordenación (µs):

| n   | Datos          | Inserción | Mezcla | Selector (lo que usa el programa) |
|-----|----------------|-----------|--------|-----------------------------------|
| 32  | aleatorios     | 21.1      | 31.0   | 21.3 (inserción)                  |
| 32  | al revés       | 37.6      | 26.1   | 37.1 (inserción)                  |
| 48  | aleatorios     | 43.3      | 49.9   | 52.7 (mezcla)                     |
| 48  | al revés       | 80.9      | 42.2   | 45.9 (mezcla)                     |
| 128 | aleatorios     | 268       | 156    | 165 (mezcla)                      |
| 128 | casi ordenados | 23.9      | 123    | 31.5 (inserción)                  |
| 128 | al revés       | 566       | 122    | 130 (mezcla)                      |
| 500 | aleatorios     | 4330      | 750    | 769 (mezcla)                      |
| 500 | casi ordenados | 171       | 577    | 203 (inserción)                   |

El selector no siempre escoge el más rápido, pero cuando se equivoca la diferencia es pequeña:

- Con 32 datos al revés escoge inserción (37 µs) y la mezcla habría tardado 26 µs.
- Contar las bajadas y calcular las claves le suma hasta un 30 % sobre el mejor de los dos (por ejemplo, 128 casi ordenados: 31.5 µs contra 23.9 µs).
- Lo importante es que nunca cae en el caso realmente malo: con 500 datos aleatorios, la inserción tardaría 4330 µs, casi 6 veces lo que tarda el selector (769 µs).

Comparaciones costosas (ordenar objetos por nombre, donde sacar el nombre cuesta algo, como en la vista del inventario):

| n | Clave una vez por elemento (lo nuestro) | Clave en cada comparación (versión original) |
|----|----|----|
| 10 | 11 µs | 30 µs |
| 50 | 97 µs | 1010 µs |
| 200 | 448 µs | 16 619 µs |

Calcular la clave una sola vez es hasta 37 veces más rápido.

### 6. Cuándo dejaría de servir

- Contar las bajadas cuesta un poco, aunque la lista ya esté ordenada.
- La mezcla usa memoria extra del tamaño de la lista; con listas gigantes eso podría importar.
- Los umbrales (32 y 2 log₂(n)) salieron de medir en esta computadora; en otra podrían moverse un poco.

## 4.10 Guardado binario de la partida

### 1. El problema

Guardar la partida en un archivo binario de formato propio. Al cargar tiene que poder leerse una sala sin leer todo el archivo, hay que detectar si el archivo es de otra versión del formato, y hay que comparar contra guardar lo mismo en JSON.

Cuántas veces pasa: solo cuando el jugador escribe `guardar` o `cargar`.

### 2. Opciones

- **JSON:** fácil y se puede leer a ojo, pero ocupa más y, para sacar una sala, hay que leer todo el archivo.
- **`pickle` de Python:** no es un formato propio y no permite leer una sola sala.
- **Binario propio con un índice al final.**

### 3. Qué escogimos

Un binario propio (con el módulo `struct`):

```
[encabezado] "CRPT" | versión del formato | cantidad de salas | dónde empieza el índice
[global]     versiones, semilla, azar, reloj, jugador, efectos, eventos...
[salas]      un bloque por sala, ordenados por id
[índice]     (id de sala, dónde empieza, cuánto mide) ordenado por id
```

Para cargar una sala se lee el encabezado, se salta al índice, se busca la sala con búsqueda binaria y se lee solo ese bloque. Si la “versión del formato” no coincide, el archivo se rechaza con un mensaje claro.

### 4. Complejidad

- Cargar una sala: leer el índice O(salas) (16 bytes por sala) + búsqueda binaria O(log salas) + leer un bloque.
- Cargar todo: O(tamaño del archivo).

### 5. Lo que medimos

| Estado guardado | Formato | Tamaño | Guardar | Cargar todo | Cargar UNA sala |
|----|----|----|----|----|----|
| Partida real en cripta-04 (50 salas) | binario | **11.5 KB** | **0.5 ms** | 0.32 ms | **0.10 ms** |
|  | JSON | 28.1 KB | 1.4 ms | 0.31 ms | (hay que leer todo) |
| Sintética (900 salas, 500 enemigos) | binario | **112 KB** | **2.9 ms** | 3.9 ms | **0.24 ms** |
|  | JSON | 406 KB | 16.8 ms | 3.9 ms | (hay que leer todo) |

El binario ocupa entre 2.4 y 3.6 veces menos y se guarda entre 2.8 y 5.8 veces más rápido. Cargar el archivo completo tarda lo mismo en los dos formatos: el lector de JSON de Python está escrito en C, y el nuestro, aunque lee menos bytes, está escrito en Python. La ventaja fuerte del binario es leer una sola sala: 0.24 ms contra 3.9 ms de cargar todo.

### 6. Cuándo dejaría de servir

- Con criptas gigantes, leer el índice completo para buscar una sala crece con la cantidad de salas. Se podría hacer la búsqueda binaria directamente sobre el archivo (cada entrada mide lo mismo, 16 bytes) y leer solo unas pocas entradas.
- Para cargar partidas completas no le ganamos a JSON. Si eso fuera lo importante, convendría optimizar nuestro lector (por ejemplo, leer el bloque entero de una vez y descomponerlo con `struct.unpack_from`).

## 4.11 Bitácora de partida y reproducción (replay)

### 1. El problema

Cada acción del jugador se anota en un archivo de texto al que solo se le agregan líneas al final. El encabezado lleva el id y la versión de la cripta, la versión del catálogo y la semilla. Con `--replay archivo.log` se reproduce la partida completa sin que nadie juegue. Si las versiones ya no coinciden, hay que avisar y no reproducir con datos distintos.

Cuántas veces pasa: una línea por cada acción aceptada (se escribe y se guarda en disco enseguida).

### 2. Opciones

- **Guardar el estado completo después de cada acción:** enorme, y muy parecido a la copia completa que ya descartamos.
- **Guardar solo la semilla y la lista de acciones:** pequeño, pero solo funciona si el juego hace exactamente lo mismo cada vez que recibe las mismas acciones.

### 3. Qué escogimos

Semilla + acciones. Para que el juego dé siempre lo mismo:

- Todo el azar sale de un `random.Random(semilla)` propio del juego.
- Los eventos se ordenan por (hora, número de secuencia).
- Las salidas se revisan siempre en orden N, S, E, O.
- El juego decide recorriendo sus propias listas (salidas en orden N, S, E, O; enemigos de la sala). Las tablas de búsqueda son arreglos ordenados: si se recorren, salen siempre en el mismo orden.
- Las respuestas del servidor se meten al juego en puntos fijos.
- Los ids de los objetos se generan siempre igual.
- Las acciones nombran a los enemigos y objetos por su id, no por su posición en pantalla.

Cada partida crea su propio archivo de log. Si se carga una partida guardada, el log de esa sesión se cierra, porque un log siempre empieza desde el inicio con su semilla.

### 4. Complejidad

Anotar una acción: O(1). Reproducir: O(acciones del log), porque se vuelve a jugar todo.

### 5. Lo que comprobamos

- Una partida jugada contra la API real se reprodujo con el mismo resultado (derrota en t=223), tanto en línea como sin red (`--offline`).
- Las pruebas (`tests/test_integracion.py` y `tests/test_modelo.py`) reproducen partidas y comparan el estado final, que sale idéntico.
- Además, jugamos la misma partida (bot en `cripta-04`, 98 decisiones, caché de solo 3 fichas para forzar desalojos) con distintos valores de `PYTHONHASHSEED` (lo que hace cambiar el `hash()` de Python): el estado final guardado fue idéntico byte por byte.
- Un log con una versión de cripta distinta se rechaza con el mensaje “No se puede garantizar una reproducción fiel” y el programa termina con código 2.

### 6. Cuándo dejaría de servir

- Si el servidor publica una versión nueva de la cripta y no queda una copia local de la vieja, ese log ya no se puede reproducir (el programa lo avisa).
- Reproducir una partida muy larga cuesta lo mismo que volver a jugarla.
- Si se cambiara la versión de Python, el generador de azar podría dar otros números en algunas funciones; conviene reproducir con la misma versión.
