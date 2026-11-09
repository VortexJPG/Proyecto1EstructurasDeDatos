"""Instancias de objetos y trampas.                                   [Persona A]

La ficha (catálogo) es compartida; la instancia es la que está en el suelo o
en el inventario (§2.7). El contenido del servicio trae los objetos solo como
ids de TIPO, así que el modelo genera los ids de instancia. Deben ser
DETERMINISTAS (mismo id en cada ejecución y en el replay) y no depender del
orden de llegada de las respuestas HTTP.

Formatos de id elegidos (no pueden chocar entre sí):
- Objeto del contenido de una sala:  "o-<sala>-<posición>"   p. ej. "o-2-0"
- Objeto que suelta un enemigo:      "s<serie>-<enemigo>"    p. ej. "s3-e-201"
  ``serie`` es un contador del Juego que NUNCA se revierte: si un retroceso
  revive a un enemigo y vuelve a morir, sus objetos reciben ids nuevos. Sin
  eso, un pergamino que sobrevive al retroceso (§2.11) podría quedar con el
  mismo id que el que se genera en la segunda muerte.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from cripta.constantes import TRAMPA_REARME_POR_DEFECTO

if TYPE_CHECKING:
    from cripta.modelo.datos import Ficha
    from cripta.modelo.eventos import Evento


class ClaseObjeto(Enum):
    ARMA = "arma"
    ARMADURA = "armadura"
    POCION = "pocion"
    ANTIDOTO = "antidoto"
    LLAVE = "llave"
    ANTORCHA = "antorcha"
    PERGAMINO = "pergamino_retroceso"

    @staticmethod
    def desde_texto(texto: str) -> ClaseObjeto:
        """Convierte el campo ``clase`` de la ficha. ValueError si no es de objeto."""
        for clase in ClaseObjeto:
            if clase.value == texto:
                return clase
        raise ValueError(f"Clase de objeto desconocida: {texto!r}")


class InstanciaObjeto:
    """Un objeto concreto. Sus datos (peso, valor, bonos) están en la ficha."""

    __slots__ = ("id", "tipo_id", "clase")

    id: str
    tipo_id: str
    clase: ClaseObjeto

    def __init__(self, id: str, tipo_id: str, clase: ClaseObjeto) -> None:
        self.id = id
        self.tipo_id = tipo_id
        self.clase = clase

    def es_pergamino(self) -> bool:
        """Los pergaminos quedan FUERA del estado reversible (§2.11)."""
        return self.clase is ClaseObjeto.PERGAMINO

    def __repr__(self) -> str:
        return f"InstanciaObjeto({self.id!r}, {self.tipo_id!r})"


class InstanciaTrampa:
    """Trampa colocada en una sala (§2.10).

    Copia de la ficha lo que necesita la simulación (daño, rearme) para no
    consultar la caché cada vez que se activa.
    """

    id: str
    tipo_id: str
    nombre: str
    dano: int
    rearme: int  # intervalo de rearme (ficha o 300 por defecto)
    veneno: int  # opcional: daño por pulso de veneno (0 = no envenena)
    armada: bool
    evento_rearme: Evento | None

    def __init__(self, id: str, ficha: Ficha) -> None:
        self.id = id
        self.tipo_id = ficha.id
        self.nombre = ficha.nombre
        self.dano = ficha.dano if ficha.dano is not None else 0
        self.rearme = ficha.rearme if ficha.rearme is not None else TRAMPA_REARME_POR_DEFECTO
        self.veneno = ficha.veneno if ficha.veneno is not None else 0
        self.armada = True
        self.evento_rearme = None

    def __repr__(self) -> str:
        return f"InstanciaTrampa({self.id!r}, armada={self.armada})"


def id_objeto_de_sala(sala_id: int, posicion: int) -> str:
    """Id determinista para el objeto en ``posicion`` del contenido de una sala.

    Ejemplo: "o-2-0". No choca con otro id: (sala, posición) es único.
    """
    return f"o-{sala_id}-{posicion}"


def id_objeto_soltado(enemigo_id: str, serie: int) -> str:
    """Id determinista para un objeto que deja un enemigo al morir (campo ``suelta``).

    ``serie`` es el contador ``Juego.objetos_generados`` (nunca se repite).
    """
    return f"s{serie}-{enemigo_id}"
