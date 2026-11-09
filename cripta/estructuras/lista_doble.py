"""Lista doblemente enlazada con nodos expuestos.                     [Persona A]

Usos:
- Inventario (§4.5): recorrer adelante / atrás desde un cursor, quitar el
  objeto que se está viendo en O(1) sin importar su posición, y mover al
  frente en O(1) al equipar.
- Enemigos y objetos de una sala: quitar uno cuando se mueve, muere o se
  recoge.

Las operaciones reciben y devuelven ``NodoDoble`` para que quien guarde el
nodo (p. ej. una ``TablaOrdenada`` id → nodo, o ``Enemigo.nodo_en_sala``)
pueda operar en O(1). Alternativa medida con --bench: ``list`` de Python con
``pop(i)`` / ``insert(0, x)``, que cuestan O(n).

Decisión: la lista doble "de libro", con un puntero al primer nodo y otro al
último. El primero tiene ``anterior = None`` y el último ``siguiente = None``
(no es circular). Por eso insertar y quitar revisan esos casos: si el nodo
queda primero o último, se actualiza ``_primero`` / ``_ultimo``.

Cada nodo sabe en qué lista está (``nodo.lista``; None = desenganchado). Con
eso se comprueba en O(1) que un nodo pertenece a ESTA lista antes de
moverlo o quitarlo. El retroceso (§4.6) lo aprovecha: puede volver a
enganchar EL MISMO nodo en su posición original con ``reenlazar_despues``.
"""

from __future__ import annotations

from typing import Generic, Iterator, TypeVar

T = TypeVar("T")


class NodoDoble(Generic[T]):
    """Nodo de la lista. Quien lo recibe puede guardarlo para operar en O(1)."""

    __slots__ = ("valor", "anterior", "siguiente", "lista")

    valor: T
    anterior: NodoDoble[T] | None
    siguiente: NodoDoble[T] | None
    lista: ListaDoble[T] | None  # la lista en la que está (None = desenganchado)

    def __init__(self, valor: T) -> None:
        self.valor = valor
        self.anterior = None
        self.siguiente = None
        self.lista = None


class ListaDoble(Generic[T]):
    """Lista doblemente enlazada con punteros al primero y al último."""

    __slots__ = ("_primero", "_ultimo", "_tamano")

    def __init__(self) -> None:
        self._primero: NodoDoble[T] | None = None
        self._ultimo: NodoDoble[T] | None = None
        self._tamano = 0

    def __len__(self) -> int:
        return self._tamano

    def esta_vacia(self) -> bool:
        return self._tamano == 0

    @property
    def primero(self) -> NodoDoble[T] | None:
        return self._primero

    @property
    def ultimo(self) -> NodoDoble[T] | None:
        return self._ultimo

    # --- inserción ------------------------------------------------------------------

    def agregar_al_frente(self, valor: T) -> NodoDoble[T]:
        """O(1). Devuelve el nodo creado."""
        nodo = NodoDoble(valor)
        self._enlazar_despues(None, nodo)
        return nodo

    def agregar_al_final(self, valor: T) -> NodoDoble[T]:
        """O(1). Devuelve el nodo creado."""
        nodo = NodoDoble(valor)
        self._enlazar_despues(self._ultimo, nodo)
        return nodo

    def insertar_despues(self, referencia: NodoDoble[T] | None, valor: T) -> NodoDoble[T]:
        """Inserta ``valor`` justo después de ``referencia`` (None = al frente). O(1).

        Lo necesita el retroceso para devolver un objeto a su posición original.
        """
        self._validar_referencia(referencia)
        nodo = NodoDoble(valor)
        self._enlazar_despues(referencia, nodo)
        return nodo

    def reenlazar_despues(self, referencia: NodoDoble[T] | None, nodo: NodoDoble[T]) -> None:
        """Vuelve a enganchar un nodo YA QUITADO justo después de ``referencia``. O(1).

        ``None`` = al frente. Reutilizar el mismo nodo (en vez de crear otro)
        mantiene válidas las referencias que otros guardan a él (por ejemplo
        ``Enemigo.nodo_en_sala`` o los cambios del historial).
        """
        if self.esta_enlazado(nodo):
            raise ValueError("reenlazar_despues: el nodo todavía está en una lista")
        self._validar_referencia(referencia)
        self._enlazar_despues(referencia, nodo)

    # --- eliminación y movimiento ----------------------------------------------------

    def quitar(self, nodo: NodoDoble[T]) -> T:
        """Desengancha ``nodo`` en O(1) y devuelve su valor."""
        if nodo.lista is not self:
            raise ValueError("quitar: el nodo no está en esta lista")
        self._desenlazar(nodo)
        return nodo.valor

    def mover_al_frente(self, nodo: NodoDoble[T]) -> None:
        """O(1). Usado al equipar (§2.7)."""
        self.mover_despues(nodo, None)

    def mover_al_final(self, nodo: NodoDoble[T]) -> None:
        """O(1)."""
        if nodo.lista is not self:
            raise ValueError("mover_al_final: el nodo no está en esta lista")
        if self._ultimo is nodo:
            return
        self._desenlazar(nodo)
        self._enlazar_despues(self._ultimo, nodo)

    def mover_despues(self, nodo: NodoDoble[T], referencia: NodoDoble[T] | None) -> None:
        """Mueve ``nodo`` justo después de ``referencia`` (None = al frente). O(1)."""
        if nodo.lista is not self:
            raise ValueError("mover_despues: el nodo no está en esta lista")
        self._validar_referencia(referencia)
        if referencia is nodo:
            return
        actual = self._primero if referencia is None else referencia.siguiente
        if actual is nodo:
            return  # ya está en esa posición
        self._desenlazar(nodo)
        self._enlazar_despues(referencia, nodo)

    # --- navegación (para cursores) --------------------------------------------------

    def siguiente(self, nodo: NodoDoble[T]) -> NodoDoble[T] | None:
        """Nodo que sigue a ``nodo`` (None si ``nodo`` es el último)."""
        return nodo.siguiente

    def anterior(self, nodo: NodoDoble[T]) -> NodoDoble[T] | None:
        """Nodo que precede a ``nodo`` (None si ``nodo`` es el primero)."""
        return nodo.anterior

    def contiene_nodo(self, nodo: NodoDoble[T]) -> bool:
        """True si ``nodo`` está en ESTA lista. O(1)."""
        return nodo.lista is self

    @staticmethod
    def esta_enlazado(nodo: NodoDoble[T]) -> bool:
        """True si el nodo está dentro de alguna lista (no fue quitado)."""
        return nodo.lista is not None

    # --- recorridos ------------------------------------------------------------------

    def __iter__(self) -> Iterator[T]:
        """Recorre del frente al final."""
        nodo = self._primero
        while nodo is not None:
            siguiente = nodo.siguiente  # permite quitar el nodo actual mientras se recorre
            yield nodo.valor
            nodo = siguiente

    def iterar_reversa(self) -> Iterator[T]:
        """Recorre del final al frente."""
        nodo = self._ultimo
        while nodo is not None:
            anterior = nodo.anterior
            yield nodo.valor
            nodo = anterior

    def nodos(self) -> Iterator[NodoDoble[T]]:
        """Recorre los nodos del frente al final (para buscar uno y operar en O(1))."""
        nodo = self._primero
        while nodo is not None:
            siguiente = nodo.siguiente
            yield nodo
            nodo = siguiente

    def a_lista(self) -> list[T]:
        """Copia los valores en orden a una ``list`` (p. ej. para ordenar una vista)."""
        return [valor for valor in self]

    # --- internos ------------------------------------------------------------------

    def _validar_referencia(self, referencia: NodoDoble[T] | None) -> None:
        if referencia is not None and referencia.lista is not self:
            raise ValueError("el nodo de referencia no está en la lista")

    def _enlazar_despues(self, referencia: NodoDoble[T] | None, nodo: NodoDoble[T]) -> None:
        """Engancha ``nodo`` después de ``referencia`` (None = como primero)."""
        if referencia is None:
            siguiente = self._primero
            self._primero = nodo
        else:
            siguiente = referencia.siguiente
            referencia.siguiente = nodo
        nodo.anterior = referencia
        nodo.siguiente = siguiente
        if siguiente is None:
            self._ultimo = nodo  # quedó al final
        else:
            siguiente.anterior = nodo
        nodo.lista = self
        self._tamano += 1

    def _desenlazar(self, nodo: NodoDoble[T]) -> None:
        anterior = nodo.anterior
        siguiente = nodo.siguiente
        if anterior is None:
            self._primero = siguiente  # era el primero
        else:
            anterior.siguiente = siguiente
        if siguiente is None:
            self._ultimo = anterior  # era el último
        else:
            siguiente.anterior = anterior
        nodo.anterior = None
        nodo.siguiente = None
        nodo.lista = None
        self._tamano -= 1
