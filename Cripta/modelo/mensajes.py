"""Bitácora de mensajes en pantalla.                                 [Persona A]

§4.8: la interfaz muestra solo los últimos 20 mensajes; la memoria debe ser
constante y agregar un mensaje no puede desplazar los 19 anteriores.
Implementado sobre ``BufferCircular``: al llenarse, el mensaje nuevo ocupa la
ranura del más antiguo.

Cada mensaje lleva un número correlativo (``total`` cuenta todos los que se han
agregado). Con ese número la vista separa "Tu turno" de "Turno de los
enemigos" sin guardar nada extra (ver ``Juego.marca_turno``).

El modelo escribe aquí ("Rata gigante #1 te ataca: -4") y la vista solo lee.
Los mensajes NO forman parte del estado reversible: son lo que el jugador ya
vio, no estado del juego.
"""

from __future__ import annotations

from typing import Iterator

from cripta.estructuras.buffer_circular import BufferCircular


class BitacoraMensajes:
    def __init__(self, capacidad: int) -> None:
        """``capacidad`` = constantes.MENSAJES_VISIBLES."""
        self._buffer: BufferCircular[tuple[int, int, str]] = BufferCircular(capacidad)
        self._total = 0  # mensajes agregados desde el inicio (el próximo recibe este número)

    @property
    def total(self) -> int:
        return self._total

    def agregar(self, tiempo: int, texto: str) -> None:
        """O(1); sobrescribe el más antiguo si está llena."""
        self._buffer.agregar((self._total, tiempo, texto))
        self._total += 1

    def ultimos(self) -> Iterator[tuple[int, str]]:
        """Pares (tiempo, texto) del más antiguo al más reciente."""
        for _, tiempo, texto in self._buffer:
            yield tiempo, texto

    def ultimos_numerados(self) -> Iterator[tuple[int, int, str]]:
        """Tríos (número, tiempo, texto) del más antiguo al más reciente."""
        return iter(self._buffer)

    def __len__(self) -> int:
        return len(self._buffer)
