"""Comportamiento de los enemigos.                                   [Persona A]

§2.8: en su turno, si el enemigo comparte sala con el jugador, ataca y no se
mueve. Si no:
- Guardián: espera; nunca abandona su sala.
- Errante: elige al azar una salida abierta y transitable; si no hay, espera.
- Rastreador: mira SOLO las salas vecinas por salidas abiertas y va a la de
  rastro más fresco con antigüedad < 400; empate → menor id de sala; si no
  hay, espera. No conoce el mapa ni busca rutas (§2.9).
Atacar, moverse y esperar cuestan 100.

Determinismo: el errante arma sus candidatas SIEMPRE en el orden N, S, E, O
y usa ``juego.azar`` (nunca el ``random`` global).

§4.7: la decisión del rastreador cuesta O(salidas de su sala) (como mucho 4),
no O(tamaño de la cripta) ni O(recorrido del jugador): cada sala guarda solo
su último rastro, así que basta mirar las vecinas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cripta.constantes import COSTO_ATACAR, COSTO_ESPERAR, COSTO_MOVER
from cripta.modelo.actores import Comportamiento

if TYPE_CHECKING:
    from cripta.modelo.actores import Enemigo
    from cripta.modelo.juego import Juego
    from cripta.modelo.mapa import Sala


class IAEnemigos:
    def __init__(self, juego: Juego) -> None:
        self._juego = juego

    def actuar(self, enemigo: Enemigo) -> None:
        """Ejecuta el turno completo de ``enemigo`` y programa el siguiente."""
        juego = self._juego
        if not enemigo.esta_vivo():
            return
        if enemigo.sala is juego.jugador.sala:
            costo = self._atacar_jugador(enemigo)
        elif enemigo.comportamiento is Comportamiento.GUARDIAN:
            costo = self._actuar_guardian(enemigo)
        elif enemigo.comportamiento is Comportamiento.ERRANTE:
            costo = self._actuar_errante(enemigo)
        else:
            costo = self._actuar_rastreador(enemigo)
        if not juego.esta_terminada() and enemigo.esta_vivo():
            juego._programar_turno(enemigo, costo)

    def _atacar_jugador(self, enemigo: Enemigo) -> int:
        juego = self._juego
        jugador = juego.jugador
        dano = juego._calcular_dano(enemigo, jugador)
        juego._mensaje(f"{enemigo.etiqueta()} te ataca: -{dano}")
        juego._aplicar_dano(jugador, dano)
        if enemigo.veneno_por_ataque > 0 and jugador.esta_vivo():
            juego.efectos.aplicar_veneno(jugador, enemigo.veneno_por_ataque)
        return COSTO_ATACAR

    def _actuar_guardian(self, enemigo: Enemigo) -> int:
        return COSTO_ESPERAR

    def _actuar_errante(self, enemigo: Enemigo) -> int:
        juego = self._juego
        candidatas = [salida for salida in enemigo.sala.salidas_transitables()]  # orden N, S, E, O
        if not candidatas:
            return COSTO_ESPERAR
        elegida = candidatas[juego.azar.randrange(len(candidatas))]
        juego._mover_enemigo(enemigo, elegida.destino, elegida.direccion)
        return COSTO_MOVER

    def _actuar_rastreador(self, enemigo: Enemigo) -> int:
        juego = self._juego
        destino = self.elegir_sala_por_rastro(enemigo.sala, juego.reloj)
        if destino is None:
            return COSTO_ESPERAR
        direccion = ""
        for salida in enemigo.sala.salidas_transitables():
            if salida.destino is destino:
                direccion = salida.direccion
                break
        juego._mover_enemigo(enemigo, destino, direccion)
        return COSTO_MOVER

    def elegir_sala_por_rastro(self, sala: Sala, reloj: int) -> Sala | None:
        """Vecina accesible con el rastro vigente más fresco, o None. O(grado)."""
        mejor: Sala | None = None
        for salida in sala.salidas_transitables():
            vecina = salida.destino
            if not vecina.rastro_vigente(reloj):
                continue
            if (
                mejor is None
                or vecina.rastro > mejor.rastro
                or (vecina.rastro == mejor.rastro and vecina.id < mejor.id)
            ):
                mejor = vecina
        return mejor
