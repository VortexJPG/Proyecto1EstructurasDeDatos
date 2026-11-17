"""Auditoría de entrega de la Persona B: casos, tareas y evidencias.

No repite la lógica del juego: comprueba que la documentación de aceptación
está conectada con las pruebas y que no quedan tareas pendientes.
"""

import os
import unittest

RAIZ = os.path.join(os.path.dirname(__file__), "..")
CASOS = (
    "AC-004-01",
    "AC-004-02",
    "AC-004-03",
    "AC-004-04",
    "AC-005-01",
    "AC-005-02",
    "AC-005-03",
    "AC-005-04",
    "AC-005-05",
    "AC-005-06",
)
ARCHIVOS = (
    "test_resolubilidad.py",
    "test_timeline.py",
    "test_integracion.py",
    "test_interfaz_a_b.py",
)


class PruebaTrazabilidadB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        textos = []
        for nombre in ARCHIVOS:
            with open(os.path.join(os.path.dirname(__file__), nombre), encoding="utf-8") as archivo:
                textos.append(archivo.read())
        cls.pruebas = "\n".join(textos)

    def test_los_diez_casos_del_apendice_b_se_citan(self):
        for caso in CASOS:
            self.assertIn(caso, self.pruebas, caso)

    def test_sin_tareas_pendientes_en_004_y_005(self):
        for spec in ("004-resolubilidad-llaves", "005-linea-de-tiempo"):
            ruta = os.path.join(RAIZ, "specs", spec, "tasks.md")
            with open(ruta, encoding="utf-8") as archivo:
                self.assertNotIn("- [ ]", archivo.read(), spec)

    def test_decisiones_tiene_las_secciones_b(self):
        with open(os.path.join(RAIZ, "DECISIONES.md"), encoding="utf-8") as archivo:
            texto = archivo.read()
        for seccion in ("## 5.4", "## 5.5", "### 5.6-B"):
            self.assertIn(seccion, texto, seccion)

    def test_mediciones_base_existen(self):
        for nombre in (
            "p1_linea_base.txt",
            "p2_resolubilidad.txt",
            "p2_timeline.txt",
            "p2_historial.txt",
            "p2_api_real.txt",
        ):
            ruta = os.path.join(RAIZ, "docs", "mediciones", nombre)
            self.assertTrue(os.path.exists(ruta), nombre)


if __name__ == "__main__":
    unittest.main()
