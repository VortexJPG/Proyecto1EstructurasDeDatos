from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from cripta.modelo.datos import ContenidoSala, DatosCripta, Ficha, PaginaEsqueleto, ResumenCripta


class ErrorFuenteDatos(Exception):
    def __init__(self, operacion: str, detalle: str, codigo_http: int | None = None) -> None:
        super().__init__(f"{operacion}: {detalle}" + (f" (HTTP {codigo_http})" if codigo_http is not None else ""))
        self.operacion = operacion
        self.detalle = detalle
        self.codigo_http = codigo_http


class PresupuestoAgotado(ErrorFuenteDatos):
    pass


@dataclass(slots=True)
class EstadisticasRed:
    solicitudes_realizadas: int = 0
    presupuesto: int | None = None
    respuestas_429: int = 0
    errores: int = 0


class FuenteDatos(ABC):
    @abstractmethod
    def listar_criptas(self) -> list[ResumenCripta]: ...
    @abstractmethod
    def datos_cripta(self, cripta_id: str) -> DatosCripta: ...
    @abstractmethod
    def pagina_esqueleto(self, cripta_id: str, pagina: int) -> PaginaEsqueleto: ...
    @abstractmethod
    def contenido(self, cripta_id: str, salas: list[int]) -> list[ContenidoSala]: ...
    @abstractmethod
    def catalogo(self, ids: list[str]) -> list[Ficha]: ...
    @abstractmethod
    def version_cripta(self, cripta_id: str) -> str: ...
    @abstractmethod
    def version_catalogo(self) -> str: ...
    @abstractmethod
    def establecer_presupuesto(self, presupuesto: int) -> None: ...
    @abstractmethod
    def solicitudes_restantes(self) -> int | None: ...
    @abstractmethod
    def estadisticas(self) -> EstadisticasRed: ...
