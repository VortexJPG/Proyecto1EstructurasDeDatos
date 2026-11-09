"""Inventario del jugador.                                           [Persona A]

§2.7 y §4.5:
- Recorrer hacia adelante y hacia atrás desde la posición actual (cursor).
- Soltar el objeto que se está viendo, en cualquier posición, sin que el costo
  dependa de la posición.
- Equipar mueve el objeto al FRENTE del orden real.
- Vistas ordenadas por peso, valor o nombre SIN alterar el orden real
  (usar ``estructuras.ordenamiento.ordenar`` de Persona B).
- Con ``inventario_max`` objetos, recoger queda prohibido.

Diseño: ``ListaDoble`` (orden real) + ``TablaOrdenada`` id → nodo + un nodo
cursor. El replay identifica los objetos por id, así que primero se busca el
nodo por su id (búsqueda binaria, O(log n)) y después se desengancha o se
mueve en O(1). Nada de eso depende de la POSICIÓN del objeto en el
inventario, que es lo que pide §4.5 (con una ``list`` sí dependería: hay que
correr los que vienen después). El cursor da la vuelta: después del último
viene el primero.

Retroceso: para devolver un objeto a su posición original se registra el
objeto que estaba justo antes (``anterior_de``) y luego se usa
``insertar_despues``. Como los pergaminos NO se revierten (§2.11), un
pergamino vecino podría ya no estar cuando se deshaga el cambio; por eso se
guarda también un respaldo: el anterior más cercano que no es pergamino
(``anterior_no_pergamino``).

``buscar_por_tipo`` y ``contar_clase`` recorren la lista: el inventario está
acotado por ``inventario_max`` (10 en cripta-01) y esas consultas solo se
hacen al validar ABRIR / usar un pergamino, no en cada evento.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Iterator

from cripta.estructuras.lista_doble import ListaDoble
from cripta.estructuras.ordenamiento import ordenar
from cripta.estructuras.tabla_ordenada import TablaOrdenada

if TYPE_CHECKING:
    from cripta.estructuras.lista_doble import NodoDoble
    from cripta.modelo.objetos import ClaseObjeto, InstanciaObjeto


class Inventario:
    """Orden real + cursor + índice por id."""

    def __init__(self, capacidad: int) -> None:
        """``capacidad`` = ``inventario_max`` de los datos de la cripta."""
        if capacidad < 0:
            raise ValueError(f"inventario_max no puede ser negativo ({capacidad})")
        self._capacidad = capacidad
        self._lista: ListaDoble[InstanciaObjeto] = ListaDoble()
        self._nodos: TablaOrdenada[str, NodoDoble[InstanciaObjeto]] = TablaOrdenada()
        self._cursor: NodoDoble[InstanciaObjeto] | None = None

    @property
    def capacidad(self) -> int:
        return self._capacidad

    def __len__(self) -> int:
        return len(self._lista)

    def esta_lleno(self) -> bool:
        return len(self._lista) >= self._capacidad

    def __iter__(self) -> Iterator[InstanciaObjeto]:
        """Recorre en el orden real (frente → final)."""
        return iter(self._lista)

    # --- operaciones del juego -------------------------------------------------

    def agregar(self, objeto: InstanciaObjeto) -> None:
        """Agrega al final del orden real. ValueError si está lleno."""
        if self.esta_lleno():
            raise ValueError("El inventario está lleno")
        self._registrar_nodo(objeto, self._lista.agregar_al_final(objeto))

    def quitar(self, instancia_id: str) -> InstanciaObjeto:
        """Quita por id en O(1). Si era el del cursor, el cursor se mueve a un vecino."""
        nodo = self._nodo(instancia_id)
        if self._cursor is nodo:
            vecino = self._lista.siguiente(nodo)
            if vecino is None:
                vecino = self._lista.anterior(nodo)
            self._cursor = vecino
        self._lista.quitar(nodo)
        self._nodos.eliminar(instancia_id)
        return nodo.valor

    def contiene(self, instancia_id: str | None) -> bool:
        return instancia_id is not None and self._nodos.contiene(instancia_id)

    def obtener(self, instancia_id: str | None) -> InstanciaObjeto | None:
        if instancia_id is None:
            return None
        nodo = self._nodos.obtener(instancia_id)
        return nodo.valor if nodo is not None else None

    def mover_al_frente(self, instancia_id: str) -> None:
        """O(1). Lo usa ``equipar`` (§2.7)."""
        self._lista.mover_al_frente(self._nodo(instancia_id))

    def buscar_por_tipo(self, tipo_id: str) -> InstanciaObjeto | None:
        """Primer objeto de ese tipo (p. ej. para saber si hay cierta llave)."""
        for objeto in self._lista:
            if objeto.tipo_id == tipo_id:
                return objeto
        return None

    def contar_clase(self, clase: ClaseObjeto) -> int:
        """Cuántos objetos de esa clase hay (p. ej. pergaminos disponibles)."""
        cantidad = 0
        for objeto in self._lista:
            if objeto.clase is clase:
                cantidad += 1
        return cantidad

    def primero_de_clase(self, clase: ClaseObjeto) -> InstanciaObjeto | None:
        """Primer objeto (en el orden real) de esa clase."""
        for objeto in self._lista:
            if objeto.clase is clase:
                return objeto
        return None

    def objeto_en_posicion(self, posicion: int) -> InstanciaObjeto | None:
        """Objeto en la posición ``posicion`` (desde 0) del orden real. Para la vista."""
        if posicion < 0:
            return None
        indice = 0
        for objeto in self._lista:
            if indice == posicion:
                return objeto
            indice += 1
        return None

    # --- cursor (lo usa la vista) ------------------------------------------------

    def actual(self) -> InstanciaObjeto | None:
        """Objeto que se está viendo."""
        if self._cursor is None:
            return None
        return self._cursor.valor

    def avanzar(self) -> InstanciaObjeto | None:
        if self._cursor is None:
            return None
        siguiente = self._lista.siguiente(self._cursor)
        self._cursor = siguiente if siguiente is not None else self._lista.primero
        return self.actual()

    def retroceder(self) -> InstanciaObjeto | None:
        if self._cursor is None:
            return None
        anterior = self._lista.anterior(self._cursor)
        self._cursor = anterior if anterior is not None else self._lista.ultimo
        return self.actual()

    def ir_a(self, instancia_id: str) -> None:
        self._cursor = self._nodo(instancia_id)

    # --- vistas ------------------------------------------------------------------

    def vista_ordenada(
        self,
        clave: Callable[[InstanciaObjeto], Any],
        descendente: bool = False,
    ) -> list[InstanciaObjeto]:
        """Lista NUEVA ordenada con ``ordenamiento.ordenar``; el orden real no cambia.

        La ``clave`` la arma quien llama (necesita las fichas para peso / valor /
        nombre): ver ``Juego.vista_inventario``.
        """
        return ordenar(self._lista.a_lista(), clave=clave, descendente=descendente)

    # --- soporte para el retroceso -------------------------------------------------

    def anterior_de(self, instancia_id: str) -> str | None:
        """Id del objeto inmediatamente anterior en el orden real (None si es el primero)."""
        anterior = self._lista.anterior(self._nodo(instancia_id))
        return anterior.valor.id if anterior is not None else None

    def anterior_no_pergamino(self, instancia_id: str) -> str | None:
        """Id del objeto anterior más cercano que NO sea un pergamino (None = ninguno)."""
        anterior = self._lista.anterior(self._nodo(instancia_id))
        while anterior is not None and anterior.valor.es_pergamino():
            anterior = self._lista.anterior(anterior)
        return anterior.valor.id if anterior is not None else None

    def insertar_despues(
        self, anterior_id: str | None, objeto: InstanciaObjeto, respaldo_id: str | None = None
    ) -> None:
        """Reinserta ``objeto`` justo después de ``anterior_id`` (None = al frente).

        Si ``anterior_id`` ya no está (era un pergamino que se consumió), se usa
        ``respaldo_id``. No revisa la capacidad: el retroceso puede devolver un
        objeto aunque en el intervalo se haya llenado el inventario con un
        pergamino (§2.11).
        """
        nodo = self._lista.insertar_despues(self._referencia(anterior_id, respaldo_id), objeto)
        self._registrar_nodo(objeto, nodo)

    def reubicar_despues(self, instancia_id: str, anterior_id: str | None, respaldo_id: str | None = None) -> None:
        """Mueve un objeto que ya está en el inventario justo después de ``anterior_id``.

        Inverso de ``mover_al_frente`` para el retroceso.
        """
        self._lista.mover_despues(self._nodo(instancia_id), self._referencia(anterior_id, respaldo_id))

    # --- internos --------------------------------------------------------------------

    def _referencia(self, anterior_id: str | None, respaldo_id: str | None) -> NodoDoble[InstanciaObjeto] | None:
        """Nodo después del cual reinsertar (None = al frente)."""
        if anterior_id is None:
            return None
        referencia = self._nodos.obtener(anterior_id)
        if referencia is None and respaldo_id is not None:
            referencia = self._nodos.obtener(respaldo_id)
        return referencia

    def _nodo(self, instancia_id: str) -> NodoDoble[InstanciaObjeto]:
        nodo = self._nodos.obtener(instancia_id)
        if nodo is None:
            raise KeyError(f"El objeto {instancia_id!r} no está en el inventario")
        return nodo

    def _registrar_nodo(self, objeto: InstanciaObjeto, nodo: NodoDoble[InstanciaObjeto]) -> None:
        if self._nodos.contiene(objeto.id):
            self._lista.quitar(nodo)
            raise ValueError(f"El objeto {objeto.id!r} ya está en el inventario")
        self._nodos.insertar(objeto.id, nodo)
        if self._cursor is None:
            self._cursor = nodo
