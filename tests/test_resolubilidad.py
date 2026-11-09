"""Pruebas del oráculo, de la definición estricta y del verificador (T011..T038).

El oráculo vive en ``cripta/bench/ingenuo.py`` porque solo se usa en pruebas y
mediciones; la verificación de producción es incremental.
"""

import unittest

from cripta.bench.ingenuo import verificar_ingenuo
from cripta.bench.sinteticos import generar_cripta
from cripta.modelo.datos import (
    DatosCripta,
    DatosSala,
    DatosSalida,
    EstadisticasIniciales,
    UbicacionLlave,
)
from cripta.modelo.mapa import Mapa
from cripta.modelo.verificacion import Verificador, formatear_resultado


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


def _verificar(cripta):
    mapa = Mapa.construir(cripta.datos, cripta.salas)
    return Verificador(cripta.datos, mapa, cripta.llaves).verificar()


def _manual(datos, salas, llaves):
    return Verificador(datos, Mapa.construir(datos, salas), llaves).verificar()


class PruebaVerificador(unittest.TestCase):
    def test_resoluble(self):
        cripta = generar_cripta(7, salas=30, llaves=4)
        resultado = _verificar(cripta)
        self.assertTrue(resultado.resoluble)
        self.assertEqual(resultado.orden_llaves, [f"itm_sint_llave_{j}" for j in range(1, 5)])
        self.assertEqual(resultado.llaves_inobtenibles, [])
        self.assertEqual(resultado.frontera, [])

    def test_no_resoluble_con_ciclo(self):
        cripta = generar_cripta(3, salas=20, llaves=3, resoluble=False)
        resultado = _verificar(cripta)
        self.assertFalse(resultado.resoluble)
        self.assertIn("llave de salida", resultado.motivo)
        self.assertEqual([l.id for l in resultado.llaves_inobtenibles], ["itm_sint_llave_3"])
        self.assertEqual(resultado.llaves_inobtenibles[0].ubicaciones[0].sala, cripta.datos.sala_salida)
        self.assertTrue(resultado.frontera)
        self.assertTrue(resultado.ciclo)
        self.assertEqual(resultado.ciclo[0].llave, "itm_sint_llave_3")
        self.assertEqual(resultado.ciclo[0].llave_requerida, "itm_sint_llave_3")
        texto = formatear_resultado(resultado)
        self.assertIn("NO RESOLUBLE", texto)
        self.assertIn("Ciclo:", texto)

    def test_llave_de_enemigo(self):
        cripta = generar_cripta(9, salas=30, llaves=4, llave_en_enemigo=2)
        resultado = _verificar(cripta)
        self.assertTrue(resultado.resoluble)
        self.assertIn("itm_sint_llave_3", resultado.orden_llaves)

    def test_determinista(self):
        cripta = generar_cripta(11, salas=40, llaves=5)
        self.assertEqual(_verificar(cripta), _verificar(cripta))

    def test_llave_salida_ausente(self):
        salas = [
            DatosSala(1, "Uno", [DatosSalida("N", 2)]),
            DatosSala(2, "Dos", [DatosSalida("S", 1)]),
        ]
        llaves = [UbicacionLlave("itm_k", 1)]
        resultado = _manual(_datos(llave_salida="itm_x", salas=2), salas, llaves)
        self.assertFalse(resultado.resoluble)
        self.assertIn("no aparece", resultado.motivo)

    def test_salida_libre_no_basta(self):
        salas = [
            DatosSala(1, "Uno", [DatosSalida("N", 2)]),
            DatosSala(2, "Dos", [DatosSalida("S", 1), DatosSalida("N", 3)]),
            DatosSala(3, "Salida", [DatosSalida("S", 2)]),
        ]
        resultado = _manual(_datos(), salas, [UbicacionLlave("itm_k", 1)])
        self.assertFalse(resultado.resoluble)
        self.assertIn("no hay una salida", resultado.motivo)
        self.assertEqual(resultado.llave_salida_obtenida, True)

    def test_puerta_exige_llave_no_listada(self):
        salas = [
            DatosSala(1, "Uno", [DatosSalida("N", 2, cerrada=True, llave="itm_faltante")]),
            DatosSala(2, "Dos", [DatosSalida("S", 1)]),
        ]
        resultado = _manual(_datos(salas=2), salas, [UbicacionLlave("itm_k", 1)])
        self.assertFalse(resultado.resoluble)
        self.assertIn("itm_faltante", [l.id for l in resultado.llaves_inobtenibles])
        self.assertEqual(resultado.frontera[0].llave_requerida, "itm_faltante")

    def test_llave_duplicada(self):
        salas = [
            DatosSala(1, "Uno", [DatosSalida("N", 2, cerrada=True, llave="itm_k")]),
            DatosSala(2, "Dos", [DatosSalida("S", 1),
                                 DatosSalida("N", 3, cerrada=True, llave="itm_k")]),
            DatosSala(3, "Salida", [DatosSalida("S", 2)]),
        ]
        llaves = [UbicacionLlave("itm_k", 1), UbicacionLlave("itm_k", 3)]
        resultado = _manual(_datos(), salas, llaves)
        self.assertTrue(resultado.resoluble)
        self.assertEqual(resultado.orden_llaves, ["itm_k"])

    def test_frontera_sin_duplicar_puerta_compartida(self):
        salas = [
            DatosSala(1, "Uno", [DatosSalida("N", 2, cerrada=True, llave="itm_k")]),
            DatosSala(2, "Dos", [DatosSalida("S", 1, cerrada=True, llave="itm_k"),
                                 DatosSalida("N", 3)]),
            DatosSala(3, "Tres", [DatosSalida("S", 2)]),
        ]
        llaves = [UbicacionLlave("itm_k", 3)]
        resultado = _manual(_datos(llave_salida="itm_x", salas=3), salas, llaves)
        self.assertFalse(resultado.resoluble)
        self.assertEqual(len(resultado.frontera), 1)
        self.assertEqual(resultado.frontera[0].puerta_id, "p-1N-2")

    def test_ac_004_03_dos_corridas_mismo_orden(self):
        cripta = generar_cripta(13, salas=40, llaves=5)
        primera = _verificar(cripta)
        segunda = _verificar(cripta)
        self.assertTrue(primera.resoluble)
        self.assertEqual(primera.orden_llaves, segunda.orden_llaves)
        self.assertEqual(primera, segunda)

    def test_validez_del_orden(self):
        from cripta.bench.ingenuo import alcanzables

        for semilla in range(5):
            cripta = generar_cripta(semilla, salas=30, llaves=4)
            resultado = _verificar(cripta)
            self.assertTrue(resultado.resoluble)
            salas_por_id = {sala.id: sala for sala in cripta.salas}
            ubicaciones = {}
            for ubicacion in cripta.llaves:
                ubicaciones.setdefault(ubicacion.id, []).append(ubicacion.sala)
            obtenidas = set()
            for llave_id in resultado.orden_llaves:
                region = alcanzables(cripta.datos.sala_inicial, salas_por_id, obtenidas)
                self.assertTrue(
                    any(sala in region for sala in ubicaciones[llave_id]),
                    (semilla, llave_id),
                )
                obtenidas.add(llave_id)
            self.assertEqual(resultado.orden_llaves[-1], cripta.datos.llave_salida)

    def test_desempate_por_id(self):
        salas = [
            DatosSala(1, "Uno", [DatosSalida("N", 2, cerrada=True, llave="itm_b")]),
            DatosSala(2, "Salida", [DatosSalida("S", 1)]),
        ]
        llaves = [UbicacionLlave("itm_b", 1), UbicacionLlave("itm_a", 1)]
        resultado = _manual(_datos(llave_salida="itm_b", salas=2), salas, llaves)
        self.assertTrue(resultado.resoluble)
        self.assertEqual(resultado.orden_llaves, ["itm_a", "itm_b"])

    def test_coincide_con_el_oraculo(self):
        for salas in (12, 20, 40):
            for llaves in (1, 2, 3, 5):
                if salas < llaves + 2:
                    continue
                for semilla in range(10):
                    for resoluble in (True, False):
                        cripta = generar_cripta(
                            semilla, salas=salas, llaves=llaves, resoluble=resoluble,
                            llave_en_enemigo=(1 if llaves > 1 else None),
                            puertas_cambiantes=min(2, llaves),
                        )
                        resultado = _verificar(cripta)
                        ok, obtenidas = verificar_ingenuo(cripta.datos, cripta.salas, cripta.llaves)
                        inobtenibles = [l.id for l in resultado.llaves_inobtenibles]
                        obtenidas_produccion = [
                            u.id for u in cripta.llaves if u.id not in inobtenibles
                        ]
                        self.assertEqual(resultado.resoluble, ok, (salas, llaves, semilla, resoluble))
                        self.assertEqual(
                            sorted(set(obtenidas_produccion)), sorted(obtenidas),
                            (salas, llaves, semilla, resoluble),
                        )


if __name__ == "__main__":
    unittest.main()