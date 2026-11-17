"""Aprobación y contenido mínimo de la constitución v1.0.1.

No es una prueba de código: comprueba que el documento que gobierna el
proyecto está completo, versionado y aprobado por ambos integrantes.
"""

import os
import unittest

RUTA = os.path.join(
    os.path.dirname(__file__), "..", ".specify", "memory", "constitution.md"
)


class PruebaConstitucion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(RUTA, encoding="utf-8") as archivo:
            cls.texto = archivo.read()
        cls.minusculas = cls.texto.lower()

    def test_version_1_0_1(self):
        self.assertIn("**Version**: 1.0.1", self.texto)

    def test_siete_principios(self):
        for romano in ("I", "II", "III", "IV", "V", "VI", "VII"):
            self.assertIn(f"### {romano}.", self.texto, romano)

    def test_aprobacion_de_ambos(self):
        self.assertIn("Persona A (2026-11-15)", self.texto)
        self.assertIn("Persona B (2026-11-17)", self.texto)
        self.assertIn("Aprobada por la Persona B el 2026-11-17", self.texto)

    def test_prohibiciones_y_estructuras(self):
        for termino in ("dict", "set", "heapq", "bisect", "collections", "networkx"):
            self.assertIn(termino, self.minusculas, termino)

    def test_principios_operativos(self):
        for termino in (
            "determinismo",
            "mvc",
            "--replay",
            "--bench",
            "--verificar",
            "presupuesto_solicitudes",
            "spec",
            "decisiones.md",
        ):
            self.assertIn(termino, self.minusculas, termino)

    def test_sin_plantillas_pendientes(self):
        for marcador in ("[PRINCIPLE", "[SECTION", "[GOVERNANCE", "[PROJECT_NAME]"):
            self.assertNotIn(marcador, self.texto, marcador)


if __name__ == "__main__":
    unittest.main()
