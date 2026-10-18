"""Benchmarks de datos, caché y persistencia.                         [Persona B]

Evidencia para las secciones §4.2, §4.3, §4.4, §4.9 y §4.10 del Documento de
Decisiones. Cada caso devuelve un ``ResultadoMedicion``; ``repeticiones`` es
la cantidad de operaciones medidas, así que la última columna es el costo de
UNA operación. Cuando el dato importante no es el tiempo (tasa de aciertos,
tamaño en disco, solicitudes), va escrito en el nombre del caso.
"""

from __future__ import annotations

import os
import random
import shutil
import tempfile
import time

from cripta.estructuras.cola import ColaEnlazada
from cripta.estructuras.lru import CacheAcotada
from cripta.estructuras.ordenamiento import ordenar, ordenar_con_algoritmo
from cripta.estructuras.tabla_ordenada import ConjuntoOrdenado, TablaOrdenada


def registrar(registro) -> None:
    """Agrega todos los casos de este archivo al registro."""
    # §4.3 buscar por clave: arreglo ordenado (el del programa) vs lista sin ordenar (descartada)
    for n in (25, 100, 1000, 5000):
        for estructura in ("ordenada", "lineal"):
            registro.agregar("busqueda", f"buscar {estructura} n={n}", lambda n=n, e=estructura: bench_busqueda(e, n))
            registro.agregar("busqueda", f"insertar {estructura} n={n}", lambda n=n, e=estructura: bench_insercion(e, n))
    for n in (100, 1000, 5000, 50_000):
        registro.agregar("cola", f"enlazada n={n}", lambda n=n: bench_cola_enlazada(n))
        registro.agregar("cola", f"pop0 n={n}", lambda n=n: bench_cola_pop0(n))
    # §4.9 ordenamiento
    for n in (16, 32, 48, 64, 128, 500, 5000):  # alrededor del umbral (32) y tamaños grandes
        for patron in ("aleatorio", "casi_ordenado", "inverso"):
            for algoritmo in ("insercion", "mezcla", "selector"):
                if n == 5000 and algoritmo == "insercion" and patron != "casi_ordenado":
                    continue  # tarda demasiado y no aporta (O(n²) con 5000 elementos)
                registro.agregar("ordenamiento", f"{algoritmo} {patron} n={n}",
                                 lambda n=n, p=patron, a=algoritmo: bench_ordenamiento(a, n, p))
    for n in (10, 50, 200):
        registro.agregar("ordenamiento", f"clave costosa n={n}", lambda n=n: bench_orden_clave_costosa(n, False))
        registro.agregar("ordenamiento", f"clave por comparación n={n}", lambda n=n: bench_orden_clave_costosa(n, True))
    # §4.4 caché
    for n in (100, 1000):
        registro.agregar("cache", f"hit n={n}", lambda n=n: bench_cache_busqueda(n, True))
        registro.agregar("cache", f"miss n={n}", lambda n=n: bench_cache_busqueda(n, False))
    for capacidad in (2, 4, 6):
        for politica in ("LRU", "FIFO", "LFU"):
            registro.agregar("cache", f"{politica} real cap={capacidad}",
                             lambda c=capacidad, p=politica: bench_politica_desalojo(p, c, "real"))
    for capacidad in (10, 25):
        for politica in ("LRU", "FIFO", "LFU"):
            registro.agregar("cache", f"{politica} catálogo grande cap={capacidad}",
                             lambda c=capacidad, p=politica: bench_politica_desalojo(p, c, "sintetica"))
    registro.agregar("cache", "ficha desde memoria", lambda: bench_recuperacion("memoria"))
    registro.agregar("cache", "ficha desde disco", lambda: bench_recuperacion("disco"))
    # §4.2 precarga
    for salas in (100, 2500, 10_000):
        registro.agregar("precarga", f"elegir lote salas={salas}", lambda s=salas: bench_seleccion_lote(s))
    registro.agregar("precarga", "solicitudes por lotes vs por sala", bench_solicitudes_precarga)
    # §4.10 guardado
    # "real": una partida del bot en la cripta más grande de datos_ejemplo/.
    for origen in ("real", "sintetica-900"):
        for formato in ("binario", "json"):
            registro.agregar("guardado", f"{formato} {origen}", lambda f=formato, o=origen: bench_guardado(f, o))
        registro.agregar("guardado", f"una sala {origen}", lambda o=origen: bench_cargar_una_sala(o))


# --- §4.3 / §4.4 búsquedas -------------------------------------------------------

def _resultado(subsistema: str, caso: str, n: int, repeticiones: int, segundos: float):
    from cripta.bench.runner import ResultadoMedicion

    return ResultadoMedicion(subsistema, caso, n, repeticiones, segundos)


_NOMBRES_ESTRUCTURA = (
    ("ordenada", "TablaOrdenada (arreglo + búsqueda binaria)"),
    ("lineal", "lista sin ordenar, sin repetir (descartada)"),
)


def _nombre_estructura(estructura: str) -> str:
    for clave, nombre in _NOMBRES_ESTRUCTURA:
        if clave == estructura:
            return nombre
    return estructura


def _claves_desordenadas(elementos: int) -> list[str]:
    """Ids como los del juego ("e-123"), en un orden revuelto pero siempre igual."""
    claves = [f"e-{i}" for i in range(elementos)]
    random.Random(11).shuffle(claves)
    return claves


def bench_busqueda(estructura: str, elementos: int):
    """Buscar por clave (§4.3/§4.4): "ordenada" (la del programa) o "lineal" (recorrer una lista, descartada)."""
    claves = _claves_desordenadas(elementos)
    repeticiones = max(5, 20_000 // elementos) if estructura != "lineal" else 5
    if estructura == "lineal":
        lista = list(claves)
        inicio = time.perf_counter()
        for _ in range(repeticiones):
            for clave in claves:
                for actual in lista:
                    if actual == clave:
                        break
        segundos = time.perf_counter() - inicio
    else:
        tabla: TablaOrdenada[str, str] = TablaOrdenada()
        for clave in claves:
            tabla.insertar(clave, clave)
        inicio = time.perf_counter()
        for _ in range(repeticiones):
            for clave in claves:
                tabla.obtener(clave)
        segundos = time.perf_counter() - inicio
    return _resultado("busqueda", f"buscar en {_nombre_estructura(estructura)}, {elementos} claves", elementos,
                      repeticiones * elementos, segundos)


def bench_insercion(estructura: str, elementos: int):
    """Costo de INSERTAR una clave nueva sin repetirla.

    Arreglo ordenado: buscar el lugar y correr los elementos que siguen.
    Lista sin ordenar: agregar al final es O(1), pero una tabla no puede tener
    claves repetidas, así que antes hay que recorrerla para ver si ya está.
    """
    claves = _claves_desordenadas(elementos)
    repeticiones = max(3, 20_000 // elementos) if estructura == "ordenada" else max(1, 2_000 // elementos)
    inicio = time.perf_counter()
    for _ in range(repeticiones):
        if estructura == "ordenada":
            tabla: TablaOrdenada[str, str] = TablaOrdenada()
            for clave in claves:
                tabla.insertar(clave, clave)
        else:
            lista: list[str] = []
            for clave in claves:
                repetida = False
                for actual in lista:
                    if actual == clave:
                        repetida = True
                        break
                if not repetida:
                    lista.append(clave)
    return _resultado("busqueda", f"insertar en {_nombre_estructura(estructura)}, {elementos} claves", elementos,
                      repeticiones * elementos, time.perf_counter() - inicio)


def bench_cola_enlazada(elementos: int):
    inicio = time.perf_counter()
    for _ in range(5):
        cola: ColaEnlazada[int] = ColaEnlazada()
        for i in range(elementos):
            cola.encolar(i)
        while not cola.esta_vacia():
            cola.desencolar()
    return _resultado("cola", f"ColaEnlazada, {elementos} elementos", elementos, 5 * elementos,
                      time.perf_counter() - inicio)


def bench_cola_pop0(elementos: int):
    """ALTERNATIVA: ``list`` con ``pop(0)`` (corre todos los elementos en cada salida)."""
    inicio = time.perf_counter()
    for _ in range(5):
        lista = list(range(elementos))
        while lista:
            lista.pop(0)
    return _resultado("cola", f"list pop(0) (descartada), {elementos} elementos", elementos, 5 * elementos,
                      time.perf_counter() - inicio)


# --- §4.9 ordenamiento ---------------------------------------------------------

def _datos_orden(n: int, patron: str) -> list[int]:
    azar = random.Random(42)
    if patron == "aleatorio":
        return [azar.randint(0, 10**9) for _ in range(n)]
    if patron == "casi_ordenado":
        datos = list(range(n))
        for _ in range(max(1, n // 200)):  # pocos intercambios lejanos
            a, b = azar.randrange(n), azar.randrange(n)
            datos[a], datos[b] = datos[b], datos[a]
        return datos
    return list(range(n, 0, -1))


def bench_ordenamiento(algoritmo: str, tamano: int, distribucion: str):
    """``algoritmo``: "insercion", "mezcla" o "selector" (el que usa el programa)."""
    datos = _datos_orden(tamano, distribucion)
    repeticiones = max(10, 20_000 // tamano)
    inicio = time.perf_counter()
    for _ in range(repeticiones):
        if algoritmo == "selector":
            ordenar(datos)
        else:
            ordenar_con_algoritmo(datos, algoritmo)
    return _resultado("ordenamiento", f"{algoritmo} {distribucion} n={tamano}", tamano, repeticiones,
                      time.perf_counter() - inicio)


_NOMBRES = ["".join(random.Random(i).choice("abcdefghijklmnopqrstuvwxyz") for _ in range(12)) for i in range(500)]


class _Objeto:
    __slots__ = ("i",)

    def __init__(self, i: int) -> None:
        self.i = i


def _clave_costosa(objeto: _Objeto) -> str:
    """Como la vista del inventario por nombre: buscar la ficha y pasar a minúsculas."""
    texto = _NOMBRES[objeto.i]
    for _ in range(20):
        texto = texto.lower()
    return texto


def _insercion_clave_por_comparacion(datos: list, clave) -> list:
    """ALTERNATIVA DESCARTADA (la versión original): calcula la clave en cada comparación."""
    salida = list(datos)
    for i in range(1, len(salida)):
        actual = salida[i]
        j = i - 1
        while j >= 0 and clave(salida[j]) > clave(actual):
            salida[j + 1] = salida[j]
            j -= 1
        salida[j + 1] = actual
    return salida


def bench_orden_clave_costosa(tamano: int, por_comparacion: bool):
    datos = [_Objeto(i) for i in range(tamano)]
    random.Random(7).shuffle(datos)
    repeticiones = max(3, 2000 // tamano)
    inicio = time.perf_counter()
    for _ in range(repeticiones):
        if por_comparacion:
            _insercion_clave_por_comparacion(datos, _clave_costosa)
        else:
            ordenar(datos, clave=_clave_costosa)
    nombre = "clave en cada comparación (descartada)" if por_comparacion else "clave una vez por elemento"
    return _resultado("ordenamiento", f"{nombre} n={tamano}", tamano, repeticiones, time.perf_counter() - inicio)


# --- §4.4 caché -------------------------------------------------------------------

def bench_cache_busqueda(tamano: int, acierto: bool):
    cache: CacheAcotada[str, str] = CacheAcotada(max(1, tamano // 2))
    claves = [f"k{i}" for i in range(tamano)]
    for clave in claves:
        cache.insertar(clave, clave)
    buscadas = claves[tamano // 2:] if acierto else claves[: tamano // 2]  # las primeras ya se desalojaron
    inicio = time.perf_counter()
    for _ in range(5):
        for clave in buscadas:
            cache.obtener(clave)
    return _resultado("cache", f"CacheAcotada {'acierto' if acierto else 'fallo'}, {tamano} claves", tamano,
                      5 * len(buscadas), time.perf_counter() - inicio)


class _PoliticaFIFO:
    """ALTERNATIVA: sale la ficha que entró primero, aunque se use mucho."""

    def __init__(self, capacidad: int) -> None:
        self.capacidad = capacidad
        self.presentes: ConjuntoOrdenado[str] = ConjuntoOrdenado()
        self.orden: ColaEnlazada[str] = ColaEnlazada()

    def acceder(self, clave: str) -> bool:
        if self.presentes.contiene(clave):
            return True
        self.presentes.agregar(clave)
        self.orden.encolar(clave)
        if len(self.presentes) > self.capacidad:
            self.presentes.eliminar(self.orden.desencolar())
        return False


class _PoliticaLFU:
    """ALTERNATIVA: sale la ficha menos usada (empate: la más antigua)."""

    def __init__(self, capacidad: int) -> None:
        self.capacidad = capacidad
        self.usos: TablaOrdenada[str, int] = TablaOrdenada()
        self.llegada: list[str] = []

    def acceder(self, clave: str) -> bool:
        usos = self.usos.obtener(clave)
        if usos is not None:
            self.usos.insertar(clave, usos + 1)
            return True
        if len(self.llegada) >= self.capacidad:
            victima = 0
            for i in range(1, len(self.llegada)):  # O(capacidad) al desalojar
                if self.usos.obtener(self.llegada[i]) < self.usos.obtener(self.llegada[victima]):
                    victima = i
            self.usos.eliminar(self.llegada.pop(victima))
        self.usos.insertar(clave, 1)
        self.llegada.append(clave)
        return False


class _PoliticaLRU:
    """La que usa el programa: ``CacheAcotada`` de verdad."""

    def __init__(self, capacidad: int) -> None:
        self.cache: CacheAcotada[str, bool] = CacheAcotada(capacidad)

    def acceder(self, clave: str) -> bool:
        if self.cache.obtener(clave) is not None:
            return True
        self.cache.insertar(clave, True)
        return False


def _traza_sintetica(semilla: int = 3, tipos: int = 120, accesos: int = 6000) -> list[str]:
    """Catálogo grande (como podría ser la cripta de la revisión): el jugador
    recorre salas vecinas y cada sala usa pocos tipos, algunos muy comunes."""
    azar = random.Random(semilla)
    salas = []
    for _ in range(200):
        cantidad = azar.randint(2, 6)
        # tipos "populares" (ratas, pociones...) aparecen en muchas salas
        salas.append([f"t{min(tipos - 1, int(azar.paretovariate(1.2)) * 3 + azar.randrange(3))}" for _ in range(cantidad)])
    traza: list[str] = []
    sala = 0
    while len(traza) < accesos:
        traza.extend(salas[sala])
        sala = max(0, min(len(salas) - 1, sala + azar.choice((-1, 1, 1, 2, -2))))
    return traza


def bench_politica_desalojo(politica: str, capacidad: int, origen: str):
    """Tasa de aciertos LRU vs FIFO vs LFU con una secuencia de accesos del juego.

    "real": las fichas que pidió el modelo jugando las 4 criptas (11 tipos).
    "sintetica": un catálogo de 120 tipos con salas vecinas que comparten tipos.
    La simulación no fija fichas: compara solo la política.
    """
    if origen == "real":
        from cripta.bench.frecuencias import traza_fichas_reales

        traza = traza_fichas_reales()
    else:
        traza = _traza_sintetica()
    if politica == "LRU":
        cache = _PoliticaLRU(capacidad)
    elif politica == "FIFO":
        cache = _PoliticaFIFO(capacidad)
    else:
        cache = _PoliticaLFU(capacidad)
    aciertos = 0
    inicio = time.perf_counter()
    for clave in traza:
        if cache.acceder(clave):
            aciertos += 1
    segundos = time.perf_counter() - inicio
    distintas = ConjuntoOrdenado()
    for clave in traza:
        distintas.agregar(clave)
    if origen == "real":
        from cripta.bench.frecuencias import criptas_reales

        nombre = f"{len(criptas_reales())} criptas reales"
    else:
        nombre = "catálogo grande"
    return _resultado("cache", f"{politica} {nombre} cap={capacidad} aciertos={100 * aciertos / len(traza):.1f}% "
                      f"({len(distintas)} tipos)", capacidad, len(traza), segundos)


def bench_recuperacion(desde: str):
    """Costo de recuperar una ficha liberada: lectura de disco vs memoria (vs ~400 ms de red)."""
    from cripta.adaptadores.almacen_disco import AlmacenCatalogo
    from cripta.adaptadores.fuente_offline import FuenteOffline
    from cripta.bench.frecuencias import DATOS_EJEMPLO, traza_fichas_reales

    # Las fichas que pidió el juego al jugar las criptas de datos_ejemplo/ (sin repetir).
    distintas: ConjuntoOrdenado[str] = ConjuntoOrdenado()
    for tipo_id in traza_fichas_reales():
        distintas.agregar(tipo_id)
    fichas = FuenteOffline(DATOS_EJEMPLO).catalogo(list(distintas))
    directorio = tempfile.mkdtemp(prefix="cripta_bench_disco_")
    try:
        almacen = AlmacenCatalogo(directorio)
        memoria: CacheAcotada[str, object] = CacheAcotada(25)
        for ficha in fichas:
            almacen.escribir(ficha)
            memoria.insertar(ficha.id, ficha)
        ids = [ficha.id for ficha in fichas]
        repeticiones = 200
        inicio = time.perf_counter()
        for _ in range(repeticiones):
            for tipo_id in ids:
                if desde == "disco":
                    almacen.leer(tipo_id)
                else:
                    memoria.obtener(tipo_id)
        segundos = time.perf_counter() - inicio
    finally:
        shutil.rmtree(directorio, ignore_errors=True)
    return _resultado("cache", f"recuperar ficha desde {desde}", len(ids), repeticiones * len(ids), segundos)


# --- §4.2 precarga --------------------------------------------------------------------

def bench_seleccion_lote(cantidad_salas: int):
    """Costo del BFS que elige las próximas 10 salas a pedir."""
    from cripta.bench.bench_modelo import _cripta_cuadricula
    from cripta.controlador.precarga import PlanificadorPrecarga
    from cripta.modelo.mapa import Mapa

    datos, salas, _, _ = _cripta_cuadricula(cantidad_salas, 0, semilla=3)
    mapa = Mapa.construir(datos, salas)
    planificador = PlanificadorPrecarga(None, "bench", None, None, mapa.vecinos, lambda contenido: None)
    try:
        todas = list(mapa)
        azar = random.Random(5)
        # la mitad del mapa ya pedida, como a mitad de una partida
        for sala in todas:
            if azar.random() < 0.5:
                planificador._solicitadas.agregar(sala.id)
        origenes = [todas[azar.randrange(len(todas))].id for _ in range(200)]
        inicio = time.perf_counter()
        for origen in origenes:
            planificador._seleccionar_lote(origen)
        segundos = time.perf_counter() - inicio
    finally:
        planificador.cerrar()
    return _resultado("precarga", f"elegir lote (BFS), {len(todas)} salas", len(todas), len(origenes), segundos)


def bench_solicitudes_precarga():
    """Solicitudes de contenido: por lotes de 10 (precarga) vs una por cada sala visitada."""
    from cripta.bench.frecuencias import medir

    lotes = 0
    por_sala = 0
    ya_pedidas = 0
    movimientos = 0
    criptas = 0
    for medicion in medir():
        if medicion.datos_red is None:
            continue
        criptas += 1
        lotes += medicion.contador.valor("red: contenido")
        por_sala += medicion.salas_visitadas
        ya_pedidas += medicion.contador.valor("precarga: sala ya pedida al moverse")
        movimientos += medicion.contador.valor("precarga: asegurar (antes de moverse)")
    return _resultado("precarga", f"{criptas} criptas: {lotes} solicitudes por lotes vs {por_sala} una por sala; "
                      f"{ya_pedidas}/{movimientos} salas ya pedidas al moverse", por_sala, 1, 0.0)


# --- §4.10 guardado ------------------------------------------------------------------

_estados: TablaOrdenada[str, object] = TablaOrdenada()


def _etiqueta(origen: str) -> str:
    if origen == "real":
        from cripta.bench.frecuencias import cripta_mas_grande

        return f"partida real en {cripta_mas_grande()}"
    return origen


def _estado(origen: str):
    """Estado guardable de una partida real (bot en la cripta más grande) o de la sintética grande."""
    estado = _estados.obtener(origen)
    if estado is not None:
        return estado
    if origen == "real":
        from cripta.adaptadores.fuente_offline import FuenteOffline
        from cripta.bench import bot
        from cripta.bench.frecuencias import DATOS_EJEMPLO, cripta_mas_grande
        from cripta.controlador.controlador import Controlador, OpcionesEjecucion

        directorio = tempfile.mkdtemp(prefix="cripta_bench_guardado_")
        try:
            controlador = Controlador(FuenteOffline(DATOS_EJEMPLO),
                                      OpcionesEjecucion(directorio_datos=directorio, cache_size=25), None)
            controlador.preparar_cripta(cripta_mas_grande())
            controlador._datos.jugador.vida_max = 100_000
            controlador.iniciar_partida("Bot", 1, registrar_replay=False)
            bot.jugar(controlador, 60, semilla=1)
            controlador.cerrar_recursos()
            estado = controlador.juego.exportar_estado("bench")
        finally:
            shutil.rmtree(directorio, ignore_errors=True)
    else:
        from cripta.bench.bench_modelo import _juego_cuadricula
        from cripta.modelo.acciones import Accion, TipoAccion

        juego = _juego_cuadricula(900, 500, semilla=5)
        for _ in range(10):
            juego.ejecutar_accion(Accion(TipoAccion.ESPERAR))
        estado = juego.exportar_estado("bench")
    _estados.insertar(origen, estado)
    return estado


def bench_guardado(formato: str, origen: str):
    """Guardar + cargar el mismo estado en binario propio o en JSON; anota el tamaño."""
    from cripta.adaptadores.guardado import GuardadoBinario, GuardadoJSON

    estado = _estado(origen)
    guardado = GuardadoBinario() if formato == "binario" else GuardadoJSON()
    directorio = tempfile.mkdtemp(prefix="cripta_bench_sav_")
    ruta = os.path.join(directorio, "partida.sav")
    try:
        repeticiones = 5
        inicio = time.perf_counter()
        for _ in range(repeticiones):
            guardado.guardar(ruta, estado)
        segundos_guardar = time.perf_counter() - inicio
        inicio = time.perf_counter()
        for _ in range(repeticiones):
            guardado.cargar(ruta)
        segundos_cargar = time.perf_counter() - inicio
        tamano = os.path.getsize(ruta)
    finally:
        shutil.rmtree(directorio, ignore_errors=True)
    return _resultado("guardado", f"{formato} {_etiqueta(origen)}: {tamano / 1024:.1f} KB, guardar "
                      f"{segundos_guardar / repeticiones * 1000:.1f} ms, cargar (dato)",
                      len(estado.salas), repeticiones, segundos_cargar)


def bench_cargar_una_sala(origen: str):
    """``cargar_sala`` (índice + búsqueda binaria + un bloque) vs cargar todo el archivo."""
    from cripta.adaptadores.guardado import GuardadoBinario

    estado = _estado(origen)
    guardado = GuardadoBinario()
    directorio = tempfile.mkdtemp(prefix="cripta_bench_sala_")
    ruta = os.path.join(directorio, "partida.sav")
    try:
        guardado.guardar(ruta, estado)
        ids = [sala.id for sala in estado.salas]
        azar = random.Random(9)
        consultas = [ids[azar.randrange(len(ids))] for _ in range(50)]
        inicio = time.perf_counter()
        for sala_id in consultas:
            guardado.cargar_sala(ruta, sala_id)
        segundos = time.perf_counter() - inicio
    finally:
        shutil.rmtree(directorio, ignore_errors=True)
    return _resultado("guardado", f"cargar UNA sala (binario) {_etiqueta(origen)}", len(estado.salas), len(consultas),
                      segundos)
