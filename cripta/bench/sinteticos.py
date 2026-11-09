"""Fichas en memoria para --bench y pruebas sin red.                  [Persona B]

Las criptas sintéticas del bench las arma ``bench_modelo._cripta_cuadricula``.
"""

from __future__ import annotations

from cripta.estructuras.tabla_ordenada import TablaOrdenada
from cripta.modelo.datos import Ficha
from cripta.modelo.puertos import FichaNoDisponible, ProveedorFichas


class FichasEnMemoria(ProveedorFichas):
    """``ProveedorFichas`` sin caché ni disco: todas las fichas en una ``TablaOrdenada``."""

    def __init__(self, fichas: list[Ficha]) -> None:
        self._tabla: TablaOrdenada[str, Ficha] = TablaOrdenada()
        for f in fichas:
            self._tabla.insertar(f.id, f)

    def obtener(self, tipo_id: str) -> Ficha:
        valor = self._tabla.obtener(tipo_id)
        if valor is None:
            raise FichaNoDisponible(tipo_id)
        return valor

    def fijar(self, tipo_id: str) -> None:
        return None

    def liberar(self, tipo_id: str) -> None:
        return None
