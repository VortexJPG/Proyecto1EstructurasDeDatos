"""Comandos que la vista entrega al controlador.         [CONTRATO A↔B]

La vista (Persona A) traduce el texto del usuario a un ``ComandoUsuario``.
El controlador (Persona B) lo ejecuta. Los comandos de juego llevan una
``Accion`` (con ids de instancia reales); los demás son de la sesión y no
tocan el reloj virtual.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from cripta.modelo.acciones import Accion


class TipoComando(Enum):
    ACCION = "accion"  # cualquier acción de juego (incluye RETROCEDER)
    INVENTARIO_SIGUIENTE = "inventario_siguiente"
    INVENTARIO_ANTERIOR = "inventario_anterior"
    VER_INVENTARIO = "ver_inventario"
    VISTA_ORDENADA = "vista_ordenada"  # argumento: "peso" | "valor" | "nombre"
    GUARDAR = "guardar"  # argumento: ruta
    CARGAR = "cargar"  # argumento: ruta
    PUNTAJES = "puntajes"
    AYUDA = "ayuda"
    SALIR = "salir"


@dataclass(slots=True)
class ComandoUsuario:
    tipo: TipoComando
    accion: Accion | None = None
    argumento: str | None = None
