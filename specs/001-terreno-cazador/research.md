# Research: Terreno y cazador

## R1. ¿Una búsqueda por cazador o una desde el jugador?

**Decisión**: búsqueda de costo mínimo **desde la sala del jugador sobre las
salidas de entrada** (sentido inverso). Da `dist(v, jugador)` para todas las
salas a la vez; cada cazador solo lee las distancias de sus vecinas.

**Por qué**: todos los cazadores persiguen al mismo objetivo (§5.1). Con N
cazadores, N búsquedas desde cada cazador repiten casi el mismo trabajo; una
búsqueda inversa lo hace una vez. Además la regla de desempate se escribe en
términos de `dist(v, jugador)` (§3.2), que es exactamente lo que produce la
búsqueda inversa.

**Alternativas**:
- *Una búsqueda por cazador, desde su sala*: costo proporcional a la región
  dentro de su rango y se detiene al llegar al jugador; gana si hay un solo
  cazador con rango pequeño y lejos de todo. Se conserva como estrategia
  `INDIVIDUAL` para medir.
- *Precalcular todos los pares*: O(V·(V+E) log V) memoria y tiempo; inútil
  porque las puertas cambian.

**Salidas de un solo sentido**: como la búsqueda va en sentido inverso, se
recorren las **entradas** de cada sala (las salidas que llegan a ella), así que
una salida sin regreso se respeta.

## R2. Escoger la siguiente sala a examinar

**Decisión**: `MonticuloMin` de la Parte I con **borrado perezoso** (se insertan
duplicados y se descartan al salir si ya estaban finalizados). La clave es un
entero `dist * n + índice`: una sola comparación de enteros en lugar de tuplas.

**Alternativas**: búsqueda lineal del mínimo en cada paso (O(V²)); montículo
indexado con disminución de clave (más código, cada intercambio actualiza
posiciones; el borrado perezoso ya funcionó en la agenda de la Parte I).

## R3. Registrar distancias

**Decisión**: arreglos de tamaño V (uno de distancias y uno de marcas)
indexados por la posición de la sala en el esqueleto (`Sala.indice`). Cada
búsqueda incrementa un contador de **generación**; una distancia solo vale si su
marca coincide con la generación actual. Así una búsqueda pequeña no paga
O(V) por reiniciar el arreglo, que es lo que exige §5.1 para rangos pequeños.

**Alternativas**: `TablaOrdenada` por id de sala (O(log V) por acceso); crear
arreglos nuevos en cada búsqueda (O(V) aunque la búsqueda toque 5 salas).

## R4. Cumplir el desempate con cualquier algoritmo

**Decisión**: separar "calcular distancias" de "elegir el paso". La búsqueda
solo calcula distancias exactas; el paso se elige después recorriendo las
salidas de la sala del cazador en orden N, S, E, O y quedándose con la vecina
de menor id que cumple `costo(u,v) + dist(v) = d` (y, para la misma vecina, la
primera salida). Así el resultado no depende del orden en que el montículo
saca salas con distancias empatadas.

Solo se usan distancias **finalizadas**: una vecina que cumpla la igualdad
tiene `dist(v) < d` (los costos son ≥ 1) y por lo tanto ya se finalizó antes que
`u`.

## R5. Acotar por rango

**Decisión**: la búsqueda se detiene cuando la menor distancia pendiente supera
el alcance pedido. Con la estrategia compartida, el alcance es el mayor rango
de los cazadores que han decidido (si llega uno con rango mayor, se rehace con
ese alcance). Es exacto: si `d ≤ rango ≤ alcance`, todas las salas de la ruta
tienen distancia ≤ alcance y quedaron finalizadas.

## R6. Costo de un pasaje

**Decisión**: igual que con las puertas de la Parte I, el costo es uno por
pasaje: vale el primero no nulo entre la ida (en el orden del esqueleto) y la
vuelta; ausente en los dos lados ⇒ 100. Un costo no entero o < 1 lanza
`ValueError` con la sala y la dirección (clarify).

## R7. Mediciones planificadas

`--bench cazador` (en `bench/bench_rutas.py`), criptas sintéticas deterministas:
cuadrículas de 400, 2 500 y 10 000 salas con costos aleatorios en [20, 300]
(semilla fija), el jugador recorriendo la cripta con una caminata determinista
y los cazadores activos.

| Caso | Variable |
|---|---|
| 1 vs. 10 vs. 50 cazadores | cantidad |
| rango 300 vs. rango 10⁶ | alcance |
| compartido vs. individual | estrategia |
| montículo vs. mínimo lineal | estructura auxiliar |
| ciclo en la cripta de referencia | límite 20 ms (mediana, p95, máximo) |

Se reportan mediana de 5 repeticiones y salas examinadas por decisión.
