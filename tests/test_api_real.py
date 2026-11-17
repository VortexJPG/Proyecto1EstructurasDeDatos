"""Prueba de aceptación contra la API real (opt-in).

No se ejecuta en la suite normal porque necesita red y consume el presupuesto
del servicio. Para correrla:

    CRIPTA_API_REAL=1 .venv/bin/python -m unittest tests.test_api_real -v

Evidencia de la corrida del 2026-11-17: `docs/mediciones/p2_api_real.txt`.
"""

import os
import shutil
import tempfile
import unittest

from cripta.adaptadores.cliente_http import BASE_URL, ClienteHTTP
from cripta.controlador.controlador import Controlador, OpcionesEjecucion

ACTIVA = os.environ.get("CRIPTA_API_REAL") == "1"


@unittest.skipUnless(ACTIVA, "define CRIPTA_API_REAL=1 para usar la red")
class PruebaApiReal(unittest.TestCase):
    def setUp(self):
        self.directorio = tempfile.mkdtemp(prefix="cripta_api_")

    def tearDown(self):
        shutil.rmtree(self.directorio, ignore_errors=True)

    def test_contrato_criptas_y_llaves(self):
        cliente = ClienteHTTP(BASE_URL)
        criptas = cliente.listar_criptas()
        ids = [cripta.id for cripta in criptas]
        self.assertIn("cripta-06", ids)

        datos = cliente.datos_cripta("cripta-06")
        self.assertEqual(datos.salas_total, 300)
        self.assertGreater(datos.presupuesto_solicitudes, 0)

        llaves = cliente.llaves("cripta-06")
        ids_llaves = [ubicacion.id for ubicacion in llaves]
        self.assertIn(datos.llave_salida, ids_llaves)
        self.assertTrue(any(ubicacion.enemigo for ubicacion in llaves))
        self.assertLessEqual(
            cliente.estadisticas().solicitudes_realizadas,
            datos.presupuesto_solicitudes,
        )
        self.assertEqual(cliente.estadisticas().errores, 0)

    def test_verificar_cripta_05_y_06(self):
        for cripta_id, esperado in (("cripta-05", False), ("cripta-06", True)):
            cliente = ClienteHTTP(BASE_URL)
            controlador = Controlador(
                cliente,
                OpcionesEjecucion(
                    directorio_datos=os.path.join(self.directorio, cripta_id),
                    cache_size=25,
                ),
                None,
            )
            resultado = controlador.verificar_cripta(cripta_id)
            self.assertEqual(resultado.resoluble, esperado, cripta_id)
            self.assertLessEqual(
                cliente.estadisticas().solicitudes_realizadas,
                controlador._datos.presupuesto_solicitudes,
                cripta_id,
            )
            self.assertEqual(cliente.estadisticas().errores, 0, cripta_id)


if __name__ == "__main__":
    unittest.main()
