"""Tabla de búsqueda por clave: arreglo ordenado + búsqueda binaria.     [Persona B]

§7 prohíbe usar ``dict`` como índice, caché o tabla de búsqueda. Esta tabla lo
reemplaza en TODO el programa: salas por id, enemigos por id, fichas de la
caché, nodos del inventario por id, salas ya pedidas, etc.

Decisión (Documento de Decisiones, §4.3): el proyecto usa solo estructuras
vistas en el curso (arreglos, listas enlazadas, pilas, colas y montículo). Por
eso la tabla son dos ARREGLOS paralelos ordenados por clave: ``_claves[i]`` va
con ``_valores[i]``. La alternativa descartada, recorrer una lista sin ordenar
(O(n)), se mide con ``--bench busqueda``.

- Buscar: búsqueda binaria sobre ``_claves``, O(log n). Se mira la clave del
  medio y se descarta la mitad donde no puede estar. Con 25 fichas son unas 5
  comparaciones; con 1000 salas, unas 10.
- Eliminar: BORRADO PEREZOSO, igual que en la agenda (§4.1). No se corre
  nada: la casilla se marca como borrada (``_BORRADO``) y la clave se queda
  donde estaba, así el arreglo sigue ordenado. O(log n).
- Insertar: si la clave ya estaba (viva o borrada), se reutiliza su casilla,
  O(log n). Pasa todo el tiempo en el inventario: soltar un objeto y volver a
  recogerlo usa el mismo id. Si la casilla donde iría la clave nueva está
  borrada, también se reutiliza. Si no, hay que correr los elementos que
  siguen, como en cualquier arreglo: O(n). Eso pasa poco (cuando llega el
  contenido de una sala, cuando entra una ficha nueva a la caché...); buscar
  es mucho más frecuente (§4.4).
- Cuando las casillas borradas pasan a ser más que las vivas, se compacta el
  arreglo una vez (O(n)), para que la basura no crezca sin control.
- Recorrer (``claves``, ``valores``, ``pares``) da las claves en orden
  creciente, siempre igual en cada ejecución. Eso ayuda al replay: no depende
  de ``hash()`` de Python, que cambia entre ejecuciones.

Todas las claves de una misma tabla deben ser del mismo tipo (todas ``int`` o
todas ``str``), porque hay que poder compararlas con ``<``.
"""

from __future__ import annotations

from typing import Any, Generic, Iterator, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class _Borrado:
    """Marca de una casilla borrada (no se confunde con ningún valor guardado, ni con None)."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "<borrado>"


_BORRADO: Any = _Borrado()

# No se compacta por poca basura: con menos de esto, correr el arreglo costaría más.
_MINIMO_PARA_COMPACTAR = 32


class TablaOrdenada(Generic[K, V]):
    """Mapa clave → valor sobre dos arreglos ordenados por clave."""

    __slots__ = ("_claves", "_valores", "_borrados")

    def __init__(self) -> None:
        self._claves: list[K] = []
        self._valores: list[Any] = []  # el valor, o _BORRADO si la casilla está borrada
        self._borrados = 0

    def insertar(self, clave: K, valor: V) -> None:
        """Agrega o reemplaza. O(log n) si reutiliza una casilla; O(n) si hay que correr."""
        claves = self._claves
        posicion = self._posicion(clave)
        if posicion < len(claves) and claves[posicion] == clave:  # ya estaba (viva o borrada)
            if self._valores[posicion] is _BORRADO:
                self._borrados -= 1
            self._valores[posicion] = valor  # misma casilla
            return
        # ``clave`` va entre la casilla ``posicion - 1`` (menor) y ``posicion``
        # (mayor). Si alguna de las dos está borrada, se escribe ahí: el orden se
        # mantiene y no hay que correr nada.
        for vecina in (posicion, posicion - 1):
            if 0 <= vecina < len(claves) and self._valores[vecina] is _BORRADO:
                claves[vecina] = clave
                self._valores[vecina] = valor
                self._borrados -= 1
                return
        claves.insert(posicion, clave)  # el arreglo corre una casilla los que siguen
        self._valores.insert(posicion, valor)

    def obtener(self, clave: Any, defecto: V | None = None) -> V | None:
        """Valor de ``clave`` (o ``defecto`` si no está). O(log n)."""
        posicion = self._buscar(clave)
        return self._valores[posicion] if posicion >= 0 else defecto

    def contiene(self, clave: Any) -> bool:
        return self._buscar(clave) >= 0

    def eliminar(self, clave: Any) -> bool:
        """Marca la clave como borrada (no corre nada). Devuelve False si no estaba. O(log n)."""
        posicion = self._buscar(clave)
        if posicion < 0:
            return False
        self._valores[posicion] = _BORRADO
        self._borrados += 1
        if self._borrados > _MINIMO_PARA_COMPACTAR and self._borrados > len(self._claves) - self._borrados:
            self._compactar()
        return True

    def claves(self) -> Iterator[K]:
        """Claves en orden creciente (sobre una copia: se puede modificar la tabla mientras tanto)."""
        return iter([clave for clave, _ in self.pares()])

    def valores(self) -> Iterator[V]:
        """Valores en el orden de sus claves."""
        return iter([valor for _, valor in self.pares()])

    def pares(self) -> Iterator[tuple[K, V]]:
        """Pares (clave, valor) en orden creciente de clave, sin las casillas borradas."""
        claves = list(self._claves)
        valores = list(self._valores)
        for i in range(len(claves)):
            if valores[i] is not _BORRADO:
                yield claves[i], valores[i]

    def __len__(self) -> int:
        return len(self._claves) - self._borrados

    def __contains__(self, clave: object) -> bool:
        return self._buscar(clave) >= 0

    # --- búsqueda binaria -------------------------------------------------------------

    def _posicion(self, clave: Any) -> int:
        """Primera posición cuya clave es >= ``clave`` (donde está o donde iría)."""
        claves = self._claves
        bajo = 0
        alto = len(claves)
        while bajo < alto:
            medio = (bajo + alto) // 2
            if claves[medio] < clave:
                bajo = medio + 1  # está en la mitad derecha
            else:
                alto = medio  # está en la mitad izquierda (o es el medio)
        return bajo

    def _buscar(self, clave: Any) -> int:
        """Posición de ``clave`` si está viva, o -1."""
        try:
            posicion = self._posicion(clave)
        except TypeError:
            return -1  # clave de otro tipo (por ejemplo None): no puede estar en la tabla
        if (posicion < len(self._claves) and self._claves[posicion] == clave
                and self._valores[posicion] is not _BORRADO):
            return posicion
        return -1

    def _compactar(self) -> None:
        """Rehace los arreglos solo con las casillas vivas (siguen ordenadas). O(n)."""
        claves: list[K] = []
        valores: list[Any] = []
        for i in range(len(self._claves)):
            if self._valores[i] is not _BORRADO:
                claves.append(self._claves[i])
                valores.append(self._valores[i])
        self._claves = claves
        self._valores = valores
        self._borrados = 0


class ConjuntoOrdenado(Generic[K]):
    """Conjunto de claves (sin valores) sobre una ``TablaOrdenada``."""

    __slots__ = ("_tabla",)

    def __init__(self) -> None:
        self._tabla: TablaOrdenada[K, None] = TablaOrdenada()

    def agregar(self, clave: K) -> bool:
        """Agrega la clave. Devuelve False si ya estaba."""
        if self._tabla.contiene(clave):
            return False
        self._tabla.insertar(clave, None)
        return True

    def contiene(self, clave: Any) -> bool:
        return self._tabla.contiene(clave)

    def eliminar(self, clave: Any) -> bool:
        return self._tabla.eliminar(clave)

    def __len__(self) -> int:
        return len(self._tabla)

    def __contains__(self, clave: object) -> bool:
        return self._tabla.contiene(clave)

    def __iter__(self) -> Iterator[K]:
        """Claves en orden creciente."""
        return self._tabla.claves()
