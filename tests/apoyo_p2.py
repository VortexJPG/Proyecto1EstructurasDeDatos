"""Apoyo para las pruebas de la Parte II de la Persona A (specs 001, 002 y 003).

- ``CriptaPrueba``: arma criptas pequeñas a mano (salas, salidas con costo y
  puertas, contenido y fichas) y un ``Juego`` listo para jugar.
- ``distancias_oraculo`` / ``decision_oraculo``: el "cálculo desde cero" de
  referencia (spec 001, FR-015; spec 002, FR-001). Es un Dijkstra SIN montículo,
  O(V²), escrito de la forma más literal posible para que sirva de comparación
  independiente del ``BuscadorRutas`` del juego. No usa dict ni set.
"""

from __future__ import annotations

import random

from cripta.bench.sinteticos import FichasEnMemoria
from cripta.modelo.datos import (
    ColocacionEnemigo,
    ColocacionTrampa,
    ContenidoSala,
    DatosCripta,
    DatosSala,
    DatosSalida,
    EstadisticasIniciales,
    Ficha,
)
from cripta.modelo.juego import Juego
from cripta.modelo.mapa import Mapa
from cripta.modelo.rutas import EstrategiaCazador

INF = None


def ficha_cazador(rango: int = 600, velocidad: int = 100, id: str = "ent_cazador") -> Ficha:
    return Ficha(id, "enemigo", "Cazador", vida_max=50, ataque=1, defensa=0, velocidad=velocidad,
                 comportamiento="cazador", rango=rango)


def ficha_enemigo(id: str, comportamiento: str, velocidad: int = 100, ataque: int = 1) -> Ficha:
    return Ficha(id, "enemigo", id, vida_max=30, ataque=ataque, defensa=0, velocidad=velocidad,
                 comportamiento=comportamiento)


FICHAS_BASE = [
    Ficha("itm_antorcha", "antorcha", "Antorcha", peso=1, valor=1, duracion=5000),
    Ficha("itm_pergamino", "pergamino_retroceso", "Pergamino", peso=1, valor=1),
    Ficha("itm_llave", "llave", "Llave", peso=1, valor=0),
    Ficha("trp_pinchos", "trampa", "Pinchos", dano=3, rearme=300),
    ficha_enemigo("ent_rata", "guardián"),
    ficha_enemigo("ent_errante", "errante"),
    ficha_enemigo("ent_rastreador", "rastreador"),
]


def salida(direccion: str, destino: int, costo: int | None = None, cerrada: bool = False,
           llave: str | None = None, cierre: int | None = None) -> DatosSalida:
    return DatosSalida(direccion, destino, cerrada, llave, cierre, costo)


class CriptaPrueba:
    """Cripta construida a mano. ``salas`` = lista de (id, [DatosSalida...])."""

    def __init__(self, salas, inicial: int = 1, salida_id: int | None = None, velocidad: int = 100,
                 vida: int = 1000, inventario: int = 10) -> None:
        self.esqueleto = [DatosSala(id, f"Sala {id}", lista) for id, lista in salas]
        ultima = self.esqueleto[-1].id
        self.datos = DatosCripta(
            id="prueba", version="v1", salas_total=len(self.esqueleto), paginas=1,
            salas_por_pagina=len(self.esqueleto), sala_inicial=inicial,
            sala_salida=salida_id if salida_id is not None else ultima, llave_salida="itm_llave_salida",
            presupuesto_solicitudes=99, inventario_max=inventario,
            jugador=EstadisticasIniciales(vida_max=vida, ataque=5, defensa=0, velocidad=velocidad),
        )
        self.enemigos: list[tuple[int, str, str]] = []  # (sala, instancia, tipo)
        self.objetos: list[tuple[int, str]] = []
        self.trampas: list[tuple[int, str, str]] = []
        self.fichas = list(FICHAS_BASE)

    def con_enemigo(self, sala: int, instancia: str, tipo: str, ficha: Ficha | None = None) -> CriptaPrueba:
        self.enemigos.append((sala, instancia, tipo))
        if ficha is not None:
            self.fichas.append(ficha)
        return self

    def con_objeto(self, sala: int, tipo: str) -> CriptaPrueba:
        self.objetos.append((sala, tipo))
        return self

    def con_trampa(self, sala: int, instancia: str, tipo: str = "trp_pinchos") -> CriptaPrueba:
        self.trampas.append((sala, instancia, tipo))
        return self

    def contenido(self) -> list[ContenidoSala]:
        resultado = []
        for datos_sala in self.esqueleto:
            enemigos = [ColocacionEnemigo(inst, tipo) for sala, inst, tipo in self.enemigos if sala == datos_sala.id]
            objetos = [tipo for sala, tipo in self.objetos if sala == datos_sala.id]
            trampas = [ColocacionTrampa(inst, tipo) for sala, inst, tipo in self.trampas if sala == datos_sala.id]
            resultado.append(ContenidoSala(datos_sala.id, enemigos, objetos, trampas))
        return resultado

    def mapa(self, cargar_contenido: bool = True) -> Mapa:
        mapa = Mapa.construir(self.datos, self.esqueleto)
        if cargar_contenido:
            proveedor = FichasEnMemoria(self.fichas)
            for contenido in self.contenido():
                mapa.incorporar_contenido(contenido, proveedor)
        return mapa

    def juego(self, semilla: int = 1, estrategia: EstrategiaCazador = EstrategiaCazador.COMPARTIDA,
              iniciar: bool = True) -> Juego:
        mapa = self.mapa()
        juego = Juego(self.datos, mapa, FichasEnMemoria(self.fichas), semilla, "Prueba", estrategia)
        if iniciar:
            juego.iniciar()
        return juego


def activar(juego: Juego, *instancias: str) -> None:
    """Activa enemigos lejos del jugador (como si ya los hubiera visto)."""
    for instancia in instancias:
        enemigo = juego.enemigos.obtener(instancia)
        if not enemigo.activo:
            juego._activar_enemigos(enemigo.sala)


# --- oráculo "desde cero" -----------------------------------------------------------


def distancias_oraculo(mapa: Mapa, objetivo, transitable) -> list:
    """dist[sala.indice] = costo mínimo de la sala a ``objetivo`` (None si no hay ruta). O(V²)."""
    salas = [sala for sala in mapa]
    n = len(salas)
    dist = [INF] * n
    hecho = [False] * n
    dist[objetivo.indice] = 0
    for _ in range(n):
        mejor = -1
        for i in range(n):
            if not hecho[i] and dist[i] is not None and (mejor < 0 or dist[i] < dist[mejor]):
                mejor = i
        if mejor < 0:
            break
        hecho[mejor] = True
        # Relajar en sentido inverso: toda salida s (origen -> salas[mejor]).
        for sala in salas:
            for s in sala.salidas:
                if s is None or s.destino is not salas[mejor] or not transitable(s):
                    continue
                nueva = dist[mejor] + s.costo
                j = sala.indice
                if dist[j] is None or nueva < dist[j]:
                    dist[j] = nueva
    return dist


def abierta(s) -> bool:
    return s.puerta is None or not s.puerta.cerrada


def decision_oraculo(juego: Juego, cazador) -> tuple[str, int | None, str | None]:
    """("atacar"|"esperar"|"mover", destino, direccion) según §3.2 calculado desde cero."""
    u = cazador.sala
    jugador = juego.jugador.sala
    if u is jugador:
        return ("atacar", None, None)
    dist = distancias_oraculo(juego.mapa, jugador, abierta)
    d = dist[u.indice]
    if d is None or d > cazador.rango:
        return ("esperar", None, None)
    mejor = None
    for s in u.salidas:
        if s is None or not abierta(s):
            continue
        dv = dist[s.destino.indice]
        if dv is None or s.costo + dv != d:
            continue
        if mejor is None or s.destino.id < mejor.destino.id:
            mejor = s
    return ("mover", mejor.destino.id, mejor.direccion)


def decision_juego(juego: Juego, cazador) -> tuple[str, int | None, str | None]:
    """Lo que decide el juego (sin mover nada) en el mismo formato que el oráculo."""
    if cazador.sala is juego.jugador.sala:
        return ("atacar", None, None)
    s = juego.rutas.decidir(cazador, juego.jugador.sala)
    if s is None:
        return ("esperar", None, None)
    return ("mover", s.destino.id, s.direccion)


# --- criptas aleatorias --------------------------------------------------------------


def cuadricula(lado: int, semilla: int, costos=(100,), prob_puerta: float = 0.0,
               prob_cerrada: float = 0.0, cierre: int | None = None) -> list:
    """Salas de una cuadrícula lado x lado con costos elegidos de ``costos``.

    Cada pasaje declara su costo y su puerta solo en el sentido "ida" (N o E)
    para probar que se comparten. ``prob_cerrada`` cierra algunas puertas.
    """
    azar = random.Random(semilla)
    total = lado * lado
    pasajes: list[tuple[int, int, int, bool, bool]] = []  # (a, b, costo, puerta, cerrada) con b = a+1 (E) o a+lado (S)
    for i in range(total):
        fila, columna = divmod(i, lado)
        if columna < lado - 1:
            puerta = azar.random() < prob_puerta
            pasajes.append((i, i + 1, azar.choice(costos), puerta, puerta and azar.random() < prob_cerrada))
        if fila < lado - 1:
            puerta = azar.random() < prob_puerta
            pasajes.append((i, i + lado, azar.choice(costos), puerta, puerta and azar.random() < prob_cerrada))
    salidas: list[list[DatosSalida]] = [[] for _ in range(total)]
    for a, b, costo, puerta, cerrada in pasajes:
        este = b == a + 1
        ida = "E" if este else "S"
        vuelta = "O" if este else "N"
        if puerta:
            salidas[a].append(DatosSalida(ida, b + 1, cerrada, None, cierre, costo))
        else:
            salidas[a].append(DatosSalida(ida, b + 1, False, None, None, costo))
        salidas[b].append(DatosSalida(vuelta, a + 1))
    resultado = []
    for i in range(total):
        orden = []
        for direccion in ("N", "S", "E", "O"):
            for s in salidas[i]:
                if s.direccion == direccion:
                    orden.append(s)
        resultado.append((i + 1, orden))
    return resultado
