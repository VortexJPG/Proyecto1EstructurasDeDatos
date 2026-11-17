"""Spec 002 — Invalidación de rutas (Persona A).

Cada prueba cita ``002/FR-xxx`` o ``AC-002-xx``. La regla central (FR-001) se
comprueba envolviendo ``RutasCazadores.decidir``: en cada turno real de cada
cazador se compara lo que decide el juego con el cálculo desde cero.
"""

import random
import unittest

from cripta.modelo.acciones import Accion, TipoAccion
from cripta.modelo.rutas import EstrategiaCazador
from tests.apoyo_p2 import (
    CriptaPrueba,
    activar,
    cuadricula,
    decision_juego,
    decision_oraculo,
    ficha_cazador,
    salida,
)

ESPERAR = Accion(TipoAccion.ESPERAR)


def mover(direccion):
    return Accion(TipoAccion.MOVER, direccion=direccion)


def vigilar(prueba, juego):
    """Envuelve ``juego.rutas.decidir`` para comparar CADA decisión con el oráculo (FR-001)."""
    original = juego.rutas.decidir
    contador = [0]

    def decidir(cazador, sala_jugador):
        esperado = decision_oraculo(juego, cazador)
        resultado = original(cazador, sala_jugador)
        obtenido = ("esperar", None, None) if resultado is None else ("mover", resultado.destino.id, resultado.direccion)
        prueba.assertEqual(obtenido, esperado, f"decisión distinta al cálculo desde cero (t={juego.reloj})")
        contador[0] += 1
        return resultado

    juego.rutas.decidir = decidir
    return contador


def dos_rutas():
    """Cazador en 1, jugador en 4. Ruta corta 1→2→4 (puerta 2-4) y larga 1→3→4."""
    return [
        (1, [salida("N", 2, 100), salida("E", 3, 300)]),
        (2, [salida("S", 1), salida("E", 4, 100, cerrada=False, cierre=None)]),
        (3, [salida("O", 1), salida("N", 4, 300)]),
        (4, [salida("O", 2), salida("S", 3)]),
    ]


class PruebaInvalidacion(unittest.TestCase):
    def preparar(self, salas, inicial, sala_cazador, rango=10_000, estrategia=EstrategiaCazador.COMPARTIDA):
        cripta = CriptaPrueba(salas, inicial=inicial).con_enemigo(
            sala_cazador, "e-caz", "ent_cazador", ficha_cazador(rango))
        juego = cripta.juego(estrategia=estrategia)
        activar(juego, "e-caz")
        return juego, juego.enemigos.obtener("e-caz")

    def test_ac_002_01_puerta_de_la_ruta_se_cierra_entre_turnos(self):
        """AC-002-01 / 002/FR-001, FR-003: se cierra la puerta de la ruta ⇒ decide como desde cero."""
        salas = dos_rutas()
        salas[1] = (2, [salida("S", 1), salida("E", 4, 100, cerrada=False, llave=None, cierre=10_000)])
        juego, cazador = self.preparar(salas, 4, 1)
        self.assertEqual(decision_juego(juego, cazador), ("mover", 2, "N"))
        calculos = juego.rutas.calculos
        juego.mapa.sala(2).salida("E").puerta.cerrada = True  # como si se cerrara sola
        self.assertEqual(decision_juego(juego, cazador), decision_oraculo(juego, cazador))
        self.assertEqual(decision_juego(juego, cazador), ("mover", 3, "E"))
        self.assertGreater(juego.rutas.calculos, calculos)

    def test_002_fr003_el_jugador_cambia_de_sala(self):
        """002/FR-003: el jugador se mueve ⇒ la siguiente decisión apunta a la sala nueva."""
        salas = [(i, l) for i, l in cuadricula(4, semilla=1, costos=(100,))]
        juego, cazador = self.preparar(salas, 16, 1)
        primera = decision_juego(juego, cazador)
        juego.ejecutar_accion(mover("N"))  # 16 → 12
        self.assertEqual(juego.jugador.sala.id, 12)
        self.assertEqual(decision_juego(juego, cazador), decision_oraculo(juego, cazador))
        self.assertIsNotNone(primera)

    def test_ac_002_02_puerta_lejos_no_obliga_a_recalcular(self):
        """AC-002-02 / 002/FR-004, FR-005: una puerta fuera de la región cambia ⇒ mismas decisiones y ningún cálculo nuevo."""
        # Línea 1..8 con puertas abiertas; jugador en 1, cazador en 3 con rango 250:
        # la región llega hasta la sala 3 (costo 200). La puerta 6-7 está lejos.
        salas = []
        for i in range(1, 9):
            lista = []
            if i < 8:
                lista.append(salida("E", i + 1, 100, cerrada=False, cierre=5000))
            if i > 1:
                lista.append(salida("O", i - 1))
            salas.append((i, lista))
        juego, cazador = self.preparar(salas, 1, 3, rango=250)
        antes = decision_juego(juego, cazador)
        calculos = juego.rutas.calculos
        lejos = juego.mapa.sala(6).salida("E").puerta
        for _ in range(5):
            lejos.cerrada = not lejos.cerrada
            self.assertEqual(decision_juego(juego, cazador), antes)
        self.assertEqual(juego.rutas.calculos, calculos)
        self.assertEqual(juego.rutas.invalidaciones, 0)
        # En cambio, la gruesa invalida con cualquier cambio de puerta.
        gruesa, cazador_g = self.preparar(salas, 1, 3, rango=250, estrategia=EstrategiaCazador.COMPARTIDA_GRUESA)
        decision_juego(gruesa, cazador_g)
        gruesa.mapa.sala(6).salida("E").puerta.cerrada = True
        decision_juego(gruesa, cazador_g)
        self.assertEqual(gruesa.rutas.calculos, 2)

    def test_002_fr004_reutiliza_entre_cazadores_y_turnos(self):
        """002/FR-004, SC-003: jugador quieto y puertas estables ⇒ un solo cálculo para todos."""
        cripta = CriptaPrueba(cuadricula(5, semilla=2, costos=(100, 200)), inicial=13)
        cripta.fichas.append(ficha_cazador(10_000))
        for k, sala in enumerate((1, 5, 21, 25)):
            cripta.con_enemigo(sala, f"e-{k}", "ent_cazador")
        juego = cripta.juego()
        activar(juego, "e-0", "e-1", "e-2", "e-3")
        for _ in range(3):  # los cazadores se acercan pero el jugador no se mueve
            juego.ejecutar_accion(ESPERAR)
        self.assertEqual(juego.rutas.calculos, 1)
        self.assertGreater(juego.rutas.reutilizados, 0)

    def test_002_fr006_pergamino_revierte_una_apertura(self):
        """002/FR-006: un pergamino revierte la apertura de una puerta ⇒ la siguiente decisión es la de desde cero."""
        salas = [
            (1, [salida("E", 2, 100, cerrada=True)]),  # puerta 1-2 cerrada sin llave (se puede abrir)
            (2, [salida("O", 1), salida("E", 3, 100)]),
            (3, [salida("O", 2), salida("N", 4, 900)]),
            (4, [salida("S", 3), salida("O", 5, 900)]),
            (5, [salida("E", 4), salida("S", 1, 900)]),
        ]
        cripta = CriptaPrueba(salas, inicial=1).con_enemigo(3, "e-caz", "ent_cazador", ficha_cazador(10_000))
        cripta.con_objeto(1, "itm_pergamino")
        juego = cripta.juego()
        activar(juego, "e-caz")
        cazador = juego.enemigos.obtener("e-caz")
        juego.ejecutar_accion(Accion(TipoAccion.RECOGER, objetivo=juego.jugador.sala.objetos_suelo.a_lista()[0].id))
        self.assertEqual(decision_juego(juego, cazador), ("mover", 4, "N"))  # rodeo por 4-5
        juego.ejecutar_accion(Accion(TipoAccion.ABRIR, direccion="E"))
        self.assertEqual(decision_juego(juego, cazador), decision_oraculo(juego, cazador))
        self.assertTrue(juego.usar_pergamino().aceptada)
        self.assertTrue(juego.mapa.sala(1).salida("E").puerta.cerrada)
        self.assertEqual(decision_juego(juego, cazador), decision_oraculo(juego, cazador))

    def test_002_fr011_sin_cazadores_no_hay_calculos(self):
        """002/FR-011: una cripta sin cazadores no calcula rutas."""
        juego = CriptaPrueba(cuadricula(4, 1)).con_enemigo(6, "e-r", "ent_rata").juego()
        for _ in range(20):
            juego.ejecutar_accion(ESPERAR)
        self.assertEqual(juego.rutas.calculos, 0)


class PruebaSimulacion(unittest.TestCase):
    """002/FR-001, FR-002, SC-002: puertas que cambian, jugador que se mueve y cazadores que mueren."""

    def correr(self, estrategia, semilla, vigilar_decisiones=True):
        cripta = CriptaPrueba(cuadricula(6, semilla, costos=(20, 100, 100, 300), prob_puerta=0.6,
                                         prob_cerrada=0.3, cierre=250), inicial=1, vida=10**6)
        cripta.fichas.append(ficha_cazador(700, id="ent_caz_a"))
        cripta.fichas.append(ficha_cazador(2400, velocidad=130, id="ent_caz_b"))
        azar_pos = random.Random(semilla)
        ids = []
        for k in range(8):
            ids.append(f"e-{k}")
            cripta.con_enemigo(azar_pos.randint(2, 36), f"e-{k}", "ent_caz_a" if k % 2 else "ent_caz_b")
        juego = cripta.juego(semilla=semilla, estrategia=estrategia)
        activar(juego, *ids)
        contador = vigilar(self, juego) if vigilar_decisiones else [0]
        azar = random.Random(semilla * 7)
        puertas = juego.mapa.lista_puertas
        for paso in range(80):
            if juego.esta_terminada():
                break
            # Entre decisiones: algunas puertas cambian (como cierres automáticos o aperturas).
            for _ in range(azar.randint(0, 3)):
                if puertas:
                    puerta = puertas[azar.randrange(len(puertas))]
                    puerta.cerrada = not puerta.cerrada
            sala = juego.jugador.sala
            enemigos = juego.enemigos_en_sala()
            if enemigos and azar.random() < 0.7:
                juego.ejecutar_accion(Accion(TipoAccion.ATACAR, objetivo=enemigos[0].id))
                continue
            abiertas = [s for s in sala.salidas_transitables()]
            if abiertas and azar.random() < 0.75:
                juego.ejecutar_accion(mover(abiertas[azar.randrange(len(abiertas))].direccion))
            else:
                juego.ejecutar_accion(ESPERAR)
        return juego, contador[0]

    def test_002_sc002_todas_las_decisiones_iguales_al_oraculo(self):
        """002/FR-001, FR-002 (SC-002): reutilizar nunca da una decisión distinta a la de un cálculo desde cero."""
        total = 0
        for estrategia in EstrategiaCazador:
            for semilla in (1, 2, 3):
                with self.subTest(estrategia=estrategia.value, semilla=semilla):
                    _, decisiones = self.correr(estrategia, semilla)
                    total += decisiones
        self.assertGreater(total, 500)

    def test_ac_002_03_misma_partida_con_todas_las_estrategias(self):
        """AC-002-03 / 002/FR-007, FR-008: la partida es idéntica con y sin reutilización."""
        for semilla in (4, 5):
            estados = []
            calculos = []
            for estrategia in EstrategiaCazador:
                juego, _ = self.correr(estrategia, semilla, vigilar_decisiones=False)
                estados.append(juego.exportar_estado("x"))
                calculos.append(juego.rutas.calculos)
            for estado in estados[1:]:
                self.assertEqual(estado, estados[0])
            # COMPARTIDA (índice 0) reutiliza: hace menos cálculos que RECALCULAR_SIEMPRE (índice 2).
            self.assertLess(calculos[0], calculos[2])


if __name__ == "__main__":
    unittest.main()
