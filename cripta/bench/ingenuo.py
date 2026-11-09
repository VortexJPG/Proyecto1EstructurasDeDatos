"""Oráculo ingenuo de resolubilidad: solo pruebas y --bench.      [Persona B]

Repite el recorrido desde cero cada vez que obtiene una llave. Su costo es
O(K·(R+E)) y **no se usa en el juego**: existe para comprobar que el
verificador incremental da el mismo veredicto y el mismo conjunto de llaves
obtenibles, y para medir la alternativa descartada.

Puede usar ``dict``/``set`` porque no forma parte de los problemas evaluados.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cripta.modelo.datos import DatosCripta, DatosSala, UbicacionLlave


def alcanzables(inicio, salas_por_id, obtenidas):
    vistos = {inicio}
    pendientes = [inicio]
    while pendientes:
        actual = pendientes.pop()
        for salida in salas_por_id[actual].salidas:
            if salida.cerrada and salida.llave is not None and salida.llave not in obtenidas:
                continue
            if salida.sala_destino not in vistos:
                vistos.add(salida.sala_destino)
                pendientes.append(salida.sala_destino)
    return vistos


def verificar_ingenuo(
    datos: DatosCripta, salas: list[DatosSala], llaves: list[UbicacionLlave]
) -> tuple[bool, list[str]]:
    """Devuelve ``(resoluble, llaves_obtenibles_ordenadas)``."""
    salas_por_id = {sala.id: sala for sala in salas}
    ubicaciones = {}
    for ubicacion in llaves:
        ubicaciones.setdefault(ubicacion.id, []).append(ubicacion.sala)
    obtenidas = set()
    while True:
        region = alcanzables(datos.sala_inicial, salas_por_id, obtenidas)
        nuevas = [
            llave_id
            for llave_id, sitios in ubicaciones.items()
            if llave_id not in obtenidas and any(sitio in region for sitio in sitios)
        ]
        if not nuevas:
            break
        for llave_id in sorted(nuevas):
            obtenidas.add(llave_id)
    region = alcanzables(datos.sala_inicial, salas_por_id, obtenidas)
    salida_con_llave = any(
        sala.id in region
        and salida.sala_destino == datos.sala_salida
        and salida.llave == datos.llave_salida
        for sala in salas
        for salida in sala.salidas
    )
    resoluble = datos.llave_salida in obtenidas and salida_con_llave
    return resoluble, sorted(obtenidas)
