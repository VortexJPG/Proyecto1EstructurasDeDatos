"""Pruebas del generador de criptas sintéticas (T009, T010)."""

import os
import unittest

from cripta.bench.sinteticos import generar_cripta


class PruebaGeneradorSintetico(unittest.TestCase):
    def test_dos_corridas_iguales(self):
        a = generar_cripta(7, salas=30, llaves=4, llave_en_enemigo=1, puertas_cambiantes=2)
        b = generar_cripta(7, salas=30, llaves=4, llave_en_enemigo=1, puertas_cambiantes=2)
        self.assertEqual(a, b)

    def test_estructura_basica(self):
        cripta = generar_cripta(11, salas=40, llaves=5)
        self.assertEqual(len(cripta.salas), 40)
        self.assertEqual(len(cripta.contenido), 40)
        self.assertEqual([s.id for s in cripta.salas], list(range(1, 41)))
        ids_llaves = [u.id for u in cripta.llaves]
        self.assertEqual(len(ids_llaves), 5)
        self.assertEqual(cripta.datos.llave_salida, ids_llaves[-1])
        fichas_llave = [f.id for f in cripta.fichas if f.clase == "llave"]
        self.assertEqual(fichas_llave, ids_llaves)

    def test_cada_llave_aparece_una_vez(self):
        cripta = generar_cripta(13, salas=30, llaves=4)
        en_suelo = [obj for sala in cripta.contenido for obj in sala.objetos]
        for ubicacion in cripta.llaves:
            self.assertEqual(en_suelo.count(ubicacion.id), 1, ubicacion.id)

    def test_llave_en_enemigo_errante(self):
        cripta = generar_cripta(5, salas=20, llaves=3, llave_en_enemigo=1)
        ubicacion = cripta.llaves[1]
        self.assertEqual(ubicacion.enemigo, "e-sint-2")
        ficha = next(f for f in cripta.fichas if f.id == "ent_sint_errante_2")
        self.assertEqual(ficha.comportamiento, "errante")
        self.assertEqual(ficha.suelta, [ubicacion.id])
        en_suelo = [obj for sala in cripta.contenido for obj in sala.objetos]
        self.assertNotIn(ubicacion.id, en_suelo)
        sala = next(s for s in cripta.contenido if s.sala == ubicacion.sala)
        self.assertEqual([e.instancia for e in sala.enemigos], ["e-sint-2"])

    def test_no_resoluble_por_ciclo(self):
        cripta = generar_cripta(3, salas=20, llaves=3, resoluble=False)
        self.assertEqual(cripta.llaves[-1].sala, cripta.datos.sala_salida)
        # la puerta de salida exige la última llave
        puerta = next(
            d
            for sala in cripta.salas
            for d in sala.salidas
            if d.sala_destino == cripta.datos.sala_salida and d.llave == cripta.datos.llave_salida
        )
        self.assertTrue(puerta.cerrada)

    def test_costos_y_cierres_automaticos(self):
        cripta = generar_cripta(
            2, salas=50, llaves=4, costo_min=10, costo_max=20, puertas_cambiantes=2
        )
        costos = [d.costo for sala in cripta.salas for d in sala.salidas if d.costo is not None]
        self.assertTrue(costos)
        self.assertTrue(all(10 <= costo <= 20 for costo in costos))
        cierres = [
            d for sala in cripta.salas for d in sala.salidas if d.cierre_automatico is not None
        ]
        self.assertEqual(len(cierres), 2)

    def test_sin_estructuras_prohibidas(self):
        ruta = os.path.join(os.path.dirname(__file__), "..", "cripta", "bench", "sinteticos.py")
        with open(ruta, encoding="utf-8") as archivo:
            texto = archivo.read()
        for prohibido in ("import heapq", "import bisect", "import collections", "import networkx"):
            self.assertNotIn(prohibido, texto)

    def test_modulos_evaluados_sin_prohibidos(self):
        base = os.path.join(os.path.dirname(__file__), "..", "cripta")
        modulos = [
            os.path.join(base, "modelo", "verificacion.py"),
            os.path.join(base, "bench", "sinteticos.py"),
            os.path.join(base, "bench", "bench_resolubilidad.py"),
        ]
        for ruta in modulos:
            with open(ruta, encoding="utf-8") as archivo:
                texto = archivo.read()
            for prohibido in (
                "import heapq",
                "import bisect",
                "import collections",
                "import networkx",
                "from collections",
                "sorted(",
                ".sort(",
            ):
                self.assertNotIn(prohibido, texto, f"{prohibido} en {ruta}")


if __name__ == "__main__":
    unittest.main()
