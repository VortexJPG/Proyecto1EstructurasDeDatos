"""Agenda de eventos: qué ocurre a continuación.                     [Persona A]

§2.3 y §4.1. El juego no tiene rondas: avanza sacando siempre el evento con
menor (tiempo, secuencia). La secuencia es un contador creciente asignado al
PROGRAMAR; toda reprogramación recibe una secuencia nueva.

Requisitos que esta clase debe cumplir:
- Obtener el siguiente evento sin examinar todos (montículo, §4.1).
- Cancelar en O(1) o O(log n) sin recorrer la agenda: muerte de un actor,
  antídoto, fin anticipado de un efecto (§2.10).
- Reprogramar por cambio de velocidad conservando el determinismo (§2.3).
- Poder revertir todo lo anterior (retroceso, §2.11).

Decisión (Documento §4.1): ``MonticuloMin`` + BORRADO PEREZOSO.
- Cancelar = marcar ``evento.cancelado`` en O(1). El evento sigue físicamente
  en el montículo y se descarta cuando llega a la cima.
- Reprogramar = cancelar + programar uno nuevo (secuencia nueva, §2.3).
- La basura está acotada: si los cancelados superan a los vivos (y a un
  mínimo), el montículo se reconstruye en O(n) solo con los vivos.
- ``en_agenda`` indica si el evento está FÍSICAMENTE en el montículo. El
  retroceso lo necesita para saber si "des-cancelar" exige reinsertar.

Estados posibles de un evento:
    pendiente              en_agenda=True   cancelado=False
    cancelado (basura)     en_agenda=True   cancelado=True
    cancelado y descartado en_agenda=False  cancelado=True
    ya ejecutado           en_agenda=False  cancelado=False

Esta clase NO registra nada en el historial: ``Juego._programar``,
``Juego._cancelar_evento`` y ``Juego._avanzar_hasta_decision`` son los que
registran los cambios. Los métodos de "soporte para el retroceso" son los
inversos que usa ``historial.py``.
"""

from __future__ import annotations

from enum import Enum
from typing import Iterator

from cripta.estructuras.monticulo import MonticuloMin

# Basura mínima antes de considerar una compactación (evita reconstruir por
# unos pocos cancelados).
BASURA_MINIMA_PARA_COMPACTAR = 64


class TipoEvento(Enum):
    TURNO_JUGADOR = "turno_jugador"  # punto de decisión del jugador
    TURNO_ENEMIGO = "turno_enemigo"
    # El veneno es una cadena de pulsos: cada pulso programa el siguiente
    # mientras no se pase de los 400 de duración (no hace falta un evento de fin).
    PULSO_VENENO = "pulso_veneno"  # cada 80
    FIN_VELOCIDAD = "fin_velocidad"
    APAGAR_ANTORCHA = "apagar_antorcha"
    PULSO_REGENERACION = "pulso_regeneracion"  # cada 200
    REARME_TRAMPA = "rearme_trampa"
    CIERRE_PUERTA = "cierre_puerta"

    @staticmethod
    def desde_nombre(nombre: str) -> TipoEvento:
        """Inverso de ``tipo.name`` (lo usa la carga de partida)."""
        for tipo in TipoEvento:
            if tipo.name == nombre:
                return tipo
        raise ValueError(f"Tipo de evento desconocido: {nombre!r}")


class Evento:
    """Un evento programado.

    Es un DATO (tipo + objetivo), no una función o lambda: así se puede
    guardar en el archivo de partida y revertir. ``Juego._despachar`` decide
    qué hacer según ``tipo``.
    """

    __slots__ = ("tiempo", "secuencia", "tipo", "objetivo", "cancelado", "en_agenda")

    tiempo: int
    secuencia: int
    tipo: TipoEvento
    objetivo: object  # Actor, Efecto, InstanciaTrampa o Puerta
    cancelado: bool
    en_agenda: bool

    def __init__(self, tiempo: int, secuencia: int, tipo: TipoEvento, objetivo: object) -> None:
        self.tiempo = tiempo
        self.secuencia = secuencia
        self.tipo = tipo
        self.objetivo = objetivo
        self.cancelado = False
        self.en_agenda = False

    def __lt__(self, otro: Evento) -> bool:
        """Menor tiempo primero; empate → menor secuencia (§2.3)."""
        if self.tiempo != otro.tiempo:
            return self.tiempo < otro.tiempo
        return self.secuencia < otro.secuencia

    def __repr__(self) -> str:
        estado = " cancelado" if self.cancelado else ""
        return f"Evento(t={self.tiempo}, sec={self.secuencia}, {self.tipo.name}{estado})"


class Agenda:
    """Cola de prioridad de eventos sobre ``MonticuloMin``."""

    __slots__ = ("_monticulo", "_secuencia", "_activos")

    def __init__(self) -> None:
        self._monticulo: MonticuloMin[Evento] = MonticuloMin()
        self._secuencia = 0
        self._activos = 0  # eventos pendientes (no cancelados) dentro del montículo

    @property
    def siguiente_secuencia(self) -> int:
        """Número que recibirá el próximo evento programado."""
        return self._secuencia

    def programar(self, tiempo: int, tipo: TipoEvento, objetivo: object) -> Evento:
        """Crea un evento con la siguiente secuencia y lo inserta. O(log n)."""
        evento = Evento(tiempo, self._secuencia, tipo, objetivo)
        self._secuencia += 1
        self._insertar(evento)
        return evento

    def cancelar(self, evento: Evento) -> bool:
        """Impide que ``evento`` se ejecute, sin recorrer la agenda. O(1).

        Devuelve True si el evento estaba pendiente y quedó cancelado; False si
        ya estaba cancelado o ya se ejecutó (en ese caso no hay nada que hacer).
        """
        if evento.cancelado or not evento.en_agenda:
            return False
        evento.cancelado = True
        self._activos -= 1
        self._compactar_si_conviene()
        return True

    def reprogramar(self, evento: Evento, nuevo_tiempo: int) -> Evento:
        """Cancela ``evento`` y programa uno equivalente en ``nuevo_tiempo``.

        Recibe secuencia NUEVA (§2.3). Devuelve el evento nuevo: quien guardaba
        el anterior (p. ej. ``actor.evento_turno``) debe actualizar la referencia.
        """
        self.cancelar(evento)
        return self.programar(nuevo_tiempo, evento.tipo, evento.objetivo)

    def ver_siguiente(self) -> Evento | None:
        """Siguiente evento válido sin quitarlo (descarta cancelados de la cima)."""
        self._descartar_cancelados()
        return self._monticulo.ver_min()

    def extraer_siguiente(self) -> Evento | None:
        """Quita y devuelve el siguiente evento válido."""
        self._descartar_cancelados()
        if self._monticulo.esta_vacio():
            return None
        evento = self._monticulo.extraer_min()
        evento.en_agenda = False
        self._activos -= 1
        return evento

    def pendientes(self) -> Iterator[Evento]:
        """Eventos no cancelados, sin orden garantizado (para guardar / --bench)."""
        for evento in self._monticulo.elementos():
            if not evento.cancelado:
                yield evento

    def __len__(self) -> int:
        """Cantidad de eventos NO cancelados."""
        return self._activos

    # --- soporte para el retroceso (solo lo usa historial.py) ----------------

    def restaurar_extraido(self, evento: Evento) -> None:
        """Devuelve a la agenda un evento ya extraído, con su MISMA secuencia."""
        if evento.en_agenda:
            return
        evento.cancelado = False
        self._insertar(evento)

    def deshacer_programado(self, evento: Evento) -> None:
        """Anula un evento que se programó dentro del intervalo revertido.

        Como el retroceso deshace en orden inverso, el contador de secuencia
        vuelve a quedar en el número que tenía ese evento.
        """
        if not evento.cancelado and evento.en_agenda:
            evento.cancelado = True
            self._activos -= 1
        self._secuencia = evento.secuencia
        self._compactar_si_conviene()

    def descancelar(self, evento: Evento) -> None:
        """Inverso de ``cancelar``. Si el evento ya se había descartado del
        montículo (borrado perezoso), se vuelve a insertar."""
        if not evento.cancelado:
            return
        evento.cancelado = False
        if evento.en_agenda:
            self._activos += 1
        else:
            self._insertar(evento)

    def establecer_secuencia(self, valor: int) -> None:
        """Restaura el contador de secuencia (retroceso y carga de partida)."""
        self._secuencia = valor

    def insertar_cargado(self, tiempo: int, secuencia: int, tipo: TipoEvento, objetivo: object) -> Evento:
        """Inserta un evento leído de una partida guardada, con SU secuencia."""
        evento = Evento(tiempo, secuencia, tipo, objetivo)
        self._insertar(evento)
        return evento

    # --- internos ------------------------------------------------------------

    def _insertar(self, evento: Evento) -> None:
        evento.en_agenda = True
        self._monticulo.insertar(evento)
        self._activos += 1

    def _descartar_cancelados(self) -> None:
        """Borrado perezoso: saca de la cima los eventos cancelados."""
        monticulo = self._monticulo
        while True:
            cima = monticulo.ver_min()
            if cima is None or not cima.cancelado:
                return
            monticulo.extraer_min()
            cima.en_agenda = False

    def _compactar_si_conviene(self) -> None:
        """Reconstruye el montículo sin basura si los cancelados ya son mayoría.

        No cambia el orden lógico (es total por tiempo y secuencia), así que no
        afecta el determinismo. Costo O(n), amortizado entre las cancelaciones
        que lo provocaron.
        """
        basura = len(self._monticulo) - self._activos
        if basura < BASURA_MINIMA_PARA_COMPACTAR or basura <= self._activos:
            return
        vivos: list[Evento] = []
        for evento in self._monticulo.elementos():
            if evento.cancelado:
                evento.en_agenda = False
            else:
                vivos.append(evento)
        self._monticulo.reconstruir(vivos)
