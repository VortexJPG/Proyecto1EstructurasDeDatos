"""Cola FIFO con nodos enlazados.                                     [Persona B]

Usos: recorrido en anchura (BFS) sobre el esqueleto para elegir qué salas
precargar (§4.2) y los ids de catálogo pendientes en orden de descubrimiento
(§4.3). Encolar y desencolar cuestan O(1): solo se mueven los punteros del
frente y del final. La alternativa medida es ``list.pop(0)``, que corre todos
los elementos (O(n)).
"""

from __future__ import annotations

from typing import Generic, Iterator, TypeVar

T = TypeVar("T")


class _Nodo(Generic[T]):
    __slots__ = ("valor", "siguiente")

    def __init__(self, valor: T) -> None:
        self.valor = valor
        self.siguiente = None


class ColaEnlazada(Generic[T]):
    def __init__(self) -> None:
        self._frente: _Nodo[T] | None = None
        self._final: _Nodo[T] | None = None
        self._tama = 0

    def encolar(self, elemento: T) -> None:
        nodo = _Nodo(elemento)
        if self._final is None:
            self._frente = self._final = nodo
        else:
            self._final.siguiente = nodo  # type: ignore[union-attr]
            self._final = nodo
        self._tama += 1

    def desencolar(self) -> T:
        if self._frente is None:
            raise IndexError("cola vacía")
        nodo = self._frente
        self._frente = nodo.siguiente
        if self._frente is None:
            self._final = None
        self._tama -= 1
        return nodo.valor

    def ver_frente(self) -> T | None:
        return None if self._frente is None else self._frente.valor

    def esta_vacia(self) -> bool:
        return self._frente is None

    def __len__(self) -> int:
        return self._tama

    def __iter__(self) -> Iterator[T]:
        nodo = self._frente
        while nodo is not None:
            yield nodo.valor
            nodo = nodo.siguiente
