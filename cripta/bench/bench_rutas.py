"""Mediciones de la Persona A en la Parte II (specs 001, 002 y 003, §6.3).  [Persona A]

Subsistemas (``--bench <subsistema>``):

- ``cazador``       (§5.1) búsqueda del cazador: un cazador vs. muchos, rango
                    pequeño vs. grande, cálculo compartido vs. individual,
                    montículo vs. mínimo lineal y costo de un rango pequeño al
                    crecer la cripta.
- ``invalidacion``  (§5.2) reutilizar vs. recalcular siempre con puertas estables
                    e inestables; cálculos hechos, reutilizados y salas
                    examinadas.
- ``ciclo_p2``      (§6.1) ciclo entre decisiones en la cripta de referencia con
                    todos sus enemigos activos (límite 20 ms) y por estrategia.
- ``mapa_conocido`` (§5.3) consultas de estado de sala y puerta (arreglo vs.
                    lista vs. ``TablaOrdenada``), exploración por sala revelada
                    y retroceso de una exploración con antorcha.
- ``ir_a``          (§5.3, §6.1) cálculo de un paso de «ir a» con el mapa
                    completo (límite 5 ms), montículo vs. mínimo lineal.
- ``agenda_p2``     (§5.6, parte A) la agenda con la carga nueva: intervalos de
                    costos variables y decenas de cazadores.

Todo es determinista por semilla y no instancia la vista. Las criptas
sintéticas son cuadrículas con costos aleatorios; la "cripta de referencia" es
la más grande del paquete offline ``datos_ejemplo_p2/`` según su
``criptas.json`` (si no hay paquete, esos casos se saltan con un aviso). Ningún
id de cripta está escrito en el código (constitución IV, spec 001 FR-018).

Los límites de §6.1 se pueden cambiar con variables de entorno
(``CRIPTA_LIMITE_CICLO_MS``, ``CRIPTA_LIMITE_IR_A_MS``); no están escritos dentro
de las mediciones.
"""

from __future__ import annotations

import gc
import math
import os
import random
import time

from cripta.bench.bench_modelo import _AgendaLineal
from cripta.bench.runner import RegistroBenchmarks, ResultadoMedicion, estadisticas, muestras, revisar_limite
from cripta.bench.sinteticos import FichasEnMemoria
from cripta.estructuras.tabla_ordenada import TablaOrdenada
from cripta.modelo.acciones import Accion, TipoAccion
from cripta.modelo.actores import Comportamiento
from cripta.modelo.conocimiento import ConocimientoMapa
from cripta.modelo.datos import (
    ColocacionEnemigo,
    ContenidoSala,
    DatosCripta,
    DatosSala,
    DatosSalida,
    EstadisticasIniciales,
    Ficha,
)
from cripta.modelo.eventos import Agenda, TipoEvento
from cripta.modelo.juego import Juego
from cripta.modelo.mapa import Mapa
from cripta.modelo.rutas import SIN_LIMITE, BuscadorRutas, EstrategiaCazador, salida_abierta

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAQUETE_REFERENCIA = os.environ.get("CRIPTA_BENCH_PAQUETE_P2", os.path.join(RAIZ, "datos_ejemplo_p2"))
LIMITE_CICLO_MS = float(os.environ.get("CRIPTA_LIMITE_CICLO_MS", "20"))
LIMITE_IR_A_MS = float(os.environ.get("CRIPTA_LIMITE_IR_A_MS", "5"))
COSTOS = (20, 50, 80, 100, 120, 150, 200, 300)  # costos de las criptas sintéticas (rango típico del servicio)


def registrar(registro: RegistroBenchmarks) -> None:
    # §5.1 un cazador vs. muchos, rango pequeño vs. grande, compartido vs. individual
    for cantidad in (1, 10, 50):
        for rango, etiqueta in ((300, "pequeño"), (10**6, "grande")):
            for estrategia in (EstrategiaCazador.COMPARTIDA, EstrategiaCazador.INDIVIDUAL):
                caso = f"{cantidad} cazadores rango {etiqueta} {estrategia.value}"
                registro.agregar(
                    "cazador", caso,
                    lambda c=cantidad, r=rango, e=estrategia, t=etiqueta, k=caso: bench_decisiones(50, c, r, e, t, k),
                )
    # SC-004: rango pequeño, cripta cada vez más grande
    for lado in (20, 50, 100):
        for estrategia in (EstrategiaCazador.INDIVIDUAL, EstrategiaCazador.COMPARTIDA):
            caso = f"rango 300 en {lado * lado} salas {estrategia.value}"
            registro.agregar(
                "cazador", caso,
                lambda l=lado, e=estrategia, k=caso: bench_decisiones(l, 1, 300, e, "pequeño", k, rondas=200),
            )
    # Estructura auxiliar: montículo vs. mínimo lineal
    for lado in (20, 50):
        registro.agregar("cazador", f"búsqueda completa montículo {lado * lado}", lambda l=lado: bench_busqueda(l, False))
        registro.agregar("cazador", f"búsqueda completa mínimo lineal {lado * lado}", lambda l=lado: bench_busqueda(l, True))
    registro.agregar("cazador", "búsqueda completa montículo 10000", lambda: bench_busqueda(100, False))

    # §5.2 invalidación: puertas estables vs. inestables
    for cambios, lejos, etiqueta in ((0, False, "estables"), (5, False, "inestables (5/decisión)"),
                                     (20, False, "inestables (20/decisión)"), (20, True, "inestables lejos (20/decisión)")):
        for estrategia in EstrategiaCazador:
            caso = f"puertas {etiqueta} {estrategia.value}"
            registro.agregar(
                "invalidacion", caso,
                lambda c=cambios, e=estrategia, k=caso, l=lejos: bench_invalidacion(c, e, k, l),
            )
    for estrategia in EstrategiaCazador:
        registro.agregar("invalidacion", f"referencia con bot {estrategia.value}",
                         lambda e=estrategia: bench_referencia_bot(e))

    # §6.1 ciclo en la cripta de referencia
    for estrategia in (EstrategiaCazador.COMPARTIDA, EstrategiaCazador.RECALCULAR_SIEMPRE, EstrategiaCazador.INDIVIDUAL):
        registro.agregar("ciclo_p2", f"referencia todos activos {estrategia.value}",
                         lambda e=estrategia: bench_ciclo_referencia(e))

    # §5.3 mapa conocido
    for conocidas in (100, 1000, 10_000):
        for estructura in ("arreglo", "lista", "tabla ordenada"):
            registro.agregar("mapa_conocido", f"consulta {estructura} {conocidas} salas",
                             lambda c=conocidas, e=estructura: bench_consulta_conocimiento(c, e))
    for lado in (20, 100):
        registro.agregar("mapa_conocido", f"explorar 5 salas con {lado * lado} conocidas",
                         lambda l=lado: bench_explorar(l))
    registro.agregar("mapa_conocido", "registrar y revertir antorcha (5 salas)", bench_revertir_antorcha)

    # §5.3 / §6.1 «ir a»
    registro.agregar("ir_a", "paso con mapa completo referencia", bench_ir_a_referencia)
    for lado in (50, 100):
        registro.agregar("ir_a", f"paso con mapa completo {lado * lado} salas", lambda l=lado: bench_ir_a(l, False))
    registro.agregar("ir_a", "paso mínimo lineal 2500 salas", lambda: bench_ir_a(50, True))

    # §5.6 parte A: agenda con la carga nueva
    for n in (100, 500, 2000):
        registro.agregar("agenda_p2", f"montículo carga P2 n={n}", lambda n=n: bench_agenda_p2(n, False))
        registro.agregar("agenda_p2", f"lista lineal carga P2 n={n}", lambda n=n: bench_agenda_p2(n, True))
    registro.agregar("agenda_p2", "eventos pendientes en la referencia", bench_tamano_agenda_referencia)


def revisar_limites(resultados: list[ResultadoMedicion]) -> None:
    """PASA/FALLA de §6.1 para el ciclo (20 ms) y el paso de «ir a» (5 ms)."""
    for resultado in resultados:
        if resultado.subsistema == "ciclo_p2" and resultado.caso.endswith(EstrategiaCazador.COMPARTIDA.value):
            peor = getattr(resultado, "_peor", None)
            if peor is not None:
                revisar_limite("ciclo entre decisiones, cripta de referencia (peor caso)", peor, LIMITE_CICLO_MS)
        if resultado.subsistema == "ir_a" and resultado.caso == "paso con mapa completo referencia":
            peor = getattr(resultado, "_peor", None)
            if peor is not None:
                revisar_limite("paso de «ir a», mapa completo de la referencia (peor caso)", peor, LIMITE_IR_A_MS)


class _Resultado(ResultadoMedicion):
    """ResultadoMedicion con el peor caso guardado (para revisar los límites)."""

    __slots__ = ("_peor",)


def _resultado(subsistema, caso, n, repeticiones, segundos, detalle, peor=None) -> ResultadoMedicion:
    resultado = _Resultado(subsistema, caso, n, repeticiones, segundos, detalle)
    resultado._peor = peor
    return resultado


# =============================================================================
# Criptas para medir
# =============================================================================

def _fichas() -> list[Ficha]:
    return [
        Ficha("ent_caz_pequeno", "enemigo", "Cazador", vida_max=40, ataque=1, defensa=0, velocidad=110,
              comportamiento="cazador", rango=300),
        Ficha("ent_caz_grande", "enemigo", "Cazador", vida_max=40, ataque=1, defensa=0, velocidad=100,
              comportamiento="cazador", rango=10**6),
        Ficha("ent_caz_medio", "enemigo", "Cazador", vida_max=40, ataque=1, defensa=0, velocidad=100,
              comportamiento="cazador", rango=2400),
        Ficha("ent_caz_700", "enemigo", "Cazador", vida_max=40, ataque=1, defensa=0, velocidad=100,
              comportamiento="cazador", rango=700),
    ]


def _cuadricula(lado: int, semilla: int, prob_puerta: float = 0.0) -> tuple[DatosCripta, list[DatosSala]]:
    """Cuadrícula lado x lado con costos aleatorios de COSTOS (puertas abiertas opcionales)."""
    azar = random.Random(semilla)
    total = lado * lado
    salidas: list[list[DatosSalida]] = [[] for _ in range(total)]
    for i in range(total):
        fila, columna = divmod(i, lado)
        if fila < lado - 1:
            costo = azar.choice(COSTOS)
            puerta = azar.random() < prob_puerta
            salidas[i].append(DatosSalida("S", i + lado + 1, False, None, 10**9 if puerta else None, costo))
            salidas[i + lado].append(DatosSalida("N", i + 1))
        if columna < lado - 1:
            costo = azar.choice(COSTOS)
            puerta = azar.random() < prob_puerta
            salidas[i].append(DatosSalida("E", i + 2, False, None, 10**9 if puerta else None, costo))
            salidas[i + 1].append(DatosSalida("O", i + 1))
    esqueleto = []
    for i in range(total):
        orden = [s for d in ("N", "S", "E", "O") for s in salidas[i] if s.direccion == d]
        esqueleto.append(DatosSala(i + 1, f"Sala {i + 1}", orden))
    datos = DatosCripta("bench-p2", "v1", total, 1, total, 1, total, "llave_bench", 999, 10,
                        EstadisticasIniciales(10**9, 1, 2, 100))
    return datos, esqueleto


def _juego(datos, esqueleto, enemigos: list[tuple[int, str]], estrategia, semilla=5,
           centro: int | None = None) -> Juego:
    fichas = FichasEnMemoria(_fichas())
    mapa = Mapa.construir(datos, esqueleto)
    por_sala: list[list[ColocacionEnemigo]] = [[] for _ in range(len(esqueleto))]
    for k, (sala, tipo) in enumerate(enemigos):
        por_sala[sala - 1].append(ColocacionEnemigo(f"e-{k:05d}", tipo))
    for i in range(len(esqueleto)):
        mapa.incorporar_contenido(ContenidoSala(i + 1, por_sala[i], [], []), fichas)
    if centro is not None:
        datos.sala_inicial = centro
        mapa.sala_inicial = mapa.sala(centro)
    juego = Juego(datos, mapa, fichas, semilla, "bench", estrategia)
    juego.iniciar()
    for sala in mapa:
        juego._activar_enemigos(sala)
    return juego


def id_referencia() -> str | None:
    """Id de la cripta más grande del paquete (la de referencia), leído de ``criptas.json``."""
    if not os.path.isfile(os.path.join(PAQUETE_REFERENCIA, "criptas.json")):
        return None
    from cripta.adaptadores.fuente_offline import FuenteOffline

    mejor = None
    for resumen in FuenteOffline(PAQUETE_REFERENCIA).listar_criptas():
        if mejor is None or resumen.salas > mejor.salas:
            mejor = resumen
    return mejor.id if mejor is not None else None


def _referencia():
    """(datos, esqueleto, contenido, fichas) de la cripta de referencia, o None si no hay paquete."""
    cripta_id = id_referencia()
    if cripta_id is None:
        return None
    from cripta.adaptadores.fuente_offline import FuenteOffline

    fuente = FuenteOffline(PAQUETE_REFERENCIA)
    datos = fuente.datos_cripta(cripta_id)
    esqueleto: list[DatosSala] = []
    for pagina in range(1, datos.paginas + 1):
        esqueleto.extend(fuente.pagina_esqueleto(cripta_id, pagina).salas)
    contenido = fuente.contenido(cripta_id, [s.id for s in esqueleto])
    tipos: list[str] = []
    for c in contenido:
        tipos.extend(c.tipos_referenciados())
    fichas = fuente.catalogo(_unicos(tipos))
    sueltas = [t for f in fichas for t in f.suelta]
    fichas.extend(fuente.catalogo(_unicos([t for t in sueltas if t not in tipos])))
    return datos, esqueleto, contenido, fichas


def _unicos(ids: list[str]) -> list[str]:
    tabla: TablaOrdenada[str, bool] = TablaOrdenada()
    for i in ids:
        tabla.insertar(i, True)
    return [clave for clave, _ in tabla.pares()]


def _juego_referencia(estrategia: EstrategiaCazador, semilla: int = 5) -> Juego | None:
    paquete = _referencia()
    if paquete is None:
        return None
    datos, esqueleto, contenido, fichas = paquete
    datos.jugador = EstadisticasIniciales(10**9, datos.jugador.ataque, 10**6, datos.jugador.velocidad)
    proveedor = FichasEnMemoria(fichas)
    mapa = Mapa.construir(datos, esqueleto)
    for c in contenido:
        mapa.incorporar_contenido(c, proveedor)
    juego = Juego(datos, mapa, proveedor, semilla, "bench", estrategia)
    juego.iniciar()
    for sala in mapa:
        juego._activar_enemigos(sala)  # TODOS los enemigos activos (peor caso de §6.1)
    return juego


def _caminata(juego: Juego, azar: random.Random) -> Accion:
    """Paso al azar por una salida abierta (o esperar). El jugador nunca ataca: los cazadores siguen buscando."""
    abiertas = [s for s in juego.jugador.sala.salidas_transitables()]
    if not abiertas:
        return Accion(TipoAccion.ESPERAR)
    return Accion(TipoAccion.MOVER, direccion=abiertas[azar.randrange(len(abiertas))].direccion)


# =============================================================================
# §5.1 búsqueda del cazador
# =============================================================================

def bench_decisiones(lado: int, cantidad: int, rango: int, estrategia: EstrategiaCazador, etiqueta: str,
                     caso: str, rondas: int = 40) -> ResultadoMedicion:
    """Rondas en las que TODOS los cazadores deciden hacia una sala del jugador distinta cada vez.

    Aísla el costo de decidir (sin el resto del ciclo). El jugador cambia de
    sala en cada ronda, así que la estrategia compartida hace UN cálculo por
    ronda y la individual, uno por cazador.
    """
    datos, esqueleto = _cuadricula(lado, semilla=11)
    azar = random.Random(3)
    tipo = "ent_caz_pequeno" if etiqueta == "pequeño" else "ent_caz_grande"
    enemigos = [(azar.randint(2, lado * lado), tipo) for _ in range(cantidad)]
    juego = _juego(datos, esqueleto, enemigos, estrategia)
    cazadores = [e for e in juego.enemigos.valores() if e.comportamiento is Comportamiento.CAZADOR]
    salas = [s for s in juego.mapa]
    rutas = juego.rutas
    destinos = []
    for _ in range(rondas):
        destino = salas[azar.randrange(len(salas))]
        # Para el rango pequeño, el jugador queda cerca de algún cazador (si no, todos esperan sin buscar nada).
        if etiqueta == "pequeño" and cazadores:
            base = cazadores[azar.randrange(len(cazadores))].sala
            vecinas = [s.destino for s in base.salidas if s is not None]
            destino = vecinas[azar.randrange(len(vecinas))] if vecinas else base
        destinos.append(destino)
    gc.collect()
    tiempos = []
    examinadas_antes = rutas.buscador.salas_examinadas
    for destino in destinos:
        inicio = time.perf_counter()
        for cazador in cazadores:
            rutas.decidir(cazador, destino)
        tiempos.append(time.perf_counter() - inicio)
    total = sum(tiempos)
    decisiones = max(1, rondas * len(cazadores))
    examinadas = (rutas.buscador.salas_examinadas - examinadas_antes) / decisiones
    est = estadisticas(tiempos)
    detalle = (f"ronda: {est.en_ms()} | cálculos {rutas.calculos}, reutilizados {rutas.reutilizados}, "
               f"salas examinadas/decisión {examinadas:.1f}")
    return _resultado("cazador", caso, lado * lado, decisiones, total, detalle)


def _dijkstra_lineal(mapa: Mapa, objetivo, alcance: int) -> list:
    """ALTERNATIVA DESCARTADA: Dijkstra inverso escogiendo el mínimo con un recorrido lineal (O(V²))."""
    salas = [s for s in mapa]
    n = len(salas)
    dist = [None] * n
    hecho = [False] * n
    dist[objetivo.indice] = 0
    while True:
        mejor = -1
        for i in range(n):
            if not hecho[i] and dist[i] is not None and (mejor < 0 or dist[i] < dist[mejor]):
                mejor = i
        if mejor < 0 or dist[mejor] > alcance:
            break
        hecho[mejor] = True
        for entrada in salas[mejor].entradas:
            if not salida_abierta(entrada):
                continue
            j = entrada.origen.indice
            nueva = dist[mejor] + entrada.costo
            if not hecho[j] and (dist[j] is None or nueva < dist[j]):
                dist[j] = nueva
    return dist


def bench_busqueda(lado: int, lineal: bool) -> ResultadoMedicion:
    """Una búsqueda completa (sin límite) desde una sala: montículo propio vs. mínimo lineal."""
    datos, esqueleto = _cuadricula(lado, semilla=11)
    mapa = Mapa.construir(datos, esqueleto)
    salas = [s for s in mapa]
    azar = random.Random(7)
    repeticiones = 1 if lineal and lado >= 50 else (3 if lineal else 10)
    objetivos = [salas[azar.randrange(len(salas))] for _ in range(repeticiones)]
    buscador = BuscadorRutas(mapa)
    gc.collect()
    inicio = time.perf_counter()
    for objetivo in objetivos:
        if lineal:
            _dijkstra_lineal(mapa, objetivo, SIN_LIMITE)
        else:
            buscador.calcular(objetivo, SIN_LIMITE, salida_abierta)
    segundos = time.perf_counter() - inicio
    nombre = "mínimo lineal (descartado)" if lineal else "montículo"
    return _resultado("cazador", f"búsqueda completa {nombre} {lado * lado}", lado * lado, repeticiones, segundos,
                      f"{segundos / repeticiones * 1000:.2f} ms por búsqueda")


# =============================================================================
# §5.2 invalidación
# =============================================================================

def bench_invalidacion(cambios: int, estrategia: EstrategiaCazador, caso: str, lejos: bool = False,
                       decisiones: int = 120) -> ResultadoMedicion:
    """Cuadrícula de 2 500 salas con puerta en el 60 % de los pasajes y 30 cazadores de rango 700.

    El jugador espera en el centro (no cambia de sala), así que lo único que
    puede invalidar el cálculo compartido son las puertas. Los cazadores están
    a 3..15 salas: los cercanos se acercan y los lejanos (fuera de rango)
    deciden "esperar" en cada turno, así que siempre hay decisiones que tomar.
    Entre decisiones se abren o cierran ``cambios`` puertas al azar de toda la
    cripta (o, con ``lejos``, solo puertas con sus dos salas a 15 o más salas
    del jugador: fuera de la región del cálculo, AC-002-02).
    """
    lado = 50
    datos, esqueleto = _cuadricula(lado, semilla=21, prob_puerta=0.6)
    centro = (lado // 2) * lado + lado // 2 + 1
    azar = random.Random(4)

    def distancia(sala_id: int) -> int:
        f, c = divmod(sala_id - 1, lado)
        return abs(f - lado // 2) + abs(c - lado // 2)

    enemigos = []
    while len(enemigos) < 30:
        sala = azar.randint(1, lado * lado)
        if 3 <= distancia(sala) <= 15:
            enemigos.append((sala, "ent_caz_700"))
    juego = _juego(datos, esqueleto, enemigos, estrategia, centro=centro)
    puertas = juego.mapa.lista_puertas
    if lejos:
        puertas = [p for p in puertas if distancia(p.salas[0].id) >= 15 and distancia(p.salas[1].id) >= 15]
    esperar = Accion(TipoAccion.ESPERAR)
    gc.collect()
    tiempos = []
    for _ in range(decisiones):
        for _ in range(cambios):
            puerta = puertas[azar.randrange(len(puertas))]
            puerta.cerrada = not puerta.cerrada
        inicio = time.perf_counter()
        juego.ejecutar_accion(esperar)
        tiempos.append(time.perf_counter() - inicio)
    rutas = juego.rutas
    est = estadisticas(tiempos)
    detalle = (f"{est.en_ms()} | cálculos {rutas.calculos}, reutilizados {rutas.reutilizados}, "
               f"invalidaciones {rutas.invalidaciones}, salas examinadas {rutas.buscador.salas_examinadas}")
    return _resultado("invalidacion", caso, lado * lado, decisiones, sum(tiempos), detalle)


def bench_referencia_bot(estrategia: EstrategiaCazador, decisiones: int = 250) -> ResultadoMedicion:
    """La cripta de referencia jugada con el bot (puertas reales con cierre automático)."""
    from cripta.bench.bot import elegir_accion

    juego = _juego_referencia(estrategia)
    if juego is None:
        return _resultado("invalidacion", f"referencia con bot {estrategia.value}", 0, 0, 0.0,
                          "SIN DATOS: falta datos_ejemplo_p2/")
    for enemigo in juego.enemigos.valores():  # el bot ataca; que sobrevivan para seguir midiendo
        enemigo.vida_max = enemigo.vida = 10**6
    azar = random.Random(5)
    visitadas: list[int] = []
    gc.collect()
    tiempos = []
    for _ in range(decisiones):
        if juego.esta_terminada():
            break
        if juego.jugador.sala.id not in visitadas:
            visitadas.append(juego.jugador.sala.id)
        accion = elegir_accion(juego, azar, visitadas)
        if accion.tipo is TipoAccion.ATACAR:
            accion = _caminata(juego, azar)
        inicio = time.perf_counter()
        juego.ejecutar_accion(accion)
        tiempos.append(time.perf_counter() - inicio)
    rutas = juego.rutas
    est = estadisticas(tiempos)
    detalle = (f"{est.en_ms()} | cálculos {rutas.calculos}, reutilizados {rutas.reutilizados}, "
               f"salas examinadas {rutas.buscador.salas_examinadas}")
    return _resultado("invalidacion", f"referencia con bot {estrategia.value}", len(juego.mapa), len(tiempos),
                      sum(tiempos), detalle)


# =============================================================================
# §6.1 ciclo en la cripta de referencia
# =============================================================================

def bench_ciclo_referencia(estrategia: EstrategiaCazador, decisiones: int = 300) -> ResultadoMedicion:
    """Ciclo entre decisiones con TODOS los enemigos de la referencia activos (36 cazadores)."""
    juego = _juego_referencia(estrategia)
    if juego is None:
        return _resultado("ciclo_p2", f"referencia todos activos {estrategia.value}", 0, 0, 0.0,
                          "SIN DATOS: falta datos_ejemplo_p2/")
    cazadores = sum(1 for e in juego.enemigos.valores()
                    if e.comportamiento is Comportamiento.CAZADOR and e.activo)
    azar = random.Random(8)
    gc.collect()
    gc.freeze()  # como el controlador al iniciar la partida (_congelar_objetos_cargados)
    tiempos = []
    try:
        for _ in range(decisiones):
            if juego.esta_terminada():
                break
            accion = _caminata(juego, azar)
            inicio = time.perf_counter()
            juego.ejecutar_accion(accion)
            tiempos.append(time.perf_counter() - inicio)
    finally:
        gc.unfreeze()
    est = estadisticas(tiempos)
    detalle = (f"{est.en_ms()} | {cazadores} cazadores activos, cálculos {juego.rutas.calculos}, "
               f"reutilizados {juego.rutas.reutilizados}")
    return _resultado("ciclo_p2", f"referencia todos activos {estrategia.value}", len(juego.mapa), len(tiempos),
                      sum(tiempos), detalle, peor=est.maximo)


# =============================================================================
# §5.3 mapa conocido
# =============================================================================

def bench_consulta_conocimiento(conocidas: int, estructura: str, consultas: int = 50_000) -> ResultadoMedicion:
    """¿Está explorada esta sala? con el arreglo del juego vs. alternativas."""
    azar = random.Random(2)
    ids = list(range(1, 2 * conocidas + 1))
    exploradas = ids[::2]
    preguntas = [azar.choice(ids) for _ in range(consultas)]
    if estructura == "arreglo":
        arreglo = [0] * (2 * conocidas + 1)
        for i in exploradas:
            arreglo[i] = 2
        inicio = time.perf_counter()
        for i in preguntas:
            _ = arreglo[i] == 2
        segundos = time.perf_counter() - inicio
    elif estructura == "lista":
        lista = list(exploradas)
        consultas = min(consultas, 2_000)
        preguntas = preguntas[:consultas]
        inicio = time.perf_counter()
        for i in preguntas:
            _ = i in lista  # búsqueda lineal
        segundos = time.perf_counter() - inicio
    else:
        tabla: TablaOrdenada[int, bool] = TablaOrdenada()
        for i in exploradas:
            tabla.insertar(i, True)
        inicio = time.perf_counter()
        for i in preguntas:
            _ = tabla.contiene(i)
        segundos = time.perf_counter() - inicio
    nombre = estructura if estructura == "arreglo" else f"{estructura} (descartada)"
    return _resultado("mapa_conocido", f"consulta {nombre} {conocidas} salas", conocidas, consultas, segundos, "")


def bench_explorar(lado: int, repeticiones: int = 2_000) -> ResultadoMedicion:
    """Explorar 5 salas nuevas cuesta lo mismo con 400 que con 10 000 salas conocidas (NFR-003)."""
    datos, esqueleto = _cuadricula(lado, semilla=1)
    mapa = Mapa.construir(datos, esqueleto)
    conocimiento = ConocimientoMapa(mapa)
    salas = [s for s in mapa]
    cambios = []

    def asignar(arreglo, indice, valor):
        cambios.append((arreglo, indice, arreglo[indice]))
        arreglo[indice] = valor

    for sala in salas[: len(salas) - 10]:  # casi todo el mapa ya conocido
        conocimiento.explorar(sala, asignar)
    nuevas = salas[len(salas) - 5:]
    tiempos = 0.0
    for _ in range(repeticiones):
        cambios.clear()
        inicio = time.perf_counter()
        for sala in nuevas:
            conocimiento.explorar(sala, asignar)
        tiempos += time.perf_counter() - inicio
        for arreglo, indice, anterior in reversed(cambios):  # deshacer para repetir
            arreglo[indice] = anterior
    return _resultado("mapa_conocido", f"explorar 5 salas con {lado * lado} conocidas", lado * lado, repeticiones,
                      tiempos, f"{len(cambios)} casillas registradas por exploración")


def bench_revertir_antorcha(repeticiones: int = 300) -> ResultadoMedicion:
    """Entrar con antorcha (explora la sala y sus vecinas) y revertirlo con un pergamino."""
    from cripta.modelo.datos import ContenidoSala as Contenido

    datos, esqueleto = _cuadricula(30, semilla=3)
    fichas = FichasEnMemoria([Ficha("itm_bench_antorcha", "antorcha", "Antorcha", peso=1, valor=1, duracion=10**8),
                              Ficha("itm_bench_pergamino", "pergamino_retroceso", "Pergamino", peso=1, valor=1)])
    datos.inventario_max = 1000
    mapa = Mapa.construir(datos, esqueleto)
    objetos = ["itm_bench_antorcha"] + ["itm_bench_pergamino"] * repeticiones
    for sala in mapa:
        mapa.incorporar_contenido(Contenido(sala.id, [], objetos if sala.id == 1 else [], []), fichas)
    juego = Juego(datos, mapa, fichas, 1, "bench")
    juego.iniciar()
    for objeto in juego.jugador.sala.objetos_suelo.a_lista():
        juego.ejecutar_accion(Accion(TipoAccion.RECOGER, objetivo=objeto.id))
    antorcha = juego.jugador.inventario.buscar_por_tipo("itm_bench_antorcha")
    juego.ejecutar_accion(Accion(TipoAccion.USAR, objetivo=antorcha.id))
    tiempo_registro = 0.0
    tiempo_revertir = 0.0
    cambios = 0
    for _ in range(repeticiones):
        direccion = "E" if juego.jugador.sala.salida("E") is not None else "O"
        inicio = time.perf_counter()
        juego.ejecutar_accion(Accion(TipoAccion.MOVER, direccion=direccion))
        tiempo_registro += time.perf_counter() - inicio
        cambios += juego.historial.cambios_del_ultimo()
        inicio = time.perf_counter()
        juego.usar_pergamino()
        tiempo_revertir += time.perf_counter() - inicio
    return _resultado("mapa_conocido", "registrar y revertir antorcha (5 salas)", 5, repeticiones,
                      tiempo_registro + tiempo_revertir,
                      f"mover con antorcha {tiempo_registro / repeticiones * 1e6:.1f} us, "
                      f"pergamino {tiempo_revertir / repeticiones * 1e6:.1f} us (acción completa), "
                      f"{cambios / repeticiones:.1f} cambios registrados por acción")


# =============================================================================
# «ir a»
# =============================================================================

def _todo_explorado(juego: Juego) -> None:
    for sala in juego.mapa:
        juego.conocimiento.explorar(sala, juego._asignar_casilla)
        for salida in sala.salidas:
            if salida is not None and salida.puerta is not None:
                juego.conocimiento.observar(salida.puerta, juego._asignar_casilla)


def _medir_pasos(juego: Juego, repeticiones: int, lineal: bool = False) -> tuple[float, float, int]:
    salas = [s for s in juego.mapa]
    azar = random.Random(9)
    destinos = [salas[azar.randrange(len(salas))] for _ in range(repeticiones)]
    gc.collect()
    tiempos = []
    for destino in destinos:
        inicio = time.perf_counter()
        if lineal:
            _dijkstra_lineal(juego.mapa, destino, SIN_LIMITE)
        else:
            juego.paso_hacia(destino.id)
        tiempos.append(time.perf_counter() - inicio)
    est = estadisticas(tiempos)
    return sum(tiempos), est.maximo, len(tiempos)


def bench_ir_a_referencia(repeticiones: int = 300) -> ResultadoMedicion:
    juego = _juego_referencia(EstrategiaCazador.COMPARTIDA)
    if juego is None:
        return _resultado("ir_a", "paso con mapa completo referencia", 0, 0, 0.0, "SIN DATOS: falta datos_ejemplo_p2/")
    _todo_explorado(juego)
    total, peor, n = _medir_pasos(juego, repeticiones)
    return _resultado("ir_a", "paso con mapa completo referencia", len(juego.mapa), n, total,
                      f"peor {peor * 1000:.3f} ms", peor=peor)


def bench_ir_a(lado: int, lineal: bool) -> ResultadoMedicion:
    datos, esqueleto = _cuadricula(lado, semilla=13)
    centro = (lado // 2) * lado + lado // 2 + 1
    juego = _juego(datos, esqueleto, [], EstrategiaCazador.COMPARTIDA, centro=centro)
    _todo_explorado(juego)
    repeticiones = 3 if lineal else 100
    total, peor, n = _medir_pasos(juego, repeticiones, lineal)
    nombre = f"paso mínimo lineal (descartado) {lado * lado} salas" if lineal else f"paso con mapa completo {lado * lado} salas"
    return _resultado("ir_a", nombre, lado * lado, n, total, f"peor {peor * 1000:.3f} ms")


# =============================================================================
# §5.6 parte A: agenda con la carga de la Parte II
# =============================================================================

def bench_agenda_p2(eventos_simultaneos: int, lineal: bool, operaciones: int = 20_000) -> ResultadoMedicion:
    """Como ``bench_agenda_*`` de la Parte I, pero con intervalos de la Parte II.

    En la Parte I todo movimiento costaba 100 (intervalos de 50 a 150). Ahora
    el intervalo es ``costo * 100 // velocidad`` con los costos de la cripta de
    referencia (20 a 300) y velocidades de 100 a 130: los tiempos quedan mucho
    más dispersos y hay más reprogramaciones por cambios de velocidad.
    """
    azar = random.Random(1)
    agenda = _AgendaLineal() if lineal else Agenda()
    programados = [agenda.programar(azar.randint(0, 1000), TipoEvento.TURNO_ENEMIGO, None)
                   for _ in range(eventos_simultaneos)]
    velocidades = (100, 110, 120, 130)
    inicio = time.perf_counter()
    for i in range(operaciones):
        evento = agenda.extraer_siguiente()
        intervalo = max(1, azar.choice(COSTOS) * 100 // azar.choice(velocidades))
        programados[i % eventos_simultaneos] = agenda.programar(evento.tiempo + intervalo, evento.tipo, None)
        if i % 10 == 0:
            victima = programados[azar.randrange(eventos_simultaneos)]
            if agenda.cancelar(victima):
                agenda.programar(victima.tiempo + 1, victima.tipo, None)
    segundos = time.perf_counter() - inicio
    nombre = "lista lineal (descartada)" if lineal else "montículo + borrado perezoso"
    return _resultado("agenda_p2", f"{nombre} carga P2 n={eventos_simultaneos}", eventos_simultaneos, operaciones,
                      segundos, "")


def bench_tamano_agenda_referencia(decisiones: int = 200) -> ResultadoMedicion:
    """Cuántos eventos pendientes hay de verdad en la referencia con todo activo."""
    juego = _juego_referencia(EstrategiaCazador.COMPARTIDA)
    if juego is None:
        return _resultado("agenda_p2", "eventos pendientes en la referencia", 0, 0, 0.0,
                          "SIN DATOS: falta datos_ejemplo_p2/")
    azar = random.Random(8)
    maximo = 0
    suma = 0
    inicio = time.perf_counter()
    for _ in range(decisiones):
        juego.ejecutar_accion(_caminata(juego, azar))
        tamano = len(juego.agenda)
        maximo = max(maximo, tamano)
        suma += tamano
    segundos = time.perf_counter() - inicio
    return _resultado("agenda_p2", "eventos pendientes en la referencia", maximo, decisiones, segundos,
                      f"promedio {suma / decisiones:.1f}, máximo {maximo}")


# Para quien importe este módulo sin el runner (pruebas): nada se ejecuta al importar.
_ = (math, muestras)
