# Research: Niebla de guerra e «ir a»

## R1. Representar el estado de cada sala

**Decisión**: un arreglo `estado_sala` de V enteros (0, 1, 2) indexado por
`Sala.indice` (posición en el esqueleto, asignada una vez al construir el mapa).

**Por qué**: la consulta ocurre en cada vista, en cada paso de «ir a» y en cada
actualización por antorcha (§5.3); con un arreglo cuesta O(1) sin importar
cuánto se conoce. El mapa completo ya está en memoria (esqueleto), así que el
arreglo no agrega más que V enteros pequeños.

**Alternativas**: lista de ids explorados (consulta O(k)); `TablaOrdenada` de
ids (O(log k) e inserción O(k) por desplazamiento); `set` (prohibido).

## R2. Avistada: guardarla o calcularla

**Decisión**: guardarla. Al explorar una sala se recorren sus salidas y cada
destino en 0 pasa a 1. Como una sala avistada nunca vuelve a desconocida
(salvo por retroceso, que restaura el valor exacto anterior), no hace falta un
contador de "cuántas exploradas la ven".

**Alternativa**: calcularla en cada consulta recorriendo las entradas de la
sala (O(grado de entrada)); más barata de registrar, pero la consulta deja de
ser O(1).

## R3. Memoria de puertas

**Decisión**: arreglo `recuerdo_puerta` de P enteros (0 sin observar, 1
abierta, 2 cerrada) por `Puerta.indice`. Se observa al entrar a una sala
(todas sus puertas) y cuando una puerta de la sala actual cambia (lo hace
`_abrir` o `cerrar_puerta`, que ya saben dónde está el jugador). Un pasaje sin
puerta se considera siempre abierto.

## R4. Antorcha

Al entrar a una sala con la antorcha encendida, se exploran sus vecinas por
**todas** las salidas. Explorar no toca enemigos, trampas ni contenido (no se
llama a la activación de enemigos ni se pide contenido a la red). Las puertas
de las vecinas que no conectan con la sala actual quedan sin observar
(clarify).

**Información mínima para revertir la exploración de cinco salas**: por cada
sala revelada, su valor anterior (1 entero) y el de cada destino que pasó de
desconocido a avistado; por cada puerta observada, su recuerdo anterior. Nada
más (ni copias del mapa ni listas de salas).

## R5. Guardar, revertir y reconstruir

- **Retroceso**: cada cambio de casilla pasa por `Juego._asignar_casilla`, que
  registra `CambioCasilla` si el historial está grabando. Revertir restaura en
  orden inverso.
- **Guardado**: `EstadoGuardable.conocimiento` es un texto con un dígito por
  sala (en orden del esqueleto), `|` y un dígito por puerta. Determinista y
  compacto (V + P + 1 bytes).
- **Línea de tiempo**: como el conocimiento está en el estado, cada punto de
  control lo incluye y la re-simulación lo vuelve a producir. `historia`
  muestra las salas exploradas y la cantidad de avistadas.

## R6. Qué ve la interfaz

La vista pide al modelo un "mapa conocido" (lista de salas exploradas con sus
salidas: dirección, costo, puerta recordada y destino si está explorado) y la
cantidad de avistadas. En la sala actual, el destino de una salida se muestra
con nombre solo si está explorado; si no, "sala sin explorar".

## R7. «ir a»: ¿misma búsqueda que el cazador?

**Decisión**: mismo motor (`BuscadorRutas`) y misma regla de primer paso, con:

- otro filtro: la salida va de una sala explorada a otra explorada y su puerta
  se recuerda abierta (o no tiene puerta);
- otra instancia del buscador (no comparte caché con los cazadores);
- búsqueda inversa desde el destino, detenida en cuanto se finaliza la sala del
  jugador.

**Por qué compartir**: el problema es el mismo (costo mínimo hacia un
objetivo con el mismo desempate); duplicar el código duplicaría errores. **Por
qué separar la instancia**: el conocimiento cambia en cada paso y el objetivo
es otro; mezclarla con la caché de los cazadores la invalidaría en cada paso.

El bucle de pasos vive en el controlador para que cada paso sea un `MOVER`
normal: asegura el contenido de la sala destino (precarga), entra a la línea
de tiempo y al `partida.log` como cualquier acción, y el pergamino revierte
solo el último. Las condiciones de parada se revisan después de cada paso:
partida terminada, llegada, enemigos en la sala, daño (vida menor que al
empezar el paso), sin ruta conocida o paso rechazado.

## R8. Comentario en `partida.log`

`EscritorReplay.comentario("ir a 12")` escribe `# ir a 12`; `LectorReplay`
ignora las líneas que empiezan con `#`. No cambia el encabezado ni las líneas
de acción, así que los logs de la Parte I se siguen leyendo.
