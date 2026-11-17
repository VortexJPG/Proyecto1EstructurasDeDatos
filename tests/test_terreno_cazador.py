"""Spec 001 — Terreno y cazador (Persona A).

Cada prueba cita el requisito (``001/FR-xxx``) o el escenario del Apéndice B
(``AC-001-xx``) que ejercita. El oráculo "desde cero" está en ``apoyo_p2``.
"""

import random
import unittest

from cripta.bench.sinteticos import FichasEnMemoria
from cripta.modelo.acciones import Accion, TipoAccion
from cripta.modelo.actores import Comportamiento, Enemigo
from cripta.modelo.datos import DatosSala, Ficha
from cripta.modelo.mapa import Mapa
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


def linea(*costos, cerrada_en=None):
    """Salas 1..n en línea (E/O) con los costos dados entre sala i e i+1."""
    salas = []
    n = len(costos) + 1
    for i in range(1, n + 1):
        lista = []
        if i < n:
            lista.append(salida("E", i + 1, costos[i - 1], cerrada=(cerrada_en == i)))
        if i > 1:
            lista.append(salida("O", i - 1))
        salas.append((i, lista))
    return salas


class PruebaTerreno(unittest.TestCase):
    def test_001_fr001_costo_por_defecto_100(self):
        """001/FR-001: una salida sin costo declarado cuesta 100."""
        mapa = CriptaPrueba([(1, [salida("E", 2)]), (2, [salida("O", 1)])]).mapa()
        self.assertEqual(mapa.sala(1).salida("E").costo, 100)
        self.assertEqual(mapa.sala(2).salida("O").costo, 100)

    def test_001_fr002_costo_compartido_por_pasaje(self):
        """001/FR-002: si solo un sentido declara el costo, vale para los dos."""
        mapa = CriptaPrueba([(1, [salida("E", 2, 250)]), (2, [salida("O", 1)])]).mapa()
        self.assertEqual(mapa.sala(2).salida("O").costo, 250)

    def test_001_fr002_costos_distintos_gana_el_primero_del_esqueleto(self):
        """001/FR-002 (clarify): los dos sentidos declaran distinto ⇒ vale el primero en el orden del esqueleto."""
        mapa = CriptaPrueba([(1, [salida("E", 2, 30)]), (2, [salida("O", 1, 70)])]).mapa()
        self.assertEqual(mapa.sala(1).salida("E").costo, 30)
        self.assertEqual(mapa.sala(2).salida("O").costo, 30)

    def test_001_fr002_puerta_y_costo_en_lados_distintos(self):
        """001/FR-002: el regreso de una salida con puerta es la que comparte la puerta."""
        mapa = CriptaPrueba([(1, [salida("E", 2, cerrada=True)]), (2, [salida("O", 1, 180)])]).mapa()
        self.assertIs(mapa.sala(1).salida("E").puerta, mapa.sala(2).salida("O").puerta)
        self.assertEqual(mapa.sala(1).salida("E").costo, 180)

    def test_001_fr003_costo_invalido_es_error(self):
        """001/FR-003: costo 0 o negativo ⇒ esqueleto inválido con sala y dirección."""
        for malo in (0, -5):
            with self.subTest(costo=malo):
                with self.assertRaises(ValueError) as ctx:
                    CriptaPrueba([(1, [salida("E", 2, malo)]), (2, [salida("O", 1)])]).mapa()
                self.assertIn("sala 1", str(ctx.exception))
                self.assertIn("E", str(ctx.exception))

    def test_001_fr004_jugador_cruza_salida_de_costo_250(self):
        """001/FR-004 (escenario US1-1): costo 250 y velocidad 100 ⇒ siguiente turno en t=250."""
        juego = CriptaPrueba(linea(250)).juego()
        self.assertEqual(juego.reloj, 0)
        self.assertTrue(juego.ejecutar_accion(mover("E")).aceptada)
        self.assertEqual(juego.jugador.sala.id, 2)
        self.assertEqual(juego.reloj, 250)

    def test_001_fr006_otras_acciones_no_cambian(self):
        """001/FR-006: esperar sigue costando 100 aunque las salidas sean caras."""
        juego = CriptaPrueba(linea(900)).juego()
        juego.ejecutar_accion(ESPERAR)
        self.assertEqual(juego.reloj, 100)

    def test_001_fr005_errante_tarda_el_costo_de_la_salida(self):
        """001/FR-005: un errante decide igual que en la Parte I y tarda el costo de la salida."""
        cripta = CriptaPrueba(linea(300, 100)).con_enemigo(1, "e-err", "ent_errante")
        juego = cripta.juego()
        errante = juego.enemigos.obtener("e-err")
        juego.ejecutar_accion(mover("E"))  # el jugador se va a la sala 2 (t=0 → 300)
        # El errante actuó en t=100: única salida abierta (E, costo 300) ⇒ próximo turno en 400.
        self.assertEqual(errante.sala.id, 2)
        self.assertEqual(errante.tiempo_siguiente, 400)

    def test_001_fr005_rastreador_tarda_el_costo_de_la_salida(self):
        """001/FR-005: el rastreador sigue el rastro como en la Parte I; tarda el costo de la salida."""
        cripta = CriptaPrueba(linea(300, 100)).con_enemigo(1, "e-ras", "ent_rastreador")
        juego = cripta.juego()
        rastreador = juego.enemigos.obtener("e-ras")
        juego.ejecutar_accion(mover("E"))
        self.assertEqual(rastreador.sala.id, 2)
        self.assertEqual(rastreador.tiempo_siguiente, 400)

    def test_ac_001_05_velocidad_alta_y_costo_1_da_intervalo_1(self):
        """AC-001-05 / 001/FR-004: velocidad 200 cruzando una salida de costo 1 ⇒ intervalo 1 (nunca 0)."""
        juego = CriptaPrueba(linea(1), velocidad=200).juego()
        juego.ejecutar_accion(mover("E"))
        self.assertEqual(juego.reloj, 1)

    def test_ac_001_06_cambio_de_velocidad_escala_el_restante(self):
        """AC-001-06 / 001/FR-007: el tiempo restante de un movimiento costoso se escala (P1 §2.3)."""
        cripta = CriptaPrueba(linea(300, 100)).con_enemigo(1, "e-err", "ent_errante")
        juego = cripta.juego()
        errante = juego.enemigos.obtener("e-err")
        juego.ejecutar_accion(mover("E"))  # errante cruza costo 300 en t=100 ⇒ turno en 400; reloj = 300
        self.assertEqual((juego.reloj, errante.tiempo_siguiente), (300, 400))
        juego.efectos.aplicar_velocidad(errante, 100, 10_000)  # velocidad 100 → 200 en t=300
        # restante = (400 - 300) * 100 // 200 = 50 ⇒ turno en 350
        self.assertEqual(errante.tiempo_siguiente, 350)


class PruebaFichaCazador(unittest.TestCase):
    def _sala(self):
        return Mapa.construir(CriptaPrueba([(1, [])]).datos, [DatosSala(1, "Sala 1", [])]).sala(1)

    def test_001_fr008_cazador_con_rango(self):
        """001/FR-008: el cazador copia su rango de la ficha."""
        enemigo = Enemigo("e-1", ficha_cazador(rango=600), None, 0, self._sala())
        self.assertIs(enemigo.comportamiento, Comportamiento.CAZADOR)
        self.assertEqual(enemigo.rango, 600)

    def test_001_fr008_cazador_sin_rango_es_ficha_invalida(self):
        """001/FR-008: sin rango o con rango < 1 ⇒ error, no se inventa un rango."""
        for rango in (None, 0, -3):
            with self.subTest(rango=rango):
                ficha = Ficha("ent_c", "enemigo", "C", vida_max=5, comportamiento="cazador", rango=rango)
                with self.assertRaises(ValueError):
                    Enemigo("e-1", ficha, None, 0, self._sala())


class PruebaCazador(unittest.TestCase):
    def juego_con_cazador(self, salas, sala_cazador, rango=600, inicial=1, velocidad=100, estrategia=None):
        cripta = CriptaPrueba(salas, inicial=inicial).con_enemigo(
            sala_cazador, "e-caz", "ent_cazador", ficha_cazador(rango, velocidad))
        juego = cripta.juego(estrategia=estrategia or EstrategiaCazador.COMPARTIDA)
        activar(juego, "e-caz")
        return juego, juego.enemigos.obtener("e-caz")

    def test_ac_001_01_sin_ruta_abierta_espera_100(self):
        """AC-001-01 / 001/FR-011: sin ruta abierta hacia el jugador, el cazador espera con costo 100."""
        juego, cazador = self.juego_con_cazador(linea(100, 100, cerrada_en=1), 3)
        self.assertEqual(decision_juego(juego, cazador), ("esperar", None, None))
        primer_turno = cazador.tiempo_siguiente
        while juego.reloj < primer_turno:
            juego.ejecutar_accion(ESPERAR)
        self.assertEqual(cazador.sala.id, 3)
        self.assertEqual(cazador.tiempo_siguiente, primer_turno + 100)

    def test_ac_001_02_ruta_mas_cara_que_el_rango_espera(self):
        """AC-001-02 / 001/FR-011: d = 400 > rango 300 ⇒ espera 100."""
        juego, cazador = self.juego_con_cazador(linea(200, 200), 3, rango=300)
        self.assertEqual(decision_juego(juego, cazador), ("esperar", None, None))

    def test_001_fr012_ruta_igual_al_rango_se_mueve(self):
        """001/FR-012 (clarify): d == rango ⇒ se mueve."""
        juego, cazador = self.juego_con_cazador(linea(200, 200), 3, rango=400)
        self.assertEqual(decision_juego(juego, cazador), ("mover", 2, "O"))

    def test_ac_001_03_menos_salas_pero_mas_caro(self):
        """AC-001-03 / 001/FR-010: 1→2→5 cuesta 1000 (2 salidas); 1→3→4→5 cuesta 300 (3) ⇒ va a 3."""
        salas = [
            (1, [salida("N", 2, 500), salida("E", 3, 100)]),
            (2, [salida("S", 1), salida("E", 5, 500)]),
            (3, [salida("O", 1), salida("E", 4, 100)]),
            (4, [salida("O", 3), salida("N", 5, 100)]),
            (5, [salida("O", 2), salida("S", 4)]),
        ]
        juego, cazador = self.juego_con_cazador(salas, 1, inicial=5)
        self.assertEqual(decision_juego(juego, cazador), ("mover", 3, "E"))

    def test_ac_001_04_empate_va_a_la_vecina_de_menor_id(self):
        """AC-001-04 / 001/FR-013: dos vecinas empatadas (7 por N y 4 por E) ⇒ va a la 4 aunque N va primero."""
        salas = [
            (1, [salida("N", 7, 100), salida("E", 4, 100)]),
            (4, [salida("O", 1), salida("N", 9, 100)]),
            (7, [salida("S", 1), salida("E", 9, 100)]),
            (9, [salida("S", 4), salida("O", 7)]),
        ]
        juego, cazador = self.juego_con_cazador(salas, 1, inicial=9)
        self.assertEqual(decision_juego(juego, cazador), ("mover", 4, "E"))

    def test_001_fr013_misma_vecina_por_dos_salidas(self):
        """001/FR-013: dos salidas hacia la misma vecina que empiezan ruta mínima ⇒ la primera en N, S, E, O."""
        salas = [
            (1, [salida("N", 2, 100), salida("E", 2, 100)]),
            (2, [salida("S", 1), salida("O", 1)]),
        ]
        juego, cazador = self.juego_con_cazador(salas, 1, inicial=2)
        self.assertEqual(decision_juego(juego, cazador), ("mover", 2, "N"))
        salas[0] = (1, [salida("N", 2, 150), salida("E", 2, 100)])
        juego, cazador = self.juego_con_cazador(salas, 1, inicial=2)
        self.assertEqual(decision_juego(juego, cazador), ("mover", 2, "E"))

    def test_001_fr009_ataca_si_comparte_sala(self):
        """001/FR-009: en la misma sala que el jugador, ataca y no se mueve."""
        juego, cazador = self.juego_con_cazador(linea(100), 1)
        vida = juego.jugador.vida
        while juego.jugador.vida == vida:
            juego.ejecutar_accion(ESPERAR)
        self.assertEqual(cazador.sala.id, 1)

    def test_001_fr012_un_paso_con_el_costo_de_la_salida(self):
        """001/FR-012: avanza UNA sala y la acción cuesta el costo de la salida cruzada (250)."""
        juego, cazador = self.juego_con_cazador(linea(100, 250), 3)
        turno = cazador.tiempo_siguiente
        while juego.reloj < turno:
            juego.ejecutar_accion(ESPERAR)
        self.assertEqual(cazador.sala.id, 2)
        self.assertEqual(cazador.tiempo_siguiente, turno + 250)

    def test_001_fr014_no_depende_del_contenido_ni_de_la_niebla(self):
        """001/FR-014: la decisión es la misma sin el contenido de las salas y sin conocimiento del jugador."""
        salas = cuadricula(6, semilla=3, costos=(20, 100, 300))
        cripta = CriptaPrueba(salas, inicial=36).con_enemigo(1, "e-caz", "ent_cazador", ficha_cazador(5000))
        completo = cripta.juego()
        activar(completo, "e-caz")
        esperado = decision_juego(completo, completo.enemigos.obtener("e-caz"))
        # Mapa con contenido SOLO de las salas del cazador y del jugador.
        mapa = Mapa.construir(cripta.datos, cripta.esqueleto)
        proveedor = FichasEnMemoria(cripta.fichas)
        for contenido in cripta.contenido():
            if contenido.sala in (1, 36):
                mapa.incorporar_contenido(contenido, proveedor)
        from cripta.modelo.juego import Juego
        parcial = Juego(cripta.datos, mapa, proveedor, 1, "P")
        parcial.iniciar()
        activar(parcial, "e-caz")
        for i in range(len(parcial.conocimiento.estado_sala)):
            parcial.conocimiento.estado_sala[i] = 0  # el cazador no usa la niebla
        self.assertEqual(decision_juego(parcial, parcial.enemigos.obtener("e-caz")), esperado)

    def test_001_fr016_cazador_dormido_no_actua(self):
        """001/FR-016: un cazador sin activar no se mueve."""
        cripta = CriptaPrueba(linea(100, 100)).con_enemigo(3, "e-caz", "ent_cazador", ficha_cazador())
        juego = cripta.juego()
        for _ in range(10):
            juego.ejecutar_accion(ESPERAR)
        cazador = juego.enemigos.obtener("e-caz")
        self.assertFalse(cazador.activo)
        self.assertEqual(cazador.sala.id, 3)
        self.assertEqual(juego.rutas.calculos, 0)

    def test_001_fr017_la_decision_no_consume_el_azar(self):
        """001/FR-017: decidir no toca el generador aleatorio de la partida."""
        juego, cazador = self.juego_con_cazador(cuadricula(5, 2, costos=(50, 100)), 1, inicial=25, rango=5000)
        antes = juego.azar.getstate()
        juego.rutas.decidir(cazador, juego.jugador.sala)
        self.assertEqual(juego.azar.getstate(), antes)

    def test_001_sc005_dos_corridas_misma_partida(self):
        """001/SC-005 y FR-017: misma cripta, semilla y acciones ⇒ mismo estado final."""
        def correr():
            cripta = CriptaPrueba(cuadricula(5, 4, costos=(20, 100, 300)), inicial=13)
            for k, sala in enumerate((1, 5, 21, 25)):
                cripta.con_enemigo(sala, f"e-c{k}", "ent_cazador")
            cripta.fichas.append(ficha_cazador(800))
            juego = cripta.juego(semilla=9)
            activar(juego, "e-c0", "e-c1", "e-c2", "e-c3")
            azar = random.Random(5)
            for _ in range(40):
                if juego.esta_terminada():
                    break
                abiertas = [s for s in juego.jugador.sala.salidas_transitables()]
                juego.ejecutar_accion(mover(abiertas[azar.randrange(len(abiertas))].direccion))
            return juego.exportar_estado("x")
        self.assertEqual(correr(), correr())


class PruebaSinDatosDeCripta(unittest.TestCase):
    def test_001_fr018_el_codigo_no_tiene_datos_de_criptas_concretas(self):
        """001/FR-018 (constitución IV): ningún id real de cripta, instancia o ficha escrito en ``cripta/``.

        Los ids se leen de los paquetes offline (``datos_ejemplo*``) y se buscan
        como literales de texto en el código del programa (sin contar docstrings).
        """
        import ast
        import glob
        import json
        import os

        raiz = os.path.join(os.path.dirname(__file__), "..")
        prohibidos = set()
        for archivo in glob.glob(os.path.join(raiz, "datos_ejemplo*", "**", "*.json"), recursive=True):
            with open(archivo, encoding="utf-8") as f:
                datos = json.load(f)
            nombre = os.path.basename(archivo)
            if nombre == "cripta.json":
                prohibidos.add(datos["id"])
            elif nombre.startswith("contenido"):
                for sala in datos["contenido"]:
                    for enemigo in sala["enemigos"]:
                        prohibidos.add(enemigo["instancia"])
                        prohibidos.add(enemigo["tipo"])
                    for trampa in sala.get("trampas", []):
                        prohibidos.add(trampa["instancia"])
                    prohibidos.update(sala["objetos"])
            elif nombre.startswith("catalogo_lote"):
                for ficha in datos["entidades"]:
                    prohibidos.add(ficha["id"])
        self.assertGreater(len(prohibidos), 20)
        encontrados = []
        for archivo in glob.glob(os.path.join(raiz, "cripta", "**", "*.py"), recursive=True):
            with open(archivo, encoding="utf-8") as f:
                arbol = ast.parse(f.read())
            docstrings = set()
            for nodo in ast.walk(arbol):
                if isinstance(nodo, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and nodo.body:
                    primero = nodo.body[0]
                    if isinstance(primero, ast.Expr) and isinstance(primero.value, ast.Constant):
                        docstrings.add(id(primero.value))
            for nodo in ast.walk(arbol):
                if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str) and id(nodo) not in docstrings:
                    if nodo.value in prohibidos:
                        encontrados.append(f"{os.path.relpath(archivo, raiz)}:{nodo.lineno} {nodo.value!r}")
        self.assertEqual(encontrados, [])


class PruebaVista(unittest.TestCase):
    def test_001_fr019_fr020_consola_muestra_costos_y_marca_cazadores(self):
        """001/FR-019, FR-020 (escenarios US5-1 y US5-2): costos de las salidas y cazador marcado."""
        import io
        from contextlib import redirect_stdout
        from cripta.vista.vista_consola import VistaConsola

        salas = [(1, [salida("N", 2, 20), salida("E", 3, 300)]), (2, [salida("S", 1)]), (3, [salida("O", 1)])]
        cripta = CriptaPrueba(salas).con_enemigo(1, "e-caz", "ent_cazador", ficha_cazador(600))
        cripta.con_enemigo(1, "e-rata", "ent_rata")
        juego = cripta.juego()
        texto = io.StringIO()
        with redirect_stdout(texto):
            VistaConsola().mostrar_estado(juego)
        salida_consola = texto.getvalue()
        self.assertIn("costo 20", salida_consola)
        self.assertIn("costo 300", salida_consola)
        self.assertIn("[cazador, rango 600]", salida_consola)
        self.assertEqual(salida_consola.count("[cazador"), 1)  # la rata no lleva la marca


class PruebaOraculo(unittest.TestCase):
    """001/SC-002, FR-013, FR-015: cientos de situaciones contra el cálculo desde cero."""

    def test_001_sc002_decisiones_iguales_al_oraculo(self):
        """001/FR-013, FR-015 (SC-002): cada decisión coincide con el cálculo desde cero, en todas las estrategias."""
        azar = random.Random(2026)
        situaciones = 0
        for caso in range(60):
            lado = azar.choice((3, 4, 5, 6))
            costos = azar.choice(((100,), (100, 100, 200), (1, 20, 100, 300), (50, 60)))
            salas = cuadricula(lado, semilla=caso, costos=costos, prob_puerta=0.4, prob_cerrada=0.5)
            total = lado * lado
            jugador = azar.randint(1, total)
            cripta = CriptaPrueba(salas, inicial=jugador)
            posiciones = [azar.randint(1, total) for _ in range(5)]
            rangos = [azar.choice((50, 150, 300, 600, 100_000)) for _ in range(5)]
            for k in range(5):
                cripta.con_enemigo(posiciones[k], f"e-{k}", f"ent_caz_{k}", ficha_cazador(rangos[k], id=f"ent_caz_{k}"))
            for estrategia in EstrategiaCazador:
                juego = cripta.juego(estrategia=estrategia)
                activar(juego, *[f"e-{k}" for k in range(5)])
                for k in range(5):
                    cazador = juego.enemigos.obtener(f"e-{k}")
                    with self.subTest(caso=caso, estrategia=estrategia.value, cazador=k):
                        self.assertEqual(decision_juego(juego, cazador), decision_oraculo(juego, cazador))
                    situaciones += 1
        self.assertGreaterEqual(situaciones, 1000)


if __name__ == "__main__":
    unittest.main()
