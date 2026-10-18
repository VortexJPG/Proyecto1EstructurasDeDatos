"""Pruebas de la ventana (--gui) y de los sprites.

Los sprites son solo datos: se prueban siempre. La ventana se prueba con el
"driver" de video ``dummy`` de SDL (no abre nada en la pantalla), simulando
las teclas con ``pygame.event.post``. Si pygame-ce no está instalado, esas
pruebas se saltan.
"""

import contextlib
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from cripta.controlador.aplicacion import main
from cripta.controlador.comandos import TipoComando
from cripta.modelo.acciones import TipoAccion
from cripta.vista import sprites

try:
    import pygame
except ImportError:
    pygame = None

DATOS_EJEMPLO = os.path.join(os.path.dirname(__file__), "..", "datos_ejemplo")


def _nombres(lista):
    return [nombre for nombre, _ in lista]


class PruebaSprites(unittest.TestCase):
    def test_tamano_y_colores(self):
        for lista, lado in ((sprites.SPRITES, sprites.TAMANO), (sprites.ICONOS, sprites.TAMANO_ICONO)):
            for nombre, filas in lista:
                self.assertEqual(len(filas), lado, nombre)
                for fila in filas:
                    self.assertEqual(len(fila), lado, f"{nombre}: {fila!r}")
                    for caracter in fila:
                        sprites.color_de(caracter)  # ValueError si no está en la paleta

    def test_nombres_sin_repetir(self):
        for lista in (sprites.SPRITES, sprites.ICONOS):
            nombres = _nombres(lista)
            for nombre in nombres:
                self.assertEqual(nombres.count(nombre), 1, nombre)

    def test_sprite_segun_la_ficha(self):
        casos = (
            (sprites.sprite_enemigo("ent_rata_gigante", "Rata gigante"), "rata"),
            (sprites.sprite_enemigo("ent_guardian_oseo", "Guardián óseo"), "esqueleto"),
            (sprites.sprite_enemigo("ent_arana", "Araña"), "arana"),
            (sprites.sprite_enemigo("ent_x", "Cosa desconocida"), "limo"),
            (sprites.sprite_objeto("arma", "itm_daga_oxidada", "Daga oxidada"), "daga"),
            (sprites.sprite_objeto("arma", "itm_espada", "Espada"), "espada"),
            # "arma" está dentro de "armadura": la clase se compara completa.
            (sprites.sprite_objeto("armadura", "itm_coraza_cuero", "Coraza de cuero"), "coraza"),
            (sprites.sprite_objeto("armadura", "itm_escudo", "Escudo"), "escudo"),
            (sprites.sprite_objeto("llave", "itm_llave_negra", "Llave negra"), "llave_negra"),
            (sprites.sprite_objeto("llave", "itm_llave_bronce", "Llave de bronce"), "llave_bronce"),
            (sprites.sprite_objeto("pocion", "itm_pocion_menor", "Poción menor"), "pocion"),
            (sprites.sprite_objeto("pocion", "itm_pocion_vel", "Poción veloz", True), "pocion_veloz"),
            (sprites.sprite_objeto("pergamino_retroceso", "itm_pergamino", "Pergamino"), "pergamino"),
            (sprites.sprite_objeto("clase_nueva", "itm_x", "Algo"), "pocion"),
            (sprites.sprite_trampa("trp_dardos", "Dardos en la pared"), "dardos"),
            (sprites.sprite_trampa("trp_pinchos", "Pinchos"), "pinchos"),
        )
        existentes = _nombres(sprites.SPRITES)
        for obtenido, esperado in casos:
            self.assertEqual(obtenido, esperado)
            self.assertIn(obtenido, existentes)

    def test_recolorear_cambia_cada_pixel_una_vez(self):
        self.assertEqual(sprites.recolorear(["RrO."], "RU ru"), ["UuO."])
        self.assertEqual(sprites.recolorear(["yO"], "Oo yO"), ["Oo"])


class PruebaSinPygame(unittest.TestCase):
    def test_gui_sin_pygame_da_un_mensaje_claro(self):
        errores = io.StringIO()
        with mock.patch.dict(sys.modules, {"pygame": None}):
            sys.modules.pop("cripta.vista.vista_grafica", None)
            with contextlib.redirect_stderr(errores):
                codigo = main(["--gui", "--offline", DATOS_EJEMPLO])
        self.assertEqual(codigo, 1)
        self.assertIn("pip install -r requirements.txt", errores.getvalue())


@unittest.skipIf(pygame is None, "pygame-ce no está instalado")
class PruebaVentana(unittest.TestCase):
    def setUp(self):
        from cripta.vista.vista_grafica import VistaGrafica
        from tests.test_modelo import crear_juego_prueba

        self.vista = VistaGrafica()
        self.vista._ayuda_mostrada = True  # que la primera tecla no sea para cerrar la ayuda
        self.vista.espera_fin_ms = 0
        self.juego, _ = crear_juego_prueba(vida=500)
        self.vista.mostrar_estado(self.juego)

    def tearDown(self):
        self.vista.cerrar()

    @staticmethod
    def teclas(*teclas):
        for tecla in teclas:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=tecla))

    def comando(self, *teclas):
        self.teclas(*teclas)
        return self.vista.pedir_comando(self.juego)

    def jugar(self, comando):
        self.assertIs(comando.tipo, TipoComando.ACCION)
        self.assertTrue(self.juego.ejecutar_accion(comando.accion).aceptada)
        self.vista.mostrar_estado(self.juego)

    def test_teclas(self):
        self.assertIs(self.comando(pygame.K_t).accion.tipo, TipoAccion.ESPERAR)
        accion = self.comando(pygame.K_w).accion
        self.assertIs(accion.tipo, TipoAccion.MOVER)
        self.assertEqual(accion.direccion, "N")
        self.assertEqual(self.comando(pygame.K_a).accion.direccion, "O")
        self.assertIs(self.comando(pygame.K_z).accion.tipo, TipoAccion.RETROCEDER)
        self.assertIs(self.comando(pygame.K_UP).tipo, TipoComando.INVENTARIO_ANTERIOR)
        self.assertIs(self.comando(pygame.K_F5).tipo, TipoComando.GUARDAR)
        ordenar = self.comando(pygame.K_i)
        self.assertIs(ordenar.tipo, TipoComando.VISTA_ORDENADA)
        self.assertEqual(ordenar.argumento, "peso")

    def test_menu_con_numero_flechas_y_cancelar(self):
        # En la sala 1 hay 5 objetos: E abre el menú (igual que en la consola).
        self.assertEqual(self.comando(pygame.K_e, pygame.K_3).accion.objetivo, "o-1-2")
        self.assertEqual(self.comando(pygame.K_e, pygame.K_DOWN, pygame.K_DOWN, pygame.K_RETURN).accion.objetivo,
                         "o-1-2")
        # Esc cancela el menú; la tecla siguiente ya es otro comando.
        self.assertIs(self.comando(pygame.K_e, pygame.K_ESCAPE, pygame.K_t).accion.tipo, TipoAccion.ESPERAR)

    def test_cerrar_la_ventana_es_salir(self):
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.assertIs(self.vista.pedir_comando(self.juego).tipo, TipoComando.SALIR)

    def test_dibuja_todo_sin_errores(self):
        from cripta.adaptadores.puntajes import RegistroPuntaje

        self.vista._mostrar_cuadro()
        self.jugar(self.comando(pygame.K_w))  # sala 2: araña, trampa, llave y espada
        self.vista._mostrar_cuadro()
        self.jugar(self.comando(pygame.K_s))
        self.jugar(self.comando(pygame.K_d))  # sala 3: dos lobos
        self.vista.mostrar_error("Un aviso de error")
        self.vista.mostrar_ayuda()
        self.vista._mostrar_cuadro()
        self.vista.mostrar_puntajes([RegistroPuntaje("Ana", "prueba", "v1", 10, 2, 900, "victoria")])
        self.vista._mostrar_cuadro()
        self.vista._capa = None
        self.vista._fin = (self.juego.resumen(), "Solicitudes: 1/9")
        self.vista._mostrar_cuadro()

    def test_bitacora_completa_muestra_los_20_mensajes(self):
        from cripta.vista import vista_grafica

        self.jugar(self.comando(pygame.K_w))  # sala 2: la araña ataca y hay mensajes en cada turno
        while self.juego.mensajes.total < 30:
            self.jugar(self.comando(pygame.K_t))
        self.assertEqual(len(self.juego.mensajes), 20)
        # En la capa de la bitácora caben los 20 mensajes con sus encabezados de turno.
        self.vista._capa = "bitacora"
        self.vista._mostrar_cuadro()
        renglones = self.vista._renglones_bitacora(self.juego, self.vista._fuente, vista_grafica.ANCHO - 120)
        mensajes = [texto for texto, _ in renglones if texto.startswith("[t=")]
        self.assertEqual(len(mensajes), 20)
        caben = (vista_grafica.ALTO - 48 - 90) // 17
        self.assertLessEqual(len(renglones), caben)
        self.vista._capa = None
        # L solo abre la capa (no es un comando del juego); Espacio la cierra y T sí es un comando.
        self.assertIs(self.comando(pygame.K_l, pygame.K_SPACE, pygame.K_t).accion.tipo, TipoAccion.ESPERAR)

    def test_numero_de_dano_al_entrar_a_una_trampa(self):
        self.jugar(self.comando(pygame.K_w))  # sala 2: pinchos armados
        textos = [flotante.texto for flotante in self.vista._flotantes]
        self.assertTrue(any(texto.startswith("-") for texto in textos), textos)

    def test_no_consulta_la_cache_en_cada_cuadro(self):
        # Consultar fichas en cada cuadro inflaría las estadísticas de la caché
        # y movería el orden de la LRU: la ventana las consulta una vez por tipo.
        consultas = []
        obtener = self.juego.fichas.obtener
        self.juego.fichas.obtener = lambda tipo_id: consultas.append(tipo_id) or obtener(tipo_id)
        self.vista._mostrar_cuadro()
        primeras = len(consultas)
        for _ in range(10):
            self.vista._mostrar_cuadro()
        self.assertEqual(len(consultas), primeras)

    def test_partida_con_el_controlador(self):
        from cripta.adaptadores.fuente_offline import FuenteOffline
        from cripta.controlador.controlador import Controlador, OpcionesEjecucion

        self.vista._ayuda_mostrada = False  # como en una partida de verdad
        with tempfile.TemporaryDirectory() as carpeta:
            opciones = OpcionesEjecucion(directorio_datos=carpeta, cache_size=25, offline=DATOS_EJEMPLO, semilla=7)
            controlador = Controlador(FuenteOffline(DATOS_EJEMPLO), opciones, self.vista)
            self.teclas(pygame.K_1)  # cripta-01 en la lista
            pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text="Ana"))
            self.teclas(
                pygame.K_RETURN,  # nombre
                pygame.K_SPACE,  # cierra la ayuda del inicio
                pygame.K_w,  # al norte
                pygame.K_ESCAPE, pygame.K_RETURN,  # "¿Salir?" → "Sí, salir"
                pygame.K_SPACE,  # cierra la pantalla final
            )
            with contextlib.redirect_stdout(io.StringIO()):
                controlador.ejecutar_interactivo()
            juego = controlador.juego
            self.assertEqual(juego.jugador.nombre, "Ana")
            self.assertEqual(juego.datos.id, "cripta-01")
            self.assertEqual(juego.jugador.sala.id, 2)
            self.assertEqual(juego.jugador.acciones_ejecutadas, 1)
            self.assertTrue(os.listdir(os.path.join(carpeta, "replays")))


if __name__ == "__main__":
    unittest.main()
