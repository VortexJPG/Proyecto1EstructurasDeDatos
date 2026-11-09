"""Interfaces que el modelo necesita del exterior.     [CONTRATO A↔B]

El modelo depende de estas abstracciones, nunca de HTTP ni de archivos (§6).
- Persona B las implementa (``adaptadores.cache_catalogo.CacheCatalogo``).
- Persona A las usa desde el modelo.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from cripta.modelo.datos import Ficha


class FichaNoDisponible(Exception):
    """La ficha no estaba resuelta cuando el modelo la pidió (bug de orquestación)."""


class ProveedorFichas(ABC):
    """Acceso a las fichas del catálogo desde el modelo."""

    @abstractmethod
    def obtener(self, tipo_id: str) -> Ficha:
        """Devuelve la ficha de ``tipo_id`` desde memoria o disco.

        Nunca hace solicitudes de red: el controlador garantiza que toda ficha
        referenciada por una sala quede resuelta ANTES de incorporarla al
        modelo. Si aun así no está, lanza ``FichaNoDisponible``.
        """

    @abstractmethod
    def fijar(self, tipo_id: str) -> None:
        """Una instancia en uso empieza a referenciar esta ficha (§4.4).

        En uso = enemigo vivo, objeto en el inventario o en el suelo de la sala
        actual, trampa de la sala actual. Mientras tenga referencias, la ficha
        no puede desalojarse. Persona A decide en qué puntos del modelo llamar
        a ``fijar`` / ``liberar`` (entrar / salir de sala, recoger, soltar,
        morir...) y debe mantenerlo coherente también al hacer retroceso.
        """

    @abstractmethod
    def liberar(self, tipo_id: str) -> None:
        """Una instancia deja de referenciar esta ficha."""
