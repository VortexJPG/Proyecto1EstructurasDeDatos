"""Oráculo ingenuo de resolubilidad: solo pruebas y --bench.      [Persona B]

Repite el recorrido desde cero cada vez que obtiene una llave. Su costo es
O(K·(R+E)) y **no se usa en el juego**: existe para comprobar que el
verificador incremental da el mismo veredicto y el mismo conjunto de llaves
obtenibles, y para medir la alternativa descartada.

Revisión cruzada (Persona A, 2026-11-17): usa las MISMAS estructuras propias
que el verificador (``TablaOrdenada``, ``ConjuntoOrdenado``, ``ordenar``) en
lugar de ``dict``/``set``/``sorted``. Así la comparación de ``--bench
resolubilidad`` mide solo la diferencia de algoritmo (recorrido incremental
contra recorrido repetido por llave) y el código entregado no usa ``dict`` ni
``set`` como índice (constitución, principio I).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cripta.estructuras.ordenamiento import ordenar
from cripta.estructuras.tabla_ordenada import ConjuntoOrdenado, TablaOrdenada

if TYPE_CHECKING:
    from cripta.modelo.datos import DatosCripta, DatosSala, UbicacionLlave


def alcanzables(inicio, salas_por_id, obtenidas) -> ConjuntoOrdenado[int]:
    """Salas alcanzables desde ``inicio`` con las llaves ``obtenidas`` (recorrido con pila).

    ``salas_por_id`` es una ``TablaOrdenada`` (o cualquier objeto con ``obtener``
    o con ``[]``) y ``obtenidas`` cualquier colección con ``in``; así las pruebas
    pueden llamarla con sus propios datos.
    """
    obtener = salas_por_id.obtener if hasattr(salas_por_id, "obtener") else salas_por_id.__getitem__
    vistos: ConjuntoOrdenado[int] = ConjuntoOrdenado()
    vistos.agregar(inicio)
    pendientes = [inicio]
    while pendientes:
        actual = pendientes.pop()
        for salida in obtener(actual).salidas:
            if salida.cerrada and salida.llave is not None and salida.llave not in obtenidas:
                continue
            if vistos.agregar(salida.sala_destino):
                pendientes.append(salida.sala_destino)
    return vistos


def _alcanzables_por_indice(inicio: int, adyacencia: list, obtenidas: ConjuntoOrdenado[str]) -> list[bool]:
    """Recorrido completo desde cero (lo que repite el ingenuo por cada llave): O(R + E)."""
    vistos = [False] * len(adyacencia)
    vistos[inicio] = True
    pendientes = [inicio]
    while pendientes:
        actual = pendientes.pop()
        for destino, cerrada, llave in adyacencia[actual]:
            if cerrada and llave is not None and not obtenidas.contiene(llave):
                continue
            if destino >= 0 and not vistos[destino]:
                vistos[destino] = True
                pendientes.append(destino)
    return vistos


def verificar_ingenuo(
    datos: DatosCripta, salas: list[DatosSala], llaves: list[UbicacionLlave]
) -> tuple[bool, list[str]]:
    """Devuelve ``(resoluble, llaves_obtenibles_ordenadas)``.

    Prepara una vez los índices y la adyacencia (igual que el verificador
    incremental) y después repite el recorrido COMPLETO cada vez que obtiene
    llaves nuevas: esa repetición es la única diferencia que mide el bench.
    """
    indices: TablaOrdenada[int, int] = TablaOrdenada()
    for posicion in range(len(salas)):
        indices.insertar(salas[posicion].id, posicion)
    adyacencia = [
        [(indices.obtener(salida.sala_destino, -1), salida.cerrada, salida.llave) for salida in sala.salidas]
        for sala in salas
    ]
    ubicaciones: TablaOrdenada[str, list[int]] = TablaOrdenada()
    for ubicacion in llaves:
        sitios = ubicaciones.obtener(ubicacion.id)
        if sitios is None:
            sitios = []
            ubicaciones.insertar(ubicacion.id, sitios)
        sitios.append(indices.obtener(ubicacion.sala, -1))
    inicio = indices.obtener(datos.sala_inicial)
    obtenidas: ConjuntoOrdenado[str] = ConjuntoOrdenado()
    while True:
        region = _alcanzables_por_indice(inicio, adyacencia, obtenidas)
        nuevas = [
            llave_id
            for llave_id, sitios in ubicaciones.pares()
            if not obtenidas.contiene(llave_id) and any(sitio >= 0 and region[sitio] for sitio in sitios)
        ]
        if not nuevas:
            break
        for llave_id in ordenar(nuevas):
            obtenidas.agregar(llave_id)
    region = _alcanzables_por_indice(inicio, adyacencia, obtenidas)
    salida_con_llave = any(
        region[posicion]
        and salida.sala_destino == datos.sala_salida
        and salida.llave == datos.llave_salida
        for posicion in range(len(salas))
        for salida in salas[posicion].salidas
    )
    resoluble = obtenidas.contiene(datos.llave_salida) and salida_con_llave
    return resoluble, ordenar([llave for llave in obtenidas])
