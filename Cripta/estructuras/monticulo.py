"""Montículo binario mínimo.                    [Persona A — entregar temprano]

Base de la agenda de eventos (§4.1): obtener el evento con menor
(tiempo, secuencia) sin examinar todos los eventos. Almacenamiento en
``list`` (permitido por §7): hijos de i en 2i+1 y 2i+2, padre en (i-1)//2.

Los elementos se comparan con ``<``; ``Evento`` define ``__lt__`` por
(tiempo, secuencia), lo que da un orden total y determinista.

Decisión tomada (Documento §4.1): la cancelación y la reprogramación se
resuelven con BORRADO PEREZOSO en ``modelo.eventos.Agenda`` (el evento se
marca como cancelado y se descarta cuando llega a la cima). Por eso este
montículo NO es indexado: no necesita ``eliminar_en`` ni ``actualizar_en``.
La alternativa (b), montículo indexado, se descartó porque cada intercambio
tendría que actualizar la posición guardada en el evento y cancelar costaría
O(log n) en vez de O(1).

Para que la basura no crezca sin control, ``reconstruir`` permite volver a
armar el montículo en O(n) solo con los elementos vivos (lo usa la Agenda).

Alternativa a medir con --bench: lista sin ordenar con búsqueda lineal del
mínimo (lo que §4.1 prohíbe hacer en el juego, pero sirve como contraste).
"""

from __future__ import annotations

from typing import Generic, Iterator, TypeVar

T = TypeVar("T")


class MonticuloMin(Generic[T]):
    """Montículo binario de mínimos sobre una ``list``."""

    __slots__ = ("_datos",)

    def __init__(self) -> None:
        self._datos: list[T] = []

    def insertar(self, elemento: T) -> None:
        """Agrega ``elemento`` y lo sube a su lugar. O(log n)."""
        self._datos.append(elemento)
        self._subir(len(self._datos) - 1)

    def extraer_min(self) -> T:
        """Quita y devuelve el mínimo. O(log n). IndexError si está vacío."""
        datos = self._datos
        if not datos:
            raise IndexError("extraer_min: el montículo está vacío")
        ultimo = datos.pop()
        if not datos:
            # Era el único elemento.
            return ultimo
        minimo = datos[0]
        # El último elemento ocupa la raíz y se hunde hasta su lugar.
        datos[0] = ultimo
        self._bajar(0)
        return minimo

    def ver_min(self) -> T | None:
        """Devuelve el mínimo sin quitarlo (None si está vacío). O(1)."""
        if self._datos:
            return self._datos[0]
        return None

    def esta_vacio(self) -> bool:
        return not self._datos

    def __len__(self) -> int:
        return len(self._datos)

    def elementos(self) -> Iterator[T]:
        """Itera los elementos en el orden interno del arreglo (NO ordenado).

        Útil para guardar la partida y para --bench. No modificar el
        montículo mientras se recorre.
        """
        return iter(self._datos)

    def reconstruir(self, elementos: list[T]) -> None:
        """Reemplaza el contenido por ``elementos`` en O(n) (algoritmo de Floyd).

        Se hunden los nodos internos desde el último padre hasta la raíz.
        """
        self._datos = list(elementos)
        for posicion in range(len(self._datos) // 2 - 1, -1, -1):
            self._bajar(posicion)

    # --- internos -------------------------------------------------------------
    # Se usa la técnica del "hueco": en vez de intercambiar en cada nivel, se
    # guarda el elemento que se mueve y se corren los demás; al final se
    # escribe una sola vez. Hace la mitad de escrituras que los intercambios.

    def _subir(self, posicion: int) -> None:
        datos = self._datos
        elemento = datos[posicion]
        while posicion > 0:
            padre = (posicion - 1) // 2
            if elemento < datos[padre]:
                datos[posicion] = datos[padre]
                posicion = padre
            else:
                break
        datos[posicion] = elemento

    def _bajar(self, posicion: int) -> None:
        datos = self._datos
        cantidad = len(datos)
        elemento = datos[posicion]
        while True:
            hijo = 2 * posicion + 1
            if hijo >= cantidad:
                break
            derecho = hijo + 1
            if derecho < cantidad and datos[derecho] < datos[hijo]:
                hijo = derecho
            if datos[hijo] < elemento:
                datos[posicion] = datos[hijo]
                posicion = hijo
            else:
                break
        datos[posicion] = elemento
