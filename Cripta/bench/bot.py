"""Jugador automático para medir con partidas reales (--bench).           [A y B]

No juega "bien": explora. Si hay enemigos en la sala, ataca; si hay objetos y
cabe uno más, recoge; equipa armas y armaduras; abre puertas para las que
tiene la llave; si no, se mueve, prefiriendo salas que todavía no visitó.
Es determinista: con la misma semilla hace siempre lo mismo.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from cripta.adaptadores.fuente_datos import ErrorFuenteDatos
from cripta.modelo.acciones import Accion, TipoAccion
from cripta.modelo.objetos import ClaseObjeto

if TYPE_CHECKING:
    from cripta.controlador.controlador import Controlador
    from cripta.modelo.juego import Juego


def elegir_accion(juego: Juego, azar: random.Random, visitadas: list[int]) -> Accion:
    jugador = juego.jugador
    sala = jugador.sala
    enemigos = juego.enemigos_en_sala()
    if enemigos:
        return Accion(TipoAccion.ATACAR, objetivo=enemigos[0].id)
    if not jugador.inventario.esta_lleno():
        for objeto in sala.objetos_suelo:
            return Accion(TipoAccion.RECOGER, objetivo=objeto.id)
    for objeto in jugador.inventario:
        if objeto.clase in (ClaseObjeto.ARMA, ClaseObjeto.ARMADURA) and objeto is not jugador.arma \
                and objeto is not jugador.armadura:
            return Accion(TipoAccion.EQUIPAR, objetivo=objeto.id)
        if objeto.clase is ClaseObjeto.POCION and jugador.vida < jugador.vida_max // 2:
            return Accion(TipoAccion.USAR, objetivo=objeto.id)
    for salida in sala.salidas:
        if salida is not None and salida.puerta is not None and salida.puerta.cerrada:
            if salida.puerta.llave is None or jugador.tiene_llave(salida.puerta.llave):
                return Accion(TipoAccion.ABRIR, direccion=salida.direccion)
    abiertas = [salida for salida in sala.salidas_transitables()]
    nuevas = [salida for salida in abiertas if salida.destino.id not in visitadas]
    if nuevas:
        return Accion(TipoAccion.MOVER, direccion=nuevas[0].direccion)
    if abiertas:
        return Accion(TipoAccion.MOVER, direccion=abiertas[azar.randrange(len(abiertas))].direccion)
    return Accion(TipoAccion.ESPERAR)


def jugar(controlador: Controlador, decisiones: int, semilla: int) -> int:
    """Juega hasta ``decisiones`` acciones (o hasta que termine). Devuelve las aceptadas."""
    juego = controlador.juego
    azar = random.Random(semilla)
    visitadas: list[int] = []
    aceptadas = 0
    for _ in range(decisiones):
        if juego is None or juego.esta_terminada():
            break
        if juego.jugador.sala.id not in visitadas:
            visitadas.append(juego.jugador.sala.id)
        try:
            if controlador.ejecutar_accion(elegir_accion(juego, azar, visitadas)).aceptada:
                aceptadas += 1
        except ErrorFuenteDatos:
            break
        juego = controlador.juego
    return aceptadas
