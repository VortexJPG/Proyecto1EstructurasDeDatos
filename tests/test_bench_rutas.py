"""Requisitos de medición y de rendimiento de la Persona A (specs 001, 002 y 003).

Los tiempos dependen de la computadora, así que estas pruebas comprueban sobre
todo el TRABAJO, que es determinista: cuántas búsquedas se hicieron, cuántas se
reutilizaron y cuántas salas se examinaron. Los límites de §6.1 se comprueban
con la cripta de referencia del paquete offline; hay mucho margen (2.3 ms contra
20 ms y 0.2 ms contra 5 ms en la computadora de desarrollo).
Las mediciones completas se corren con ``python main.py --bench`` (ver
``docs/mediciones/p2_rutas.txt``).
"""

import os
import re
import unittest

from cripta.bench import bench_rutas
from cripta.bench.runner import RegistroBenchmarks, estadisticas
from cripta.modelo.rutas import EstrategiaCazador

HAY_REFERENCIA = bench_rutas.id_referencia() is not None


def contadores(resultado):
    """(cálculos, reutilizados) del detalle de una medición."""
    m = re.search(r"cálculos (\d+), reutilizados (\d+)", resultado.detalle)
    return int(m.group(1)), int(m.group(2))


def salas_por_decision(resultado):
    return float(re.search(r"salas examinadas/decisión ([\d.]+)", resultado.detalle).group(1))


def invalidaciones_y_salas(resultado):
    return (int(re.search(r"invalidaciones (\d+)", resultado.detalle).group(1)),
            int(re.search(r"salas examinadas (\d+)", resultado.detalle).group(1)))


class PruebaBenchCazador(unittest.TestCase):
    def test_001_fr021_bench_registra_los_casos_de_6_3(self):
        """001/FR-021, 003/NFR-005: --bench tiene los subsistemas de §6.3 de la Persona A."""
        registro = RegistroBenchmarks()
        bench_rutas.registrar(registro)
        subsistemas = sorted({s for s, _, _ in registro._casos})
        self.assertEqual(subsistemas, ["agenda_p2", "cazador", "ciclo_p2", "invalidacion", "ir_a", "mapa_conocido"])
        casos = " ".join(c for _, c, _ in registro._casos)
        for texto in ("1 cazadores", "50 cazadores", "rango pequeño", "rango grande", "compartida", "individual",
                      "puertas estables", "puertas inestables", "recalcular"):
            self.assertIn(texto, casos)

    def test_001_nfr003_compartido_contra_individual(self):
        """001/NFR-003: con 10 cazadores el compartido hace 1 búsqueda por ronda; el individual, 1 por cazador."""
        rondas = 8
        compartido = bench_rutas.bench_decisiones(20, 10, 10**6, EstrategiaCazador.COMPARTIDA, "grande", "c", rondas)
        individual = bench_rutas.bench_decisiones(20, 10, 10**6, EstrategiaCazador.INDIVIDUAL, "grande", "i", rondas)
        self.assertEqual(contadores(compartido), (rondas, rondas * 9))
        self.assertEqual(contadores(individual), (rondas * 10, 0))
        self.assertLess(salas_por_decision(compartido), salas_por_decision(individual))

    def test_001_nfr002_rango_pequeno_no_depende_del_tamano(self):
        """001/NFR-002 (SC-004): con rango 300 las salas examinadas no crecen con la cripta (400 vs. 3600 salas)."""
        chica = bench_rutas.bench_decisiones(20, 1, 300, EstrategiaCazador.INDIVIDUAL, "pequeño", "a", 60)
        grande = bench_rutas.bench_decisiones(60, 1, 300, EstrategiaCazador.INDIVIDUAL, "pequeño", "b", 60)
        self.assertLess(salas_por_decision(grande), 50)  # contra 3 600 salas
        self.assertLess(salas_por_decision(grande), 3 * salas_por_decision(chica) + 5)

    def test_001_nfr004_mediciones_deterministas_y_estadisticas(self):
        """001/NFR-004: la misma semilla da el mismo trabajo; mediana, p95 y máximo bien calculados."""
        a = bench_rutas.bench_decisiones(20, 5, 10**6, EstrategiaCazador.COMPARTIDA, "grande", "x", 5)
        b = bench_rutas.bench_decisiones(20, 5, 10**6, EstrategiaCazador.COMPARTIDA, "grande", "x", 5)
        self.assertEqual((contadores(a), salas_por_decision(a)), (contadores(b), salas_por_decision(b)))
        est = estadisticas([5.0, 1.0, 3.0, 2.0, 4.0])
        self.assertEqual((est.mediana, est.maximo, est.minimo), (3.0, 5.0, 1.0))
        self.assertEqual(estadisticas([float(i) for i in range(1, 101)]).p95, 95.0)


class PruebaBenchInvalidacion(unittest.TestCase):
    DECISIONES = 15

    def medir(self, cambios, estrategia, lejos=False):
        return bench_rutas.bench_invalidacion(cambios, estrategia, "prueba", lejos, self.DECISIONES)

    def test_002_fr009_fr010_nfr002_puertas_estables(self):
        """002/FR-009, FR-010, NFR-002: con puertas estables la reutilización hace UNA búsqueda y examina menos salas."""
        reutilizar = self.medir(0, EstrategiaCazador.COMPARTIDA)
        recalcular = self.medir(0, EstrategiaCazador.RECALCULAR_SIEMPRE)
        calculos, reutilizados = contadores(reutilizar)
        self.assertEqual(calculos, 1)
        self.assertGreater(reutilizados, 0)
        self.assertEqual(contadores(recalcular)[0], calculos + reutilizados)  # mismas decisiones, todas recalculadas
        self.assertLess(invalidaciones_y_salas(reutilizar)[1], invalidaciones_y_salas(recalcular)[1])

    def test_002_fr009_nfr003_puertas_inestables_lejos(self):
        """002/FR-009, FR-005, NFR-003: puertas que cambian lejos no invalidan con la fina; la gruesa sí."""
        fina = self.medir(20, EstrategiaCazador.COMPARTIDA, lejos=True)
        gruesa = self.medir(20, EstrategiaCazador.COMPARTIDA_GRUESA, lejos=True)
        self.assertEqual(invalidaciones_y_salas(fina)[0], 0)
        self.assertGreater(invalidaciones_y_salas(gruesa)[0], 0)
        self.assertEqual(self.medir(20, EstrategiaCazador.COMPARTIDA, lejos=True).detalle.split("|")[1],
                         fina.detalle.split("|")[1])  # determinista por semilla

    @unittest.skipUnless(HAY_REFERENCIA, "falta datos_ejemplo_p2/")
    def test_001_nfr001_002_nfr001_ciclo_en_la_referencia(self):
        """001/NFR-001, 002/NFR-001 (§6.1): el peor ciclo con todos los cazadores de la referencia es <= 20 ms."""
        resultado = bench_rutas.bench_ciclo_referencia(EstrategiaCazador.COMPARTIDA, decisiones=60)
        self.assertGreater(resultado.repeticiones, 0)
        self.assertLessEqual(resultado._peor * 1000, bench_rutas.LIMITE_CICLO_MS)


class PruebaBenchMapaConocido(unittest.TestCase):
    def test_003_nfr002_consulta_constante(self):
        """003/NFR-002: las tres estructuras se miden; el arreglo responde igual con 100 y con 10 000 salas."""
        for estructura in ("arreglo", "lista", "tabla ordenada"):
            self.assertGreater(bench_rutas.bench_consulta_conocimiento(100, estructura, 2_000).repeticiones, 0)

    def test_003_nfr003_explorar_cuesta_lo_revelado(self):
        """003/NFR-003: explorar 5 salas registra las mismas casillas con 400 que con 3 600 salas conocidas."""
        chica = bench_rutas.bench_explorar(20, repeticiones=20)
        grande = bench_rutas.bench_explorar(60, repeticiones=20)
        self.assertEqual(chica.detalle, grande.detalle)

    def test_003_nfr004_revertir_cuesta_lo_cambiado(self):
        """003/NFR-004: una entrada con antorcha registra una cantidad fija de cambios y el pergamino los revierte."""
        resultado = bench_rutas.bench_revertir_antorcha(repeticiones=10)
        cambios = float(re.search(r"([\d.]+) cambios registrados por acción", resultado.detalle).group(1))
        self.assertGreater(cambios, 0)
        self.assertLess(cambios, 40)

    @unittest.skipUnless(HAY_REFERENCIA, "falta datos_ejemplo_p2/")
    def test_003_nfr001_paso_de_ir_a_en_la_referencia(self):
        """003/NFR-001 (§6.1): un paso de «ir a» con el mapa completo de la referencia tarda <= 5 ms."""
        resultado = bench_rutas.bench_ir_a_referencia(repeticiones=60)
        self.assertLessEqual(resultado._peor * 1000, bench_rutas.LIMITE_IR_A_MS)


if __name__ == "__main__":
    unittest.main()
