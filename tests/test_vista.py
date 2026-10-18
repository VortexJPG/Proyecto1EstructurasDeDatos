"""Pruebas de los controles de la consola (W/A/S/D, Q, E, R, F, T, I).

Las respuestas a los menús se simulan reemplazando la entrada de la vista; lo
que la vista imprime se descarta.
"""

import contextlib
import io
import unittest

from cripta.controlador.comandos import TipoComando
from cripta.modelo.acciones import Accion, TipoAccion
from cripta.vista.vista_consola import VistaConsola
from tests.test_modelo import crear_juego_prueba


class PruebaControles(unittest.TestCase):
    def setUp(self):
        self.juego, _ = crear_juego_prueba(vida=500)
        self.vista = VistaConsola()
        self.respuestas = []
        self.vista._entrada = lambda mensaje: self.respuestas.pop(0)

    def interpretar(self, texto, *respuestas):
        """Interpreta ``texto``; ``respuestas`` contesta los menús que aparezcan."""
        self.respuestas = list(respuestas)
        with contextlib.redirect_stdout(io.StringIO()):
            comando = self.vista._interpretar(texto, self.juego)
        self.assertEqual(self.respuestas, [], "sobraron respuestas: no apareció el menú esperado")
        return comando

    def accion(self, texto, *respuestas):
        comando = self.interpretar(texto, *respuestas)
        self.assertIsNotNone(comando, texto)
        self.assertIs(comando.tipo, TipoComando.ACCION)
        return comando.accion

    def jugar(self, tipo, direccion=None, objetivo=None):
        self.assertTrue(self.juego.ejecutar_accion(Accion(tipo, direccion, objetivo)).aceptada)

    def test_wasd_para_moverse(self):
        for tecla, direccion in (("w", "N"), ("a", "O"), ("s", "S"), ("d", "E"), ("W", "N"), ("D", "E")):
            accion = self.accion(tecla)
            self.assertIs(accion.tipo, TipoAccion.MOVER)
            self.assertEqual(accion.direccion, direccion, tecla)
        self.assertEqual(self.accion("mover norte").direccion, "N")

    def test_t_espera_e_inventario(self):
        self.assertIs(self.accion("t").tipo, TipoAccion.ESPERAR)
        self.assertIs(self.interpretar("i").tipo, TipoComando.VER_INVENTARIO)
        self.assertIs(self.interpretar("salir").tipo, TipoComando.SALIR)
        self.assertIsNone(self.interpretar("xyz"))

    def test_e_recoge_y_pregunta_si_hay_varios(self):
        # En la sala 1 hay 5 objetos en el suelo: E sin número pregunta cuál.
        self.assertEqual(self.accion("e", "3").objetivo, "o-1-2")
        self.assertEqual(self.accion("e 2").objetivo, "o-1-1")
        self.assertEqual(self.accion("e2").objetivo, "o-1-1")  # "e2" = "e 2"
        self.assertIsNone(self.interpretar("e", "0"))  # 0 = cancelar

    def test_q_ataca(self):
        self.assertIsNone(self.interpretar("q"))  # sala 1 sin enemigos
        self.jugar(TipoAccion.MOVER, direccion="N")  # sala 2: una araña
        accion = self.accion("q")
        self.assertIs(accion.tipo, TipoAccion.ATACAR)
        self.assertEqual(accion.objetivo, "a-1")

    def test_r_abre_puertas(self):
        self.assertIsNone(self.interpretar("r"))  # sala 1 sin puertas cerradas
        self.jugar(TipoAccion.MOVER, direccion="N")  # sala 2: puerta cerrada al norte
        accion = self.accion("r")
        self.assertIs(accion.tipo, TipoAccion.ABRIR)
        self.assertEqual(accion.direccion, "N")
        self.assertEqual(self.accion("r d").direccion, "E")
        self.assertIsNone(self.interpretar("r x"))

    def test_f_menu_segun_el_objeto(self):
        self.jugar(TipoAccion.MOVER, direccion="N")
        self.jugar(TipoAccion.RECOGER, objetivo="o-2-1")  # espada: Equipar / Soltar
        accion = self.accion("f", "1")
        self.assertIs(accion.tipo, TipoAccion.EQUIPAR)
        self.assertEqual(accion.objetivo, "o-2-1")
        self.assertIs(self.accion("f 1", "2").tipo, TipoAccion.SOLTAR)
        self.assertIsNone(self.interpretar("f", "0"))

    def test_f_con_pocion_y_pergamino(self):
        self.jugar(TipoAccion.RECOGER, objetivo="o-1-0")  # pergamino
        self.jugar(TipoAccion.RECOGER, objetivo="o-1-2")  # poción veloz
        self.assertIs(self.accion("f 1", "1").tipo, TipoAccion.RETROCEDER)  # pergamino: usar = retroceder
        accion = self.accion("f 2", "1")
        self.assertIs(accion.tipo, TipoAccion.USAR)
        self.assertEqual(accion.objetivo, "o-1-2")
        self.assertIsNone(self.interpretar("f 9"))  # no hay objeto 9


if __name__ == "__main__":
    unittest.main()
