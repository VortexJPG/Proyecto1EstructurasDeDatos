"""Oráculo ingenuo de resolubilidad (T011) y pruebas de la definición estricta.

El oráculo repite el recorrido desde cero cada vez que obtiene una llave. Es
**solo para pruebas**: la verificación de producción es incremental. Puede usar
``dict``/``set`` porque no forma parte del juego evaluado.
"""

import unittest

from cripta.bench.sinteticos import generar_cripta
from cripta.modelo.datos import (
    DatosCripta,
    DatosSala,
    DatosSalida,
    EstadisticasIniciales,
    UbicacionLlave,
)


def _alcanzables(inicio, salas_por_id, obtenidas):
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


def verificar_ingenuo(datos, salas, llaves):
    """Devuelve ``(resoluble, llaves_obtenibles_ordenadas)``."""
    salas_por_id = {sala.id: sala for sala in salas}
    ubicaciones = {}
    for ubicacion in llaves:
        ubicaciones.setdefault(ubicacion.id, []).append(ubicacion.sala)
    obtenidas = set()
    while True:
        region = _alcanzables(datos.sala_inicial, salas_por_id, obtenidas)
        nuevas = [
            llave_id
            for llave_id, sitios in ubicaciones.items()
            if llave_id not in obtenidas and any(sitio in region for sitio in sitios)
        ]
        if not nuevas:
            break
        for llave_id in sorted(nuevas):
            obtenidas.add(llave_id)
    region = _alcanzables(datos.sala_inicial, salas_por_id, obtenidas)
    salida_con_llave = any(
        sala.id in region
        and salida.sala_destino == datos.sala_salida
        and salida.llave == datos.llave_salida
        for sala in salas
        for salida in sala.salidas
    )
    resoluble = datos.llave_salida in obtenidas and salida_con_llave
    return resoluble, sorted(obtenidas)


def _datos(llave_salida="itm_k", salas=3):
    return DatosCripta(
        id="manual",
        version="v1",
        salas_total=salas,
        paginas=1,
        salas_por_pagina=50,
        sala_inicial=1,
        sala_salida=salas,
        llave_salida=llave_salida,
        presupuesto_solicitudes=10,
        inventario_max=5,
        jugador=EstadisticasIniciales(vida_max=30, ataque=5, defensa=1, velocidad=100),
    )


class PruebaOraculo(unittest.TestCase):
    def test_sintetica_resoluble(self):
        cripta = generar_cripta(7, salas=30, llaves=4)
        resoluble, obtenidas = verificar_ingenuo(cripta.datos, cripta.salas, cripta.llaves)
        self.assertTrue(resoluble)
        self.assertEqual(len(obtenidas), 4)

    def test_sintetica_con_llave_de_enemigo(self):
        cripta = generar_cripta(9, salas=30, llaves=4, llave_en_enemigo=2)
        resoluble, obtenidas = verificar_ingenuo(cripta.datos, cripta.salas, cripta.llaves)
        self.assertTrue(resoluble)
        self.assertEqual(len(obtenidas), 4)

    def test_sintetica_no_resoluble(self):
        cripta = generar_cripta(3, salas=20, llaves=3, resoluble=False)
        resoluble, obtenidas = verificar_ingenuo(cripta.datos, cripta.salas, cripta.llaves)
        self.assertFalse(resoluble)
        self.assertEqual(len(obtenidas), 2)  # la última está detrás de su puerta

    def test_llegar_por_salida_libre_no_basta(self):
        salas = [
            DatosSala(1, "Uno", [DatosSalida("N", 2)]),
            DatosSala(2, "Dos", [DatosSalida("S", 1), DatosSalida("N", 3)]),
            DatosSala(3, "Salida", [DatosSalida("S", 2)]),
        ]
        llaves = [UbicacionLlave("itm_k", 1)]
        resoluble, obtenidas = verificar_ingenuo(_datos(), salas, llaves)
        self.assertIn("itm_k", obtenidas)
        self.assertFalse(resoluble)  # no hay puerta de salida que requiera la llave

    def test_puerta_de_salida_con_llave(self):
        salas = [
            DatosSala(1, "Uno", [DatosSalida("N", 2)]),
            DatosSala(2, "Dos", [DatosSalida("S", 1),
                                 DatosSalida("N", 3, cerrada=True, llave="itm_k")]),
            DatosSala(3, "Salida", [DatosSalida("S", 2)]),
        ]
        llaves = [UbicacionLlave("itm_k", 1)]
        resoluble, obtenidas = verificar_ingenuo(_datos(), salas, llaves)
        self.assertTrue(resoluble)
        self.assertEqual(obtenidas, ["itm_k"])

    def test_puerta_cerrada_sin_llave_se_puede_cruzar(self):
        salas = [
            DatosSala(1, "Uno", [DatosSalida("N", 2, cerrada=True)]),
            DatosSala(2, "Dos", [DatosSalida("S", 1),
                                 DatosSalida("N", 3, cerrada=True, llave="itm_salida")]),
            DatosSala(3, "Salida", [DatosSalida("S", 2)]),
        ]
        llaves = [UbicacionLlave("itm_salida", 2)]
        resoluble, obtenidas = verificar_ingenuo(
            _datos(llave_salida="itm_salida", salas=3), salas, llaves
        )
        self.assertTrue(resoluble)
        self.assertEqual(obtenidas, ["itm_salida"])


if __name__ == "__main__":
    unittest.main()
