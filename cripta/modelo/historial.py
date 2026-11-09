"""Historial reversible para los pergaminos de retroceso.            [Persona A]

§2.11 y §4.6. PROHIBIDO guardar copias completas del estado. Se registra solo
lo necesario para INVERTIR cada cambio (patrón "bitácora de deshacer").

Un ``IntervaloReversible`` cubre desde justo antes de una acción del jugador
hasta su siguiente decisión: la acción, las acciones enemigas, los efectos, el
reloj, los eventos programados / extraídos / cancelados, rastro, vidas,
inventario, suelo, puertas, trampas... Revertir = deshacer sus cambios en
orden INVERSO. Cada cambio guarda solo el valor anterior (o el nodo y su
vecino), así que registrar y revertir cuestan O(1) por cambio.

Exclusiones obligatorias:
- La cantidad de pergaminos no se registra ni se restaura (en ninguno de los
  dos sentidos: ni el usado, ni los recogidos / soltados en el intervalo).
  ``Juego`` simplemente no registra los cambios de suelo / inventario de un
  pergamino.
- La caché de catálogo es infraestructura, no juego: no se revierte. Las
  referencias que el modelo tiene fijadas (``fijar`` / ``liberar``) tampoco
  se registran: después de retroceder, ``Juego._reconciliar_fijaciones`` las
  recalcula a partir del estado restaurado.
- Los mensajes en pantalla y el cursor del inventario son de la interfaz.

Máximo 5 intervalos; al superar el límite se descarta el más antiguo
(``BufferCircular``). Dos pergaminos seguidos revierten dos intervalos.

Decisión: el estado del generador ``random.Random`` SÍ se restaura
(``CambioEstadoAzar``, tomado al abrir el intervalo). El retroceso devuelve
el juego "al punto inmediatamente anterior" (§2.11) y el generador es parte
de ese estado: repetir la misma acción da el mismo resultado.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from cripta.estructuras.buffer_circular import BufferCircular
from cripta.estructuras.lista_doble import ListaDoble

if TYPE_CHECKING:
    from cripta.estructuras.lista_doble import NodoDoble
    from cripta.modelo.acciones import Accion
    from cripta.modelo.eventos import Evento
    from cripta.modelo.juego import Juego
    from cripta.modelo.objetos import InstanciaObjeto


class Cambio(ABC):
    """Un cambio atómico que sabe deshacerse."""

    __slots__ = ()

    @abstractmethod
    def revertir(self, juego: Juego) -> None:
        """Deja el estado como estaba antes de este cambio."""


class CambioAtributo(Cambio):
    """Genérico: ``objeto.atributo`` valía ``valor_anterior``.

    Cubre la mayoría de los casos: vida, reloj, rastro, ``puerta.cerrada``,
    ``trampa.armada``, ``evento_turno``, ``sala`` de un actor, contadores...
    """

    __slots__ = ("objeto", "atributo", "valor_anterior")

    def __init__(self, objeto: object, atributo: str, valor_anterior: Any) -> None:
        self.objeto = objeto
        self.atributo = atributo
        self.valor_anterior = valor_anterior

    def revertir(self, juego: Juego) -> None:
        setattr(self.objeto, self.atributo, self.valor_anterior)


class CambioEventoProgramado(Cambio):
    """Se programó ``evento``; revertir lo anula (``Agenda.deshacer_programado``)."""

    __slots__ = ("evento",)

    def __init__(self, evento: Evento) -> None:
        self.evento = evento

    def revertir(self, juego: Juego) -> None:
        juego.agenda.deshacer_programado(self.evento)


class CambioEventoExtraido(Cambio):
    """Se ejecutó ``evento``; revertir lo devuelve a la agenda con su misma secuencia."""

    __slots__ = ("evento",)

    def __init__(self, evento: Evento) -> None:
        self.evento = evento

    def revertir(self, juego: Juego) -> None:
        juego.agenda.restaurar_extraido(self.evento)


class CambioEventoCancelado(Cambio):
    """Se canceló ``evento``; revertir lo vuelve a dejar pendiente.

    Con borrado perezoso, si el evento ya se había descartado del montículo,
    ``Agenda.descancelar`` lo reinserta.
    """

    __slots__ = ("evento",)

    def __init__(self, evento: Evento) -> None:
        self.evento = evento

    def revertir(self, juego: Juego) -> None:
        juego.agenda.descancelar(self.evento)


class CambioInventario(Cambio):
    """Un objeto entró, salió o se movió al frente del inventario.

    Para restaurar la posición se guarda el objeto que estaba justo antes
    (``anterior_id``) y, de respaldo, el anterior más cercano que NO sea un
    pergamino (``respaldo_id``): un pergamino vecino puede haberse consumido
    o soltado sin registrarse (§2.11) y ya no estar al revertir.
    """

    AGREGADO = "agregado"
    QUITADO = "quitado"
    FRENTE = "frente"

    __slots__ = ("objeto", "operacion", "anterior_id", "respaldo_id")

    def __init__(
        self, objeto: InstanciaObjeto, operacion: str, anterior_id: str | None, respaldo_id: str | None = None
    ) -> None:
        self.objeto = objeto
        self.operacion = operacion
        self.anterior_id = anterior_id
        self.respaldo_id = respaldo_id

    def revertir(self, juego: Juego) -> None:
        inventario = juego.jugador.inventario
        if self.operacion == CambioInventario.AGREGADO:
            if inventario.contiene(self.objeto.id):
                inventario.quitar(self.objeto.id)
        elif self.operacion == CambioInventario.QUITADO:
            inventario.insertar_despues(self.anterior_id, self.objeto, self.respaldo_id)
        else:
            inventario.reubicar_despues(self.objeto.id, self.anterior_id, self.respaldo_id)


class CambioNodoAgregado(Cambio):
    """Se enganchó ``nodo`` en ``lista`` (enemigo que llega a una sala, objeto al suelo).

    Revertir lo desengancha. Si el nodo ya no está enganchado es porque era un
    pergamino que el jugador recogió (cambio que no se registra, §2.11): en
    ese caso no se hace nada.
    """

    __slots__ = ("lista", "nodo")

    def __init__(self, lista: ListaDoble, nodo: NodoDoble) -> None:
        self.lista = lista
        self.nodo = nodo

    def revertir(self, juego: Juego) -> None:
        if self.lista.contiene_nodo(self.nodo):
            self.lista.quitar(self.nodo)


class CambioNodoQuitado(Cambio):
    """Se desenganchó ``nodo`` de ``lista``; estaba justo después de ``anterior``.

    Revertir vuelve a enganchar EL MISMO nodo en su lugar en O(1). Como todo se
    deshace en orden inverso, ``anterior`` vuelve a estar en la lista cuando
    llega el turno de este cambio. La única excepción es un pergamino del suelo
    que el jugador recogió (no se registra, §2.11): por eso se guarda también
    ``respaldo``, el anterior más cercano que no es pergamino.
    """

    __slots__ = ("lista", "nodo", "anterior", "respaldo")

    def __init__(
        self, lista: ListaDoble, nodo: NodoDoble, anterior: NodoDoble | None, respaldo: NodoDoble | None = None
    ) -> None:
        self.lista = lista
        self.nodo = nodo
        self.anterior = anterior
        self.respaldo = respaldo if respaldo is not None else anterior

    def revertir(self, juego: Juego) -> None:
        if ListaDoble.esta_enlazado(self.nodo):
            return
        referencia = self.anterior
        if referencia is not None and not self.lista.contiene_nodo(referencia):
            referencia = self.respaldo
            if referencia is not None and not self.lista.contiene_nodo(referencia):
                referencia = self.lista.ultimo  # no debería ocurrir; se conserva el elemento
        self.lista.reenlazar_despues(referencia, self.nodo)


class CambioEstadoAzar(Cambio):
    """Estado de ``juego.azar`` al abrir el intervalo."""

    __slots__ = ("estado",)

    def __init__(self, estado: tuple) -> None:
        self.estado = estado

    def revertir(self, juego: Juego) -> None:
        juego.azar.setstate(self.estado)


class IntervaloReversible:
    """Cambios entre una decisión del jugador y la siguiente."""

    __slots__ = ("accion", "_cambios")

    accion: Accion

    def __init__(self, accion: Accion) -> None:
        self.accion = accion
        # ``list`` usada como pila (almacenamiento contiguo, §7).
        self._cambios: list[Cambio] = []

    def registrar(self, cambio: Cambio) -> None:
        """Apila el cambio. O(1) amortizado."""
        self._cambios.append(cambio)

    def revertir(self, juego: Juego) -> None:
        """Deshace todos los cambios del más reciente al más antiguo."""
        cambios = self._cambios
        for i in range(len(cambios) - 1, -1, -1):
            cambios[i].revertir(juego)

    def __len__(self) -> int:
        return len(self._cambios)


class Historial:
    """Últimos 5 intervalos reversibles."""

    def __init__(self, maximo: int) -> None:
        """``maximo`` = constantes.MAX_ACCIONES_REVERSIBLES."""
        self._intervalos: BufferCircular[IntervaloReversible] = BufferCircular(maximo)
        self._abierto: IntervaloReversible | None = None
        # Se consulta en CADA mutación del juego: se guarda como atributo simple.
        self._grabando = False

    @property
    def grabando(self) -> bool:
        """True si hay un intervalo abierto y no se está revirtiendo."""
        return self._grabando

    def abrir_intervalo(self, accion: Accion) -> None:
        self._abierto = IntervaloReversible(accion)
        self._grabando = True

    def registrar(self, cambio: Cambio) -> None:
        """Agrega al intervalo abierto. Ignora si no se está grabando (p. ej. al revertir)."""
        if self._grabando:
            self._abierto.registrar(cambio)

    def cerrar_intervalo(self) -> None:
        """Guarda el intervalo; si ya hay 5, se descarta el más antiguo."""
        if self._abierto is not None:
            self._intervalos.agregar(self._abierto)
        self._abierto = None
        self._grabando = False

    def descartar_abierto(self, juego: Juego) -> None:
        """Revierte y descarta el intervalo abierto (si una acción falla a la mitad)."""
        intervalo = self._abierto
        self._abierto = None
        self._grabando = False
        if intervalo is not None:
            intervalo.revertir(juego)

    def puede_retroceder(self) -> bool:
        return not self._intervalos.esta_vacio()

    def retroceder(self, juego: Juego) -> bool:
        """Revierte el intervalo más reciente. False si no hay ninguno."""
        intervalo = self._intervalos.extraer_reciente()
        if intervalo is None:
            return False
        anterior = self._grabando
        self._grabando = False  # lo que pase al revertir no se registra
        try:
            intervalo.revertir(juego)
        finally:
            self._grabando = anterior
        return True

    def cambios_del_ultimo(self) -> int:
        """Cantidad de cambios del intervalo más reciente (para --bench)."""
        intervalo = self._intervalos.ver_reciente()
        return len(intervalo) if intervalo is not None else 0

    def __len__(self) -> int:
        return len(self._intervalos)
