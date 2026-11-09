"""Resolución y caché de fichas del catálogo.                         [Persona B]

Implementa ``ProveedorFichas`` (el puerto que usa el modelo).

§4.3: los ids se descubren en desorden y se repiten; se acumulan los que
faltan (ConjuntoOrdenado para no repetir + ColaEnlazada para el orden) y se piden
en lotes de hasta 10 con ``GET /catalogo?ids=...``. Un id que ya está en
memoria o en disco nunca se vuelve a pedir.

§4.4: orden de búsqueda memoria → disco → red. La memoria es una
``CacheAcotada`` (LRU con fijado). Una ficha liberada de memoria sigue en
disco: recuperarla cuesta una lectura de archivo, no una solicitud.
"""

from __future__ import annotations

from typing import Iterable

from cripta.adaptadores.almacen_disco import AlmacenCatalogo
from cripta.adaptadores.fuente_datos import FuenteDatos
from cripta.estructuras.cola import ColaEnlazada
from cripta.estructuras.tabla_ordenada import ConjuntoOrdenado
from cripta.modelo.datos import Ficha
from cripta.modelo.puertos import FichaNoDisponible, ProveedorFichas
from cripta.estructuras.lru import CacheAcotada
from cripta.estructuras.ordenamiento import ordenar


class EstadisticasCache:
    def __init__(self) -> None:
        self.aciertos_memoria = 0
        self.aciertos_disco = 0
        self.fallos_red = 0
        self.desalojos = 0


class CacheCatalogo(ProveedorFichas):
    def __init__(self, fuente: FuenteDatos, almacen: AlmacenCatalogo, capacidad: int) -> None:
        self.fuente = fuente
        self.almacen = almacen
        self._capacidad = capacidad if capacidad > 0 else 1
        self.cache: CacheAcotada[str, Ficha] = CacheAcotada(self._capacidad)
        # ConjuntoOrdenado (no ``set``, §7): ids ya encolados, para no pedir dos veces.
        self.pendientes: ConjuntoOrdenado[str] = ConjuntoOrdenado()
        self._pendientes_orden: ColaEnlazada[str] = ColaEnlazada()
        self._estadisticas = EstadisticasCache()

    def validar_version(self, version_catalogo: str) -> None:
        vigente = self.almacen.validar_version(version_catalogo)
        if not vigente:
            # invalidar memoria
            self.cache = CacheAcotada(self._capacidad)
            self.pendientes = ConjuntoOrdenado()
            self._pendientes_orden = ColaEnlazada()

    def registrar_necesarios(self, tipo_ids: Iterable[str]) -> None:
        for tipo_id in tipo_ids:
            if self.cache.contiene(tipo_id):
                continue
            if self.almacen.contiene(tipo_id):
                continue
            if self.pendientes.agregar(tipo_id):
                self._pendientes_orden.encolar(tipo_id)

    def resolver_pendientes(self) -> None:
        if len(self.pendientes) == 0:
            return
        pendientes = list(self.pendientes)
        self.pendientes = ConjuntoOrdenado()
        self._pendientes_orden = ColaEnlazada()
        # orden determinista para lotes
        pendientes = ordenar(pendientes)
        tamaño_lote = 10
        for inicio in range(0, len(pendientes), tamaño_lote):
            lote = pendientes[inicio:inicio + tamaño_lote]
            fichas = self.fuente.catalogo(lote)
            for ficha in fichas:
                self.almacen.escribir(ficha)
                self.cache.insertar(ficha.id, ficha)
                self._estadisticas.fallos_red += 1
        # los que no volvieron, re-encolar? asumimos que todos volvieron
        # stats desalojos
        self._estadisticas.desalojos = self.cache.desalojos

    def estadisticas(self) -> EstadisticasCache:
        return self._estadisticas

    def obtener(self, tipo_id: str) -> Ficha:
        if self.cache.contiene(tipo_id):
            ficha = self.cache.obtener(tipo_id)
            if ficha is not None:
                self._estadisticas.aciertos_memoria += 1
                return ficha
        ficha = self.almacen.leer(tipo_id)
        if ficha is not None:
            self.cache.insertar(ficha.id, ficha)
            self._estadisticas.aciertos_disco += 1
            return ficha
        raise FichaNoDisponible(f"no resuelta: {tipo_id}")

    def fijar(self, tipo_id: str) -> None:
        if not self.cache.contiene(tipo_id):
            ficha = self.almacen.leer(tipo_id)
            if ficha is None:
                raise FichaNoDisponible(tipo_id)
            # Insertar y fijar juntos: si no, con la caché llena de fichas
            # fijadas, la inserción desalojaría la ficha recién leída.
            self.cache.insertar_fijada(ficha.id, ficha)
            self._estadisticas.aciertos_disco += 1
            return
        self.cache.fijar(tipo_id)

    def liberar(self, tipo_id: str) -> None:
        self.cache.liberar(tipo_id)
