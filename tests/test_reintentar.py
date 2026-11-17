"""Fin de partida con «Reintentar» / «Salir» (el programa no se cierra al ganar o morir).

- El controlador juega otra partida en la misma cripta si la vista lo pide.
- La consola pregunta [R] Reintentar / [S] Salir.
- La ventana tiene los botones Reintentar (izquierda) y Salir (derecha).
"""

import contextlib
import io
import os
import tempfile
import unittest

from cripta.adaptadores.fuente_offline import FuenteOffline
from cripta.controlador.comandos import ComandoUsuario, TipoComando
from cripta.controlador.controlador import Controlador, OpcionesEjecucion
from cripta.modelo.juego import EstadoPartida
from cripta.vista.base import VistaBase
from cripta.vista.vista_consola import VistaConsola

try:
    import pygame
except ImportError:
    pygame = None

DATOS_EJEMPLO = os.path.join(os.path.dirname(__file__), "..", "datos_ejemplo")


class _VistaQueMuere(VistaBase):
    """En cada partida el jugador "muere" en su primera decisión; reintenta según la lista dada."""

    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.juegos = []
        self.finales = 0

    def pedir_comando(self, juego):
        if juego not in self.juegos:
            self.juegos.append(juego)
        juego.estado = EstadoPartida.DERROTA  # como si un enemigo lo matara
        return ComandoUsuario(TipoComando.ACCION)  # sin acción: el controlador no hace nada

    def pedir_reintentar(self):
        return self.respuestas.pop(0)

    def mostrar_fin(self, juego, reporte):
        self.finales += 1

    def mostrar_info(self, texto):
        pass

    def mostrar_error(self, texto):
        pass

    def mostrar_estado(self, juego):
        pass

    def mostrar_resultado(self, resultado):
        pass


class PruebaControlador(unittest.TestCase):
    def jugar(self, respuestas):
        vista = _VistaQueMuere(respuestas)
        with tempfile.TemporaryDirectory() as carpeta:
            opciones = OpcionesEjecucion(directorio_datos=carpeta, cache_size=25, offline=DATOS_EJEMPLO,
                                         cripta_id="cripta-02", nombre_jugador="Ana", semilla=3)
            controlador = Controlador(FuenteOffline(DATOS_EJEMPLO), opciones, vista)
            with contextlib.redirect_stdout(io.StringIO()):
                codigo = controlador.ejecutar_interactivo()
            replays = os.listdir(os.path.join(carpeta, "replays"))
        return codigo, vista, controlador, replays

    def test_reintentar_juega_otra_partida_en_la_misma_cripta(self):
        """AC-006-01 / 006/FR-001, FR-002, FR-003, FR-004: otra partida en la misma cripta, desde cero."""
        codigo, vista, controlador, replays = self.jugar([True, False])
        self.assertEqual(codigo, 0)
        self.assertEqual(len(vista.juegos), 2)  # dos partidas distintas
        self.assertIsNot(vista.juegos[0], vista.juegos[1])
        self.assertEqual(vista.finales, 2)
        self.assertEqual(controlador.juego.datos.id, "cripta-02")
        self.assertEqual(vista.juegos[1].jugador.acciones_ejecutadas, 0)  # empezó de cero
        self.assertEqual(vista.juegos[1].jugador.sala.id, vista.juegos[1].mapa.sala_inicial.id)
        self.assertGreaterEqual(len(replays), 1)

    def test_salir_termina_el_programa(self):
        """AC-006-02 / 006/FR-005: Salir termina el programa."""
        codigo, vista, _, _ = self.jugar([False])
        self.assertEqual(codigo, 0)
        self.assertEqual(len(vista.juegos), 1)


class PruebaConsola(unittest.TestCase):
    def test_pregunta_reintentar_o_salir(self):
        """006/FR-008: la terminal pregunta [R] Reintentar / [S] Salir."""
        for entradas, esperado in ((["r"], True), (["s"], False), (["x", "R"], True), ([""], False)):
            vista = VistaConsola()
            respuestas = iter(entradas)
            vista._entrada = lambda mensaje="": next(respuestas)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(vista.pedir_reintentar(), esperado, entradas)


@unittest.skipIf(pygame is None, "pygame-ce no está instalado")
class PruebaVentana(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        from cripta.vista.vista_grafica import VistaGrafica
        from tests.test_modelo import crear_juego_prueba

        self.vista = VistaGrafica()
        self.vista.espera_fin_ms = 0
        self.juego, _ = crear_juego_prueba(vida=500)
        self.vista.mostrar_estado(self.juego)

    def tearDown(self):
        self.vista.cerrar()

    def elegir(self, *teclas, terminada=True):
        if terminada:
            self.juego.estado = EstadoPartida.DERROTA
        pygame.event.clear()
        for tecla in teclas:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=tecla, mod=0, unicode=""))
        with contextlib.redirect_stdout(io.StringIO()):
            self.vista.mostrar_fin(self.juego, "Solicitudes: 0/10")
        return self.vista.pedir_reintentar()

    def test_botones_reintentar_a_la_izquierda_y_salir_a_la_derecha(self):
        """AC-006-03 / 006/FR-007: Reintentar a la izquierda y Salir a la derecha, con el teclado."""
        self.assertTrue(self.elegir(pygame.K_RETURN))  # el botón marcado al empezar es Reintentar
        self.assertFalse(self.elegir(pygame.K_RIGHT, pygame.K_RETURN))  # derecha = Salir
        self.assertTrue(self.elegir(pygame.K_RIGHT, pygame.K_LEFT, pygame.K_RETURN))
        self.assertTrue(self.elegir(pygame.K_r))
        self.assertFalse(self.elegir(pygame.K_ESCAPE))
        self.vista._fin = (self.juego.resumen(), "")
        self.vista._fin_con_botones = True
        self.vista._mostrar_cuadro()  # al dibujar quedan guardadas las posiciones de los botones
        izquierda, derecha = self.vista._zonas_fin
        self.assertLess(izquierda.x, derecha.x)

    def test_clic_en_los_botones(self):
        """AC-006-03 / 006/FR-007: los botones también se eligen con un clic."""
        self.juego.estado = EstadoPartida.VICTORIA
        self.vista._fin = (self.juego.resumen(), "")
        self.vista._fin_con_botones = True
        self.vista._mostrar_cuadro()  # dibuja los botones y guarda dónde están
        izquierda, derecha = self.vista._zonas_fin
        for zona, esperado in ((izquierda, True), (derecha, False)):
            pygame.event.clear()
            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=zona.center))
            with contextlib.redirect_stdout(io.StringIO()):
                self.vista.mostrar_fin(self.juego, "")
            self.assertEqual(self.vista.pedir_reintentar(), esperado)

    def test_salir_a_mitad_de_partida_no_muestra_botones(self):
        """AC-006-04 / 006/FR-006: si se sale a mitad de partida no se ofrece reintentar."""
        self.assertFalse(self.elegir(pygame.K_SPACE, terminada=False))
        self.assertFalse(self.vista._fin_con_botones)


if __name__ == "__main__":
    unittest.main()
