"""Precarga de contenido de salas por lotes.                           [Persona B]

§4.2: el jugador nunca queda en una sala cuyo contenido no se conoce, y la
estrategia normal evita esperar ~400 ms en cada puerta.

- Después de cada decisión: BFS (ColaEnlazada) desde la sala actual sobre el
  esqueleto; se toman hasta 10 salas no pedidas, de la más cercana a la más
  lejana, y se piden en UNA solicitud en un hilo de trabajo.
- Si al moverse falta una sala, se pide YA junto con sus vecinas no pedidas
  (cuesta lo mismo 1 sala que 10, §3.4).
- Una sala pedida (o guardada en disco) no se vuelve a pedir (ConjuntoOrdenado).
- La precarga anticipada deja las últimas ``RESERVA_SOLICITUDES`` del
  presupuesto para lo obligatorio.
- Determinismo (§2.4): las respuestas se incorporan en el orden en que se
  pidieron y solo entre decisiones del jugador. Incorporar contenido no usa el
  azar ni números de secuencia, así que el momento exacto no cambia la partida.
- Antes de incorporar una sala se resuelven sus fichas y las de lo que sueltan
  sus enemigos al morir.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable

from cripta.adaptadores.almacen_disco import AlmacenCripta
from cripta.adaptadores.cache_catalogo import CacheCatalogo
from cripta.adaptadores.fuente_datos import ErrorFuenteDatos, FuenteDatos
from cripta.constantes import MAX_SALAS_POR_CONSULTA
from cripta.estructuras.cola import ColaEnlazada
from cripta.estructuras.tabla_ordenada import ConjuntoOrdenado
from cripta.modelo.datos import ContenidoSala
from cripta.modelo.puertos import FichaNoDisponible


# La precarga ANTICIPADA nunca usa las últimas solicitudes del presupuesto (§5.1):
# quedan para lo obligatorio, es decir, el contenido de la sala a la que el
# jugador de verdad se mueve (``asegurar``) y las fichas que traiga.
RESERVA_SOLICITUDES = 2


@dataclass(slots=True)
class SolicitudPendiente:
    salas: list[int]
    futuro: object


class PlanificadorPrecarga:
    def __init__(
        self,
        fuente: FuenteDatos,
        cripta_id: str,
        almacen: AlmacenCripta,
        catalogo: CacheCatalogo,
        vecinos: Callable[[int], list[int]],
        incorporar: Callable[[ContenidoSala], None],
    ) -> None:
        self.fuente = fuente
        self.cripta_id = cripta_id
        self.almacen = almacen
        self.catalogo = catalogo
        self.vecinos = vecinos
        self.incorporar = incorporar
        self._solicitadas: ConjuntoOrdenado[int] = ConjuntoOrdenado()
        self._incorporados: ConjuntoOrdenado[int] = ConjuntoOrdenado()
        self._pendientes: list[SolicitudPendiente] = []
        self._executor = ThreadPoolExecutor(max_workers=1)
        # True cuando el BFS ya no encontró nada por pedir: desde ahí planificar
        # no recorre el mapa en cada decisión (medido con --bench: sin esto, el
        # costo de cada decisión crecía con el tamaño de la cripta).
        self._todo_pedido = False

    def _incorporar_contenido(self, contenidos: list[ContenidoSala]) -> None:
        ids: list[str] = []
        for c in contenidos:
            ids.extend(c.tipos_referenciados())
        self.catalogo.registrar_necesarios(ids)
        self.catalogo.resolver_pendientes()
        # Lo que sueltan los enemigos al morir también debe estar resuelto: el
        # modelo crea esos objetos (y pide sus fichas) en medio de la simulación.
        sueltas: list[str] = []
        for c in contenidos:
            for enemigo in c.enemigos:
                try:
                    sueltas.extend(self.catalogo.obtener(enemigo.tipo).suelta)
                except FichaNoDisponible:
                    pass
        if sueltas:
            self.catalogo.registrar_necesarios(sueltas)
            self.catalogo.resolver_pendientes()
        for c in contenidos:
            self.incorporar(c)
            self._incorporados.agregar(c.sala)
            self._solicitadas.agregar(c.sala)

    def reiniciar(self, salas_con_contenido: list[int]) -> None:
        """Tras cargar una partida: solo esas salas tienen contenido en el modelo.

        Las demás se volverán a traer (de disco si ya se guardaron, o de la red).
        """
        self._incorporados = ConjuntoOrdenado()
        self._solicitadas = ConjuntoOrdenado()
        self._todo_pedido = False
        for sala in salas_con_contenido:
            self._incorporados.agregar(sala)
            self._solicitadas.agregar(sala)

    def planificar(self, sala_actual: int) -> None:
        if self._todo_pedido:
            return
        seleccionadas = self._seleccionar_lote(sala_actual)
        if not seleccionadas:
            self._todo_pedido = True
            return
        de_disco = []
        de_red = []
        for sala in seleccionadas:
            if sala in self._solicitadas or sala in self._incorporados:
                continue
            if self.almacen.tiene_contenido(sala):
                de_disco.append(sala)
            else:
                de_red.append(sala)
        if de_disco:
            for sala in de_disco:
                c = self.almacen.cargar_contenido(sala)
                if c is not None:
                    self._incorporar_contenido([c])
        remaining = self.fuente.solicitudes_restantes()
        if de_red:
            if remaining is not None and remaining <= RESERVA_SOLICITUDES:
                # Lo que queda del presupuesto es la reserva para lo obligatorio
                # (asegurar). El presupuesto no vuelve a crecer, así que tampoco
                # se sigue planificando.
                self._todo_pedido = True
                return
            lote = de_red[:MAX_SALAS_POR_CONSULTA]
            self._lanzar_solicitud(lote)
            for sala in lote:
                self._solicitadas.agregar(sala)

    def asegurar(self, sala_id: int) -> None:
        while sala_id not in self._incorporados:
            self.incorporar_disponibles()
            if sala_id in self._incorporados:
                break
            if self._pendientes:
                try:
                    self._pendientes[0].futuro.result()
                except Exception:
                    pass
                self.incorporar_disponibles()
                if sala_id in self._incorporados:
                    break
                continue
            # no hay pendientes: resolver desde disco o red
            if self.almacen.tiene_contenido(sala_id):
                c = self.almacen.cargar_contenido(sala_id)
                if c is not None:
                    self._incorporar_contenido([c])
                    continue
            remaining = self.fuente.solicitudes_restantes()
            if remaining is not None and remaining <= 0:
                # no se puede asegurar por red; esperar no ayuda
                break
            # La consulta cuesta lo mismo con 1 sala que con 10 (§3.4): se pide la
            # sala que hace falta junto con sus vecinas más cercanas aún no pedidas.
            lote = self._lote_alrededor(sala_id)
            self._lanzar_solicitud(lote)
            for sala in lote:
                self._solicitadas.agregar(sala)
            try:
                self._pendientes[-1].futuro.result()
            except ErrorFuenteDatos:
                # Se informa una sola vez (reintentar en bucle gastaría el presupuesto).
                self.incorporar_disponibles()
                raise
            self.incorporar_disponibles()
            if sala_id not in self._incorporados:
                raise ErrorFuenteDatos("contenido", f"el servicio no devolvió el contenido de la sala {sala_id}")

    def incorporar_disponibles(self) -> int:
        incorporadas = 0
        while self._pendientes:
            pendiente = self._pendientes[0]
            if not getattr(pendiente.futuro, "done", lambda: True)():
                break
            try:
                resultado = pendiente.futuro.result()
            except Exception:
                # La solicitud falló: esas salas se podrán volver a pedir.
                for sala in pendiente.salas:
                    if sala not in self._incorporados:
                        self._solicitadas.eliminar(sala)
                        self._todo_pedido = False
                self._pendientes.pop(0)
                continue
            if isinstance(resultado, list):
                contenidos = [x for x in resultado if isinstance(x, ContenidoSala)]
                if contenidos:
                    # Persistir lo que llegó por red: la próxima vez sale de disco (§4.4).
                    try:
                        self.almacen.guardar_contenido(contenidos)
                    except OSError:
                        pass
                    self._incorporar_contenido(contenidos)
                    incorporadas += len(contenidos)
            self._pendientes.pop(0)
        return incorporadas

    def cerrar(self) -> None:
        # incorporar lo que quede
        try:
            for p in list(self._pendientes):
                try:
                    p.futuro.result()
                except Exception:
                    pass
            self.incorporar_disponibles()
        finally:
            self._executor.shutdown(wait=True)

    def _seleccionar_lote(self, sala_actual: int) -> list[int]:
        cola: ColaEnlazada[int] = ColaEnlazada()
        cola.encolar(sala_actual)
        visitados: ConjuntoOrdenado[int] = ConjuntoOrdenado()
        visitados.agregar(sala_actual)
        seleccionados: list[int] = []
        while not cola.esta_vacia() and len(seleccionados) < 10:
            actual = cola.desencolar()
            for v in self.vecinos(actual) or []:
                if v in visitados:
                    continue
                visitados.agregar(v)
                if v not in self._solicitadas and v not in self._incorporados:
                    seleccionados.append(v)
                    if len(seleccionados) >= 10:
                        break
                cola.encolar(v)
            if len(seleccionados) >= 10:
                break
        return seleccionados

    def _lote_alrededor(self, sala_id: int) -> list[int]:
        """``sala_id`` más sus vecinas más cercanas (BFS) aún no pedidas ni en disco."""
        lote = [sala_id]
        for sala in self._seleccionar_lote(sala_id):
            if len(lote) >= MAX_SALAS_POR_CONSULTA:
                break
            if sala != sala_id and not self.almacen.tiene_contenido(sala):
                lote.append(sala)
        return lote

    def _lanzar_solicitud(self, salas: list[int]) -> None:
        future = self._executor.submit(self.fuente.contenido, self.cripta_id, salas)
        self._pendientes.append(SolicitudPendiente(salas=list(salas), futuro=future))
