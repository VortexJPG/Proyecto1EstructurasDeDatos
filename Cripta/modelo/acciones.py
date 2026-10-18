"""Acciones del jugador.                                [CONTRATO A↔B]"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TipoAccion(Enum):
    MOVER = "mover"
    ABRIR = "abrir"
    ATACAR = "atacar"
    ESPERAR = "esperar"
    RECOGER = "recoger"
    SOLTAR = "soltar"
    USAR = "usar"
    EQUIPAR = "equipar"
    RETROCEDER = "retroceder"


@dataclass(slots=True)
class Accion:
    tipo: TipoAccion
    direccion: str | None = None
    objetivo: str | None = None

    def a_linea(self) -> str:
        if self.tipo in (TipoAccion.MOVER, TipoAccion.ABRIR):
            if self.direccion is None:
                raise ValueError("acción sin dirección")
            return f"{self.tipo.value} {self.direccion}"
        if self.tipo is TipoAccion.ESPERAR:
            return TipoAccion.ESPERAR.value
        if self.tipo is TipoAccion.RETROCEDER:
            return TipoAccion.RETROCEDER.value
        if self.objetivo is None:
            raise ValueError(f"acción {self.tipo.value} sin objetivo")
        return f"{self.tipo.value} {self.objetivo}"

    @staticmethod
    def desde_linea(linea: str) -> "Accion":
        texto = linea.strip()
        if not texto:
            raise ValueError("línea vacía")
        partes = texto.split(" ", 1)
        nombre = partes[0]
        try:
            tipo = TipoAccion(nombre)
        except ValueError as exc:
            raise ValueError(f"tipo de acción desconocido: {nombre!r}") from exc
        if tipo in (TipoAccion.MOVER, TipoAccion.ABRIR):
            if len(partes) != 2:
                raise ValueError(f"falta dirección en {texto!r}")
            return Accion(tipo=tipo, direccion=partes[1].strip())
        if tipo in (TipoAccion.ESPERAR, TipoAccion.RETROCEDER):
            return Accion(tipo=tipo)
        if len(partes) != 2:
            raise ValueError(f"falta objetivo en {texto!r}")
        return Accion(tipo=tipo, objetivo=partes[1].strip())


@dataclass(slots=True)
class ResultadoAccion:
    aceptada: bool
    motivo: str = ""
    requiere_sala: int | None = None
