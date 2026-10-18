"""Benchmarks del modelo.                                            [Persona A]

Evidencia para las secciones §4.1, §4.5, §4.6, §4.7, §4.8 del Documento y
para el requisito de §5.2 (< 20 ms por ciclo entre decisiones del jugador).
Cada función devuelve un ``ResultadoMedicion`` donde ``repeticiones`` es la
cantidad de operaciones medidas (así ``microsegundos_por_operacion`` da el
costo de UNA operación).

Las criptas de prueba son cuadrículas generadas aquí (``_cripta_cuadricula``),
reproducibles con una semilla, para poder medir con criptas mucho más
grandes que las publicadas (§9). Se usa ``FichasEnMemoria`` (sin disco ni
red) para medir solo el modelo.
"""

from __future__ import annotations

import gc
import math
import random
import time

from cripta.bench.runner import RegistroBenchmarks, ResultadoMedicion
from cripta.bench.sinteticos import FichasEnMemoria
from cripta.constantes import MENSAJES_VISIBLES
from cripta.modelo.acciones import Accion, TipoAccion
from cripta.modelo.comportamiento import IAEnemigos
from cripta.modelo.datos import (
    ColocacionEnemigo,
    ContenidoSala,
    DatosCripta,
    DatosSala,
    DatosSalida,
    EstadisticasIniciales,
    Ficha,
)
from cripta.modelo.eventos import Agenda, Evento, TipoEvento
from cripta.modelo.historial import CambioAtributo, Historial
from cripta.modelo.inventario import Inventario
from cripta.modelo.juego import Juego
from cripta.modelo.mapa import Mapa
from cripta.modelo.mensajes import BitacoraMensajes
from cripta.modelo.objetos import ClaseObjeto, InstanciaObjeto


def registrar(registro: RegistroBenchmarks) -> None:
    """Agrega todos los casos de este archivo al registro."""
    for n in (100, 500, 2000):
        registro.agregar("agenda", f"montículo n={n}", lambda n=n: bench_agenda_monticulo(n, 20_000))
        registro.agregar("agenda", f"lista lineal n={n}", lambda n=n: bench_agenda_lista_lineal(n, 20_000))
    for salas, enemigos in ((100, 50), (400, 200), (900, 500)):
        registro.agregar(
            "ciclo", f"salas={salas} enemigos={enemigos}",
            lambda s=salas, e=enemigos: bench_ciclo_entre_decisiones(s, e),
        )
    # Tamaños grandes a propósito: muestran que la lista doble NO depende de la
    # posición y dónde se cruza con ``list`` (cuyo desplazamiento está en C).
    for tamano in (10, 100, 1000, 10_000, 100_000):
        registro.agregar("inventario", f"lista doble n={tamano}", lambda t=tamano: bench_inventario_lista_doble(t, 20_000))
        registro.agregar("inventario", f"list n={tamano}", lambda t=tamano: bench_inventario_list_python(t, 20_000))
    # Lo que pide §4.5: que el costo NO dependa de la posición del objeto.
    for posicion in ("inicio", "medio", "final"):
        for estructura in ("lista doble", "list"):
            registro.agregar("inventario", f"{estructura} posición {posicion}",
                             lambda p=posicion, e=estructura: bench_inventario_por_posicion(e, p, 10_000, 20_000))
    for cambios in (10, 100, 1000):
        registro.agregar("historial", f"bitácora k={cambios}", lambda c=cambios: bench_historial_registrar_y_revertir(c))
    for salas, enemigos in ((100, 50), (900, 500)):
        registro.agregar(
            "historial", f"copia completa salas={salas}",
            lambda s=salas, e=enemigos: bench_historial_copia_completa(s, e),
        )
    for salas in (100, 2500, 10_000):
        registro.agregar("rastro", f"rastreadores salas={salas}", lambda s=salas: bench_rastreadores(200, s))
    for pasos in (100, 1000, 10_000):
        registro.agregar("rastro", f"recorrido pasos={pasos}", lambda p=pasos: bench_rastro_recorrido(200, p))
    for capacidad in (MENSAJES_VISIBLES, 2000, 20_000):
        registro.agregar("bitacora", f"circular cap={capacidad}", lambda c=capacidad: bench_bitacora_circular(100_000, c))
        registro.agregar("bitacora", f"list pop(0) cap={capacidad}", lambda c=capacidad: bench_bitacora_list_pop0(100_000, c))


# --- §4.1 agenda ---------------------------------------------------------------

def bench_agenda_monticulo(eventos_simultaneos: int, operaciones: int) -> ResultadoMedicion:
    """Programar / extraer / cancelar con la agenda real (cientos de eventos, decenas de miles de extracciones).

    Cada operación: extraer el siguiente y reprogramarlo más adelante; una de
    cada 10 además cancela un evento al azar y programa su reemplazo (muerte,
    antídoto, cambio de velocidad).
    """
    azar = random.Random(1)
    agenda = Agenda()
    programados = [
        agenda.programar(azar.randint(0, 1000), TipoEvento.TURNO_ENEMIGO, None) for _ in range(eventos_simultaneos)
    ]
    inicio = time.perf_counter()
    for i in range(operaciones):
        evento = agenda.extraer_siguiente()
        programados[i % eventos_simultaneos] = agenda.programar(
            evento.tiempo + azar.randint(50, 150), evento.tipo, None
        )
        if i % 10 == 0:
            victima = programados[azar.randrange(eventos_simultaneos)]
            if agenda.cancelar(victima):
                agenda.programar(victima.tiempo + 1, victima.tipo, None)
    segundos = time.perf_counter() - inicio
    return ResultadoMedicion(
        "agenda", f"montículo + borrado perezoso, {eventos_simultaneos} eventos", eventos_simultaneos, operaciones, segundos
    )


class _AgendaLineal:
    """ALTERNATIVA DESCARTADA: eventos en una ``list`` sin ordenar."""

    def __init__(self) -> None:
        self._eventos: list[Evento] = []
        self._secuencia = 0

    def programar(self, tiempo: int, tipo: TipoEvento, objetivo: object) -> Evento:
        evento = Evento(tiempo, self._secuencia, tipo, objetivo)
        self._secuencia += 1
        self._eventos.append(evento)
        return evento

    def extraer_siguiente(self) -> Evento:
        eventos = self._eventos
        minimo = 0
        for i in range(1, len(eventos)):  # examina TODOS los eventos: O(n)
            if eventos[i] < eventos[minimo]:
                minimo = i
        evento = eventos[minimo]
        eventos[minimo] = eventos[-1]
        eventos.pop()
        return evento

    def cancelar(self, evento: Evento) -> bool:
        eventos = self._eventos
        for i in range(len(eventos)):  # buscarlo también es O(n)
            if eventos[i] is evento:
                eventos[i] = eventos[-1]
                eventos.pop()
                return True
        return False


def bench_agenda_lista_lineal(eventos_simultaneos: int, operaciones: int) -> ResultadoMedicion:
    """ALTERNATIVA DESCARTADA: buscar el mínimo recorriendo una lista."""
    azar = random.Random(1)
    agenda = _AgendaLineal()
    programados = [
        agenda.programar(azar.randint(0, 1000), TipoEvento.TURNO_ENEMIGO, None) for _ in range(eventos_simultaneos)
    ]
    inicio = time.perf_counter()
    for i in range(operaciones):
        evento = agenda.extraer_siguiente()
        programados[i % eventos_simultaneos] = agenda.programar(
            evento.tiempo + azar.randint(50, 150), evento.tipo, None
        )
        if i % 10 == 0:
            victima = programados[azar.randrange(eventos_simultaneos)]
            if agenda.cancelar(victima):
                agenda.programar(victima.tiempo + 1, victima.tipo, None)
    segundos = time.perf_counter() - inicio
    return ResultadoMedicion(
        "agenda", f"lista lineal (descartada), {eventos_simultaneos} eventos", eventos_simultaneos, operaciones, segundos
    )


# --- §5.2 ciclo completo -------------------------------------------------------

def bench_ciclo_entre_decisiones(cantidad_salas: int, enemigos_activos: int) -> ResultadoMedicion:
    """Tiempo de resolver los eventos entre dos decisiones del jugador (meta < 20 ms).

    Todos los enemigos se activan (rastreadores, errantes con regeneración y
    guardianes que envenenan) y el jugador espera 200 veces. El caso informa el
    peor ciclo y el tamaño promedio de un intervalo del historial.
    """
    juego = _juego_cuadricula(cantidad_salas, enemigos_activos, semilla=5)
    # Igual que hace el controlador al iniciar la partida: lo ya cargado queda
    # fuera de las revisiones del recolector de basura (ver
    # controlador._congelar_objetos_cargados).
    gc.collect()
    gc.freeze()
    decisiones = 200
    total = 0.0
    peor = 0.0
    cambios = 0
    esperar = Accion(TipoAccion.ESPERAR)
    hechas = 0
    try:
        for _ in range(decisiones):
            if juego.esta_terminada():
                break
            inicio = time.perf_counter()
            juego.ejecutar_accion(esperar)
            duracion = time.perf_counter() - inicio
            total += duracion
            peor = max(peor, duracion)
            cambios += juego.historial.cambios_del_ultimo()
            hechas += 1
    finally:
        gc.unfreeze()
    hechas = max(1, hechas)
    return ResultadoMedicion(
        "ciclo",
        f"salas={cantidad_salas} enemigos={enemigos_activos} peor={peor * 1000:.2f} ms "
        f"cambios/intervalo={cambios // hechas}",
        enemigos_activos,
        hechas,
        total,
    )


# --- §4.5 inventario -----------------------------------------------------------

def _objetos(cantidad: int) -> list[InstanciaObjeto]:
    return [InstanciaObjeto(f"x-{i}", "tipo", ClaseObjeto.ARMA) for i in range(cantidad)]


def bench_inventario_lista_doble(tamano: int, operaciones: int) -> ResultadoMedicion:
    """Soltar en cualquier posición y mover al frente."""
    objetos = _objetos(tamano)
    inventario = Inventario(tamano)
    for objeto in objetos:
        inventario.agregar(objeto)
    azar = random.Random(2)
    elegidos = [objetos[azar.randrange(tamano)] for _ in range(operaciones)]
    inicio = time.perf_counter()
    for k in range(operaciones):
        objeto = elegidos[k]
        if k % 2 == 0:
            inventario.quitar(objeto.id)  # soltar el que se está viendo...
            inventario.agregar(objeto)  # ...y volver a recogerlo
        else:
            inventario.mover_al_frente(objeto.id)  # equipar
    segundos = time.perf_counter() - inicio
    return ResultadoMedicion("inventario", f"ListaDoble + TablaOrdenada, {tamano} objetos", tamano, operaciones, segundos)


def bench_inventario_list_python(tamano: int, operaciones: int) -> ResultadoMedicion:
    """ALTERNATIVA: ``list`` con pop(i) / insert(0, x).

    Se le regala la posición (el cursor la conocería): solo se mide el
    desplazamiento de elementos, sin buscar por id.
    """
    lista = _objetos(tamano)
    azar = random.Random(2)
    posiciones = [azar.randrange(tamano) for _ in range(operaciones)]
    inicio = time.perf_counter()
    for k in range(operaciones):
        objeto = lista.pop(posiciones[k])  # O(n - posición)
        if k % 2 == 0:
            lista.append(objeto)
        else:
            lista.insert(0, objeto)  # O(n)
    segundos = time.perf_counter() - inicio
    return ResultadoMedicion("inventario", f"list pop(i)/insert(0) (descartada), {tamano} objetos", tamano, operaciones, segundos)


def bench_inventario_por_posicion(estructura: str, posicion: str, tamano: int, operaciones: int) -> ResultadoMedicion:
    """Soltar el objeto que está en ``posicion`` (inicio / medio / final) y volver a ponerlo ahí.

    Los objetos entran al inventario en un orden revuelto respecto de su id,
    como en el juego (el id depende de dónde salió el objeto, no de cuándo se
    recogió). Así se ve solo el efecto de la POSICIÓN.
    """
    objetos = _objetos(tamano)
    random.Random(4).shuffle(objetos)
    indice = 0 if posicion == "inicio" else tamano // 2 if posicion == "medio" else tamano - 1
    if estructura == "list":
        lista = list(objetos)
        inicio = time.perf_counter()
        for _ in range(operaciones):
            objeto = lista.pop(indice)  # corre los que están después
            lista.insert(indice, objeto)  # y los vuelve a correr
        segundos = time.perf_counter() - inicio
        nombre = f"list, soltar en posición {posicion} (descartada), {tamano} objetos"
    else:
        inventario = Inventario(tamano)
        for objeto in objetos:
            inventario.agregar(objeto)
        objeto = objetos[indice]
        inicio = time.perf_counter()
        for _ in range(operaciones):
            anterior = inventario.anterior_de(objeto.id)
            inventario.quitar(objeto.id)
            inventario.insertar_despues(anterior, objeto)
        segundos = time.perf_counter() - inicio
        nombre = f"ListaDoble + TablaOrdenada, soltar en posición {posicion}, {tamano} objetos"
    return ResultadoMedicion("inventario", nombre, tamano, operaciones, segundos)


# --- §4.6 historial ------------------------------------------------------------

class _Contador:
    __slots__ = ("valor",)

    def __init__(self) -> None:
        self.valor = 0


def bench_historial_registrar_y_revertir(cambios_por_intervalo: int) -> ResultadoMedicion:
    """Costo por cambio de registrar un intervalo completo y revertirlo."""
    objetos = [_Contador() for _ in range(cambios_por_intervalo)]
    historial = Historial(5)
    repeticiones = max(1, 200_000 // cambios_por_intervalo)
    inicio = time.perf_counter()
    for _ in range(repeticiones):
        historial.abrir_intervalo(None)
        for objeto in objetos:
            historial.registrar(CambioAtributo(objeto, "valor", objeto.valor))
            objeto.valor += 1
        historial.cerrar_intervalo()
        historial.retroceder(None)  # CambioAtributo no usa el juego
    segundos = time.perf_counter() - inicio
    return ResultadoMedicion(
        "historial", f"bitácora de deshacer, {cambios_por_intervalo} cambios/intervalo",
        cambios_por_intervalo, repeticiones * cambios_por_intervalo, segundos,
    )


def bench_historial_copia_completa(cantidad_salas: int, enemigos_activos: int) -> ResultadoMedicion:
    """ALTERNATIVA PROHIBIDA (§2.11), solo como contraste: copiar TODO el estado
    en cada decisión. Se usa ``exportar_estado`` como "copia completa"."""
    juego = _juego_cuadricula(cantidad_salas, enemigos_activos, semilla=5)
    for _ in range(20):
        juego.ejecutar_accion(Accion(TipoAccion.ESPERAR))
    repeticiones = 30
    inicio = time.perf_counter()
    for _ in range(repeticiones):
        juego.exportar_estado("bench")
    segundos = time.perf_counter() - inicio
    return ResultadoMedicion(
        "historial", f"copia completa por decisión (prohibida), {cantidad_salas} salas",
        cantidad_salas, repeticiones, segundos,
    )


# --- §4.7 rastro ---------------------------------------------------------------

def bench_rastreadores(cantidad_rastreadores: int, cantidad_salas: int) -> ResultadoMedicion:
    """Debe crecer linealmente con los rastreadores que actúan, no con el tamaño de la cripta."""
    datos, salas, _, _ = _cripta_cuadricula(cantidad_salas, 0, semilla=3)
    mapa = Mapa.construir(datos, salas)
    azar = random.Random(3)
    todas = list(mapa)
    for sala in todas:
        sala.rastro = azar.randint(0, 1000) if azar.random() < 0.5 else None
    ia = IAEnemigos(None)  # elegir_sala_por_rastro no usa el juego
    posiciones = [todas[azar.randrange(len(todas))] for _ in range(cantidad_rastreadores)]
    repeticiones = 50
    inicio = time.perf_counter()
    for _ in range(repeticiones):
        for sala in posiciones:
            ia.elegir_sala_por_rastro(sala, 1200)
    segundos = time.perf_counter() - inicio
    return ResultadoMedicion(
        "rastro", f"{cantidad_rastreadores} rastreadores, {len(todas)} salas", len(todas),
        repeticiones * cantidad_rastreadores, segundos,
    )


def bench_rastro_recorrido(cantidad_rastreadores: int, pasos: int) -> ResultadoMedicion:
    """ALTERNATIVA DESCARTADA: guardar el recorrido del jugador como lista de
    (sala, tiempo) y buscar en ella el rastro de cada vecina. Crece con la
    longitud del recorrido (lo que §4.7 prohíbe)."""
    azar = random.Random(4)
    recorrido = [(azar.randint(1, 400), t * 100) for t in range(pasos)]
    vecinas = [[azar.randint(1, 400) for _ in range(4)] for _ in range(cantidad_rastreadores)]
    repeticiones = 5
    inicio = time.perf_counter()
    for _ in range(repeticiones):
        for ids in vecinas:
            mejor_tiempo = -1
            for sala_id, tiempo in recorrido:  # O(recorrido) por decisión
                if tiempo > mejor_tiempo and (sala_id == ids[0] or sala_id == ids[1] or sala_id == ids[2] or sala_id == ids[3]):
                    mejor_tiempo = tiempo
    segundos = time.perf_counter() - inicio
    return ResultadoMedicion(
        "rastro", f"recorrido como lista (descartada), {pasos} pasos", pasos,
        repeticiones * cantidad_rastreadores, segundos,
    )


# --- §4.8 bitácora -------------------------------------------------------------

def bench_bitacora_circular(mensajes: int, capacidad: int = MENSAJES_VISIBLES) -> ResultadoMedicion:
    bitacora = BitacoraMensajes(capacidad)
    inicio = time.perf_counter()
    for i in range(mensajes):
        bitacora.agregar(i, "mensaje")
    segundos = time.perf_counter() - inicio
    return ResultadoMedicion("bitacora", f"BufferCircular, capacidad {capacidad}", capacidad, mensajes, segundos)


def bench_bitacora_list_pop0(mensajes: int, capacidad: int = MENSAJES_VISIBLES) -> ResultadoMedicion:
    """ALTERNATIVA: ``list`` con append + pop(0) (desplaza todos los mensajes)."""
    lista: list[tuple[int, str]] = []
    inicio = time.perf_counter()
    for i in range(mensajes):
        lista.append((i, "mensaje"))
        if len(lista) > capacidad:
            lista.pop(0)
    segundos = time.perf_counter() - inicio
    return ResultadoMedicion("bitacora", f"list append + pop(0) (descartada), capacidad {capacidad}", capacidad, mensajes, segundos)


# --- criptas sintéticas para medir ---------------------------------------------

def _fichas_bench() -> list[Ficha]:
    rastreador = Ficha("ent_rastreador", "enemigo", "Rastreador", vida_max=50, ataque=3, defensa=1,
                       velocidad=150, comportamiento="rastreador")
    errante = Ficha("ent_errante", "enemigo", "Errante", vida_max=40, ataque=2, defensa=0,
                    velocidad=100, comportamiento="errante", regeneracion=1)
    guardian = Ficha("ent_guardian", "enemigo", "Guardián", vida_max=80, ataque=4, defensa=3,
                     velocidad=90, comportamiento="guardián", veneno=1)
    return [rastreador, errante, guardian]


def _cripta_cuadricula(
    cantidad_salas: int, cantidad_enemigos: int, semilla: int
) -> tuple[DatosCripta, list[DatosSala], list[ContenidoSala], list[Ficha]]:
    """Cuadrícula lado x lado (lado = techo de la raíz) con salidas abiertas."""
    lado = max(2, math.isqrt(max(1, cantidad_salas) - 1) + 1)
    total = lado * lado
    salas: list[DatosSala] = []
    for i in range(total):
        fila, columna = divmod(i, lado)
        salidas: list[DatosSalida] = []
        if fila > 0:
            salidas.append(DatosSalida("N", i - lado + 1))
        if fila < lado - 1:
            salidas.append(DatosSalida("S", i + lado + 1))
        if columna < lado - 1:
            salidas.append(DatosSalida("E", i + 2))
        if columna > 0:
            salidas.append(DatosSalida("O", i))
        salas.append(DatosSala(i + 1, f"Sala {i + 1}", salidas))
    fichas = _fichas_bench()
    azar = random.Random(semilla)
    por_sala: list[list[ColocacionEnemigo]] = [[] for _ in range(total)]
    for k in range(cantidad_enemigos):
        indice = azar.randrange(1, total)  # nunca en la sala inicial
        por_sala[indice].append(ColocacionEnemigo(f"e-{k:05d}", fichas[k % len(fichas)].id))
    contenido = [ContenidoSala(i + 1, por_sala[i], [], []) for i in range(total)]
    datos = DatosCripta(
        "bench", "v1", total, 1, total, 1, total, "llave_bench", 999, 10,
        EstadisticasIniciales(10**9, 1, 2, 100),
    )
    return datos, salas, contenido, fichas


def _juego_cuadricula(cantidad_salas: int, enemigos_activos: int, semilla: int) -> Juego:
    """Partida lista para medir: todo el contenido cargado y TODOS los enemigos activos."""
    datos, salas, contenido, fichas = _cripta_cuadricula(cantidad_salas, enemigos_activos, semilla)
    proveedor = FichasEnMemoria(fichas)
    mapa = Mapa.construir(datos, salas)
    for contenido_sala in contenido:
        mapa.incorporar_contenido(contenido_sala, proveedor)
    juego = Juego(datos, mapa, proveedor, semilla, "bench")
    juego.iniciar()
    for sala in mapa:
        juego._activar_enemigos(sala)  # como si el jugador ya hubiera visitado todo
    return juego
