"""Modelo del juego (MVC, §6).                                      [Persona A]

Regla de oro: nada en este paquete importa ``requests``, ``json``, ``os``,
usa ``open()`` ni conoce la vista. Lo externo llega por las interfaces de
``puertos.py`` o como DTOs de ``datos.py``. Así --offline, --replay y --bench
funcionan sin tocar el modelo.

Archivos de CONTRATO compartido (los usan A y B; cualquier cambio se avisa):
    datos.py      DTOs que vienen del servicio.
    acciones.py   Acciones del jugador (lo que se escribe en el replay).
    puertos.py    Interfaces que el modelo necesita (ProveedorFichas).
    guardable.py  Representación neutra del estado para guardar / cargar.
"""
