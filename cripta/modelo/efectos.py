"""Efectos temporales y del entorno.                                 [Persona A]

§2.10. Cada efecto es un objeto con referencias a SUS eventos en la agenda,
para poder cancelarlo sin recorrer todos los eventos pendientes (§4.1).

| Efecto       | Regla                                                           |
|--------------|-----------------------------------------------------------------|
| Veneno       | daño cada 80; dura 400 desde que se aplica; antídoto lo cancela |
| Velocidad    | cambia la velocidad; al empezar y al terminar se reajusta la    |
|              | próxima acción con la fórmula de §2.3 (secuencia nueva)         |
| Antorcha     | al encenderse programa su apagado tras ``duracion``             |
| Regeneración | el enemigo recupera N cada 200 sin pasar de vida_max            |
| Trampa       | al activarse aplica daño, se desarma y programa su rearme       |
|              | (300 o lo que diga la ficha)                                    |
| Cierre       | puerta con cierre automático programa su cierre al abrirse      |

Interpretaciones tomadas (documentarlas):
- Origen del veneno: el esquema actual no lo trae, pero ``Ficha.veneno`` es
  opcional. Un enemigo con ``veneno`` envenena al jugador con cada ataque; una
  trampa con ``veneno`` envenena al activarse.
- Veneno = cadena de pulsos en t+80, t+160, ..., hasta t+400 inclusive (5
  pulsos). Volver a envenenar reemplaza el veneno activo (reinicia los 400).
- ``modificador_velocidad`` es ADITIVO (velocidad = base + modificador). Una
  segunda poción de velocidad reemplaza a la primera.
- Encender una antorcha con otra encendida reemplaza a la anterior.
- La regeneración empieza cuando el enemigo se activa.
- El daño de una trampa no se reduce con la defensa (no es un ataque).

Cada actor tiene como mucho UN efecto de cada tipo (``actor.veneno``,
``actor.efecto_velocidad``, ``actor.regeneracion``, ``actor.antorcha``); eso
permite identificar un efecto en el archivo de guardado como
"<tipo>:<id del portador>".

Toda mutación pasa por ``juego._asignar`` / ``juego._programar`` /
``juego._cancelar_evento`` para que el retroceso la pueda invertir. Los
atributos de un ``Efecto`` recién creado se llenan directamente: si se
revierte el intervalo, nada vuelve a apuntar a ese objeto.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from cripta.constantes import REGENERACION_INTERVALO, VENENO_DURACION, VENENO_INTERVALO
from cripta.modelo.eventos import TipoEvento

if TYPE_CHECKING:
    from cripta.modelo.actores import Actor, Enemigo, Jugador
    from cripta.modelo.eventos import Evento
    from cripta.modelo.juego import Juego
    from cripta.modelo.mapa import Puerta
    from cripta.modelo.objetos import InstanciaTrampa


class TipoEfecto(Enum):
    VENENO = "veneno"
    VELOCIDAD = "velocidad"
    ANTORCHA = "antorcha"
    REGENERACION = "regeneracion"

    @staticmethod
    def desde_texto(texto: str) -> TipoEfecto:
        for tipo in TipoEfecto:
            if tipo.value == texto:
                return tipo
        raise ValueError(f"Tipo de efecto desconocido: {texto!r}")


# Atributo del actor donde vive cada tipo de efecto (en el orden de TipoEfecto).
_RANURAS: tuple[str, ...] = ("veneno", "efecto_velocidad", "antorcha", "regeneracion")


def ranura_de(tipo: TipoEfecto) -> str:
    """Nombre del atributo del actor que guarda el efecto de ese tipo."""
    if tipo is TipoEfecto.VENENO:
        return _RANURAS[0]
    if tipo is TipoEfecto.VELOCIDAD:
        return _RANURAS[1]
    if tipo is TipoEfecto.ANTORCHA:
        return _RANURAS[2]
    return _RANURAS[3]


class Efecto:
    """Efecto activo sobre un actor."""

    tipo: TipoEfecto
    portador: Actor
    inicio: int
    fin: int | None
    magnitud: int  # daño por pulso, cambio de velocidad, vida por pulso...
    evento_pulso: Evento | None
    evento_fin: Evento | None
    activo: bool

    def __init__(self, tipo: TipoEfecto, portador: Actor, inicio: int, fin: int | None, magnitud: int) -> None:
        self.tipo = tipo
        self.portador = portador
        self.inicio = inicio
        self.fin = fin
        self.magnitud = magnitud
        self.evento_pulso = None
        self.evento_fin = None
        self.activo = True

    def clave(self) -> str:
        """Identificador estable del efecto, p. ej. "veneno:jugador"."""
        return f"{self.tipo.value}:{self.portador.id}"

    def __repr__(self) -> str:
        return f"Efecto({self.clave()}, magnitud={self.magnitud}, fin={self.fin}, activo={self.activo})"


class GestorEfectos:
    """Aplica, ejecuta y cancela efectos. Usa reloj, agenda e historial del Juego.

    Toda mutación debe registrarse en el historial (vía ``juego._asignar`` o
    equivalente) para que el retroceso la pueda invertir.
    """

    def __init__(self, juego: Juego) -> None:
        self._juego = juego

    # --- veneno -------------------------------------------------------------------

    def aplicar_veneno(self, actor: Actor, dano_por_pulso: int) -> None:
        if dano_por_pulso <= 0 or not actor.esta_vivo():
            return
        juego = self._juego
        if actor.veneno is not None:
            self._terminar(actor.veneno)  # el veneno nuevo reemplaza al anterior
        efecto = Efecto(TipoEfecto.VENENO, actor, juego.reloj, juego.reloj + VENENO_DURACION, dano_por_pulso)
        efecto.evento_pulso = juego._programar(juego.reloj + VENENO_INTERVALO, TipoEvento.PULSO_VENENO, efecto)
        juego._asignar(actor, "veneno", efecto)
        juego._mensaje(f"{actor.etiqueta()} queda envenenado ({dano_por_pulso} de daño cada {VENENO_INTERVALO}).")

    def pulso_veneno(self, efecto: Efecto) -> None:
        """Aplica el daño y programa el siguiente pulso si el efecto sigue activo."""
        if not efecto.activo:
            return
        juego = self._juego
        actor = efecto.portador
        juego._asignar(efecto, "evento_pulso", None)
        juego._mensaje(f"El veneno daña a {actor.etiqueta()}: -{efecto.magnitud}")
        juego._aplicar_dano(actor, efecto.magnitud)
        if not efecto.activo:
            return  # el actor murió y sus efectos se cancelaron
        siguiente = juego.reloj + VENENO_INTERVALO
        if siguiente <= efecto.fin:
            juego._asignar(efecto, "evento_pulso", juego._programar(siguiente, TipoEvento.PULSO_VENENO, efecto))
        else:
            self._terminar(efecto)
            juego._mensaje(f"El veneno de {actor.etiqueta()} se disipa.")

    def cancelar_veneno(self, actor: Actor) -> None:
        """Antídoto: los pulsos futuros cancelados no hacen daño (Apéndice B)."""
        if actor.veneno is not None:
            self._terminar(actor.veneno)

    # --- velocidad ----------------------------------------------------------------

    def aplicar_velocidad(self, actor: Actor, modificador: int, duracion: int) -> None:
        if modificador == 0 or duracion <= 0:
            return
        juego = self._juego
        if actor.efecto_velocidad is not None:
            self.terminar_velocidad(actor.efecto_velocidad)  # reemplaza al anterior
        velocidad_anterior = actor.velocidad
        juego._asignar(actor, "modificador_velocidad", actor.modificador_velocidad + modificador)
        efecto = Efecto(TipoEfecto.VELOCIDAD, actor, juego.reloj, juego.reloj + duracion, modificador)
        efecto.evento_fin = juego._programar(juego.reloj + duracion, TipoEvento.FIN_VELOCIDAD, efecto)
        juego._asignar(actor, "efecto_velocidad", efecto)
        juego._mensaje(f"La velocidad de {actor.etiqueta()} cambia: {velocidad_anterior} -> {actor.velocidad}.")
        self.reajustar_turno(actor, velocidad_anterior, actor.velocidad)

    def terminar_velocidad(self, efecto: Efecto) -> None:
        if not efecto.activo:
            return
        juego = self._juego
        actor = efecto.portador
        velocidad_anterior = actor.velocidad
        self._terminar(efecto)
        juego._asignar(actor, "modificador_velocidad", actor.modificador_velocidad - efecto.magnitud)
        if actor.esta_vivo():
            juego._mensaje(f"Termina el efecto de velocidad de {actor.etiqueta()} ({actor.velocidad}).")
            self.reajustar_turno(actor, velocidad_anterior, actor.velocidad)

    def reajustar_turno(self, actor: Actor, velocidad_anterior: int, velocidad_nueva: int) -> None:
        """§2.3: restante_nuevo = max(1, (tiempo_siguiente - t) * v_ant // v_nueva).

        Reprograma ``actor.evento_turno`` con secuencia NUEVA. Si el actor no
        tiene turno pendiente (está ejecutando su acción), no hay nada que
        escalar: su próximo turno se programará con la velocidad nueva.
        """
        evento = actor.evento_turno
        if evento is None or velocidad_anterior == velocidad_nueva:
            return
        juego = self._juego
        restante = max(1, (evento.tiempo - juego.reloj) * velocidad_anterior // velocidad_nueva)
        juego._asignar(actor, "evento_turno", juego._reprogramar(evento, juego.reloj + restante))

    # --- antorcha -----------------------------------------------------------------

    def encender_antorcha(self, jugador: Jugador, duracion: int) -> None:
        juego = self._juego
        if jugador.antorcha is not None:
            self._terminar(jugador.antorcha)  # la nueva reemplaza a la anterior
        duracion = max(1, duracion)
        efecto = Efecto(TipoEfecto.ANTORCHA, jugador, juego.reloj, juego.reloj + duracion, 0)
        efecto.evento_fin = juego._programar(juego.reloj + duracion, TipoEvento.APAGAR_ANTORCHA, efecto)
        juego._asignar(jugador, "antorcha", efecto)
        juego._mensaje(f"Enciendes una antorcha (dura hasta t={efecto.fin}).")

    def apagar_antorcha(self, efecto: Efecto) -> None:
        if not efecto.activo:
            return
        self._terminar(efecto)
        self._juego._mensaje("La antorcha se apaga.")

    # --- regeneración -------------------------------------------------------------

    def iniciar_regeneracion(self, enemigo: Enemigo, cantidad: int) -> None:
        if cantidad <= 0:
            return
        juego = self._juego
        efecto = Efecto(TipoEfecto.REGENERACION, enemigo, juego.reloj, None, cantidad)
        efecto.evento_pulso = juego._programar(
            juego.reloj + REGENERACION_INTERVALO, TipoEvento.PULSO_REGENERACION, efecto
        )
        juego._asignar(enemigo, "regeneracion", efecto)

    def pulso_regeneracion(self, efecto: Efecto) -> None:
        """La vida regenerada nunca supera vida_max (Apéndice B)."""
        if not efecto.activo:
            return
        juego = self._juego
        enemigo = efecto.portador
        juego._curar(enemigo, efecto.magnitud)
        juego._asignar(
            efecto,
            "evento_pulso",
            juego._programar(juego.reloj + REGENERACION_INTERVALO, TipoEvento.PULSO_REGENERACION, efecto),
        )

    # --- trampas ------------------------------------------------------------------

    def activar_trampa(self, trampa: InstanciaTrampa, jugador: Jugador) -> None:
        """Al entrar el jugador, inmediatamente tras el movimiento (§2.10)."""
        if not trampa.armada:
            return
        juego = self._juego
        juego._asignar(trampa, "armada", False)
        juego._asignar(
            trampa, "evento_rearme", juego._programar(juego.reloj + trampa.rearme, TipoEvento.REARME_TRAMPA, trampa)
        )
        juego._mensaje(f"¡Se activa {trampa.nombre}! -{trampa.dano}")
        juego._aplicar_dano(jugador, trampa.dano)
        if trampa.veneno > 0:
            self.aplicar_veneno(jugador, trampa.veneno)

    def rearmar_trampa(self, trampa: InstanciaTrampa) -> None:
        juego = self._juego
        juego._asignar(trampa, "armada", True)
        juego._asignar(trampa, "evento_rearme", None)

    # --- puertas ------------------------------------------------------------------

    def programar_cierre(self, puerta: Puerta) -> None:
        if puerta.cierre_automatico is None:
            return
        juego = self._juego
        juego._asignar(
            puerta,
            "evento_cierre",
            juego._programar(juego.reloj + puerta.cierre_automatico, TipoEvento.CIERRE_PUERTA, puerta),
        )

    def cerrar_puerta(self, puerta: Puerta) -> None:
        """Si hay un actor del otro lado, se queda ahí (Apéndice B)."""
        juego = self._juego
        juego._asignar(puerta, "cerrada", True)
        juego._asignar(puerta, "evento_cierre", None)
        for salida in juego.jugador.sala.salidas:
            if salida is not None and salida.puerta is puerta:
                juego._mensaje(f"La puerta {salida.direccion} se cierra sola.")
                break

    # --- muerte -------------------------------------------------------------------

    def cancelar_efectos_de(self, actor: Actor) -> None:
        """Cancela todos los efectos del actor (al morir), en O(cantidad de efectos)."""
        for ranura in _RANURAS:
            efecto = getattr(actor, ranura)
            if efecto is not None:
                self._terminar(efecto)

    # --- internos -----------------------------------------------------------------

    def _terminar(self, efecto: Efecto) -> None:
        """Cancela los eventos pendientes del efecto y lo quita de su portador.

        No toca la velocidad: ``terminar_velocidad`` se encarga de eso.
        """
        juego = self._juego
        if efecto.evento_pulso is not None:
            juego._cancelar_evento(efecto.evento_pulso)
            juego._asignar(efecto, "evento_pulso", None)
        if efecto.evento_fin is not None:
            juego._cancelar_evento(efecto.evento_fin)
            juego._asignar(efecto, "evento_fin", None)
        juego._asignar(efecto, "activo", False)
        ranura = ranura_de(efecto.tipo)
        if getattr(efecto.portador, ranura) is efecto:
            juego._asignar(efecto.portador, ranura, None)
