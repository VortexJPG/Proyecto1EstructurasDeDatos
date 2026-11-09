"""Buffer circular de capacidad fija.                                [Persona A]

Usos previstos:
- Bitácora en pantalla (§4.8): últimos 20 mensajes, memoria constante, y
  agregar sin desplazar físicamente los anteriores (se sobrescribe la ranura
  del más antiguo).
- Historial de retroceso (§4.6): últimos 5 intervalos. Al superar el límite
  se descarta el más antiguo, y deshacer saca el más reciente (pila acotada).

Alternativa a medir con --bench: ``list`` con ``append`` + ``pop(0)``.

Representación: una ``list`` de ``capacidad`` ranuras creada UNA sola vez,
el índice del elemento más antiguo (``_inicio``) y la cantidad guardada.
La ranura del elemento k (0 = más antiguo) es ``(_inicio + k) % capacidad``.
"""

from __future__ import annotations

from typing import Generic, Iterator, TypeVar

T = TypeVar("T")


class BufferCircular(Generic[T]):
    """Arreglo de tamaño fijo con índices que dan la vuelta (módulo capacidad)."""

    __slots__ = ("_ranuras", "_inicio", "_tamano")

    def __init__(self, capacidad: int) -> None:
        if capacidad < 1:
            raise ValueError(f"La capacidad del buffer debe ser al menos 1 (se recibió {capacidad})")
        self._ranuras: list[T | None] = [None] * capacidad
        self._inicio = 0  # ranura del elemento más antiguo
        self._tamano = 0

    @property
    def capacidad(self) -> int:
        return len(self._ranuras)

    def __len__(self) -> int:
        return self._tamano

    def esta_lleno(self) -> bool:
        return self._tamano == len(self._ranuras)

    def esta_vacio(self) -> bool:
        return self._tamano == 0

    def agregar(self, elemento: T) -> T | None:
        """Agrega al extremo reciente. O(1).

        Si estaba lleno, sobrescribe el más antiguo y lo devuelve (si no, None).
        """
        capacidad = len(self._ranuras)
        if self._tamano < capacidad:
            self._ranuras[(self._inicio + self._tamano) % capacidad] = elemento
            self._tamano += 1
            return None
        # Lleno: la ranura del más antiguo pasa a ser la del más reciente.
        descartado = self._ranuras[self._inicio]
        self._ranuras[self._inicio] = elemento
        self._inicio = (self._inicio + 1) % capacidad
        return descartado

    def extraer_reciente(self) -> T | None:
        """Quita y devuelve el elemento más reciente (None si está vacío). O(1)."""
        if self._tamano == 0:
            return None
        ranura = (self._inicio + self._tamano - 1) % len(self._ranuras)
        elemento = self._ranuras[ranura]
        self._ranuras[ranura] = None  # no retener referencias innecesarias
        self._tamano -= 1
        return elemento

    def ver_reciente(self) -> T | None:
        if self._tamano == 0:
            return None
        return self._ranuras[(self._inicio + self._tamano - 1) % len(self._ranuras)]

    def __iter__(self) -> Iterator[T]:
        """Recorre del más antiguo al más reciente."""
        capacidad = len(self._ranuras)
        for k in range(self._tamano):
            yield self._ranuras[(self._inicio + k) % capacidad]

    def limpiar(self) -> None:
        for i in range(len(self._ranuras)):
            self._ranuras[i] = None
        self._inicio = 0
        self._tamano = 0
