"""Pruebas de la línea de tiempo: checkpoints, reconstrucción y recorte.

Base de la spec 005 (T003..T015). Los escenarios completos del Apéndice B se
añaden en las fases siguientes.
"""

import json
import os
import shutil
import struct
import tempfile
import unittest
from unittest import mock

from cripta.adaptadores.fuente_offline import FuenteOffline
from cripta.adaptadores.guardado import GuardadoBinario, GuardadoJSON, ErrorFormatoIncompatible
from cripta.bench.bot import jugar
from cripta.controlador.aplicacion import main
from cripta.controlador.comandos import ComandoUsuario, TipoComando
from cripta.controlador.controlador import Controlador, OpcionesEjecucion
from cripta.modelo.acciones import Accion, TipoAccion
from cripta.vista.vista_consola import VistaConsola

DATOS_EJEMPLO = os.path.join(os.path.dirname(__file__), "..", "datos_ejemplo")


class BaseTimeline(unittest.TestCase):
    def setUp(self):
        self.directorio = tempfile.mkdtemp(prefix="cripta_tl_")

    def tearDown(self):
        shutil.rmtree(self.directorio, ignore_errors=True)

    def controlador(self, k=4, sub="a", cripta="cripta-02", semilla=3, vida=None, replay=False):
        controlador = Controlador(
            FuenteOffline(DATOS_EJEMPLO),
            OpcionesEjecucion(
                directorio_datos=os.path.join(self.directorio, sub),
                cache_size=25,
                checkpoint_cada=k,
            ),
            None,
        )
        controlador.preparar_cripta(cripta)
        if vida is not None:
            controlador._datos.jugador.vida_max = vida
        controlador.iniciar_partida("Tl", semilla, registrar_replay=replay)
        return controlador


class PruebaLineaBase(BaseTimeline):
    def test_checkpoints_cada_k_y_acciones(self):
        controlador = self.controlador(k=4)
        jugar(controlador, 10, 3)
        linea = controlador._timeline
        self.assertEqual([p.indice_accion for p in linea.checkpoints], [0, 4, 8])
        self.assertEqual(len(linea.acciones), controlador.juego.jugador.acciones_ejecutadas)
        self.assertEqual(linea.acciones[0].indice, 1)

    def test_reconstruccion_coincide_con_el_oraculo(self):
        controlador = self.controlador(k=3)
        jugar(controlador, 12, 3)
        linea = controlador._timeline
        for k in range(0, len(linea.acciones) + 1):
            reconstruido = linea.resumen(linea.estado_en_accion(k), f"#{k + 1}")
            oraculo = self.controlador(k=3, sub=f"o{k}")
            for accion in linea.acciones[:k]:
                oraculo.ejecutar_accion(accion.accion)
            esperado = linea.resumen(oraculo.juego, f"#{k + 1}")
            self.assertEqual(reconstruido, esperado, f"acción {k}")
            oraculo.cerrar_recursos()

    def test_estado_en_accion_fuera_de_rango(self):
        controlador = self.controlador()
        jugar(controlador, 3, 3)
        with self.assertRaises(ValueError):
            controlador._timeline.estado_en_accion(99)

    def test_recorte_por_pergamino(self):
        controlador = self.controlador(k=2, sub="p", cripta="cripta-01", vida=500)
        acciones = [
            Accion(TipoAccion.RECOGER, objetivo="o-1-0"),
            Accion(TipoAccion.MOVER, direccion="N"),
            Accion(TipoAccion.MOVER, direccion="N"),
            Accion(TipoAccion.RECOGER, objetivo="o-3-0"),
            Accion(TipoAccion.MOVER, direccion="S"),
            Accion(TipoAccion.ABRIR, direccion="E"),
            Accion(TipoAccion.MOVER, direccion="E"),
            Accion(TipoAccion.RECOGER, objetivo="o-5-0"),
            Accion(TipoAccion.ESPERAR),
        ]
        for accion in acciones:
            self.assertTrue(controlador.ejecutar_accion(accion).aceptada, accion)
        linea = controlador._timeline
        self.assertEqual(len(linea.acciones), 9)
        self.assertTrue(controlador.ejecutar_accion(Accion(TipoAccion.RETROCEDER)).aceptada)
        self.assertEqual(len(linea.acciones), controlador.juego.jugador.acciones_ejecutadas)
        self.assertEqual(len(linea.acciones), 8)
        self.assertTrue(all(p.indice_accion <= 8 for p in linea.checkpoints))
        self.assertEqual(linea.estado_en_accion(8).jugador.acciones_ejecutadas, 8)

    def test_k_invalido_en_cli(self):
        self.assertEqual(main(["--checkpoint-cada", "0", "--bench"]), 1)


class PruebaPersistenciaLinea(BaseTimeline):
    def test_guardar_y_cargar_conserva_la_linea(self):
        controlador = self.controlador(k=4)
        jugar(controlador, 10, 3)
        ruta = os.path.join(self.directorio, "partida.sav")
        controlador.guardar_partida(ruta)
        antes = controlador._timeline.resumen(controlador._timeline.estado_en_accion(5), "#6")
        controlador.cargar_partida(ruta)
        despues = controlador._timeline.resumen(controlador._timeline.estado_en_accion(5), "#6")
        self.assertEqual(antes, despues)
        self.assertEqual(len(controlador._timeline.acciones), 10)
        self.assertEqual([p.indice_accion for p in controlador._timeline.checkpoints], [0, 4, 8])
        controlador.cerrar_recursos()

    def test_binario_y_json_coinciden_con_linea(self):
        controlador = self.controlador(k=4)
        jugar(controlador, 6, 3)
        ruta = os.path.join(self.directorio, "partida.sav")
        controlador.guardar_partida(ruta)
        self.assertEqual(GuardadoBinario().cargar(ruta), GuardadoJSON().cargar(ruta + ".json"))
        controlador.cerrar_recursos()

    def test_p1_binario_se_rechaza(self):
        ruta = os.path.join(self.directorio, "p1.sav")
        with open(ruta, "wb") as archivo:
            archivo.write(b"CRPT" + struct.pack("<H", 2))
        with self.assertRaises(ErrorFormatoIncompatible) as contexto:
            GuardadoBinario().cargar(ruta)
        self.assertIn("Parte I", str(contexto.exception))

    def test_p1_json_se_rechaza(self):
        ruta = os.path.join(self.directorio, "p1.json")
        with open(ruta, "w", encoding="utf-8") as archivo:
            json.dump({"cripta_id": "x"}, archivo)
        with self.assertRaises(ErrorFormatoIncompatible) as contexto:
            GuardadoJSON().cargar(ruta)
        self.assertIn("Parte I", str(contexto.exception))


class _VistaHistoria:
    def __init__(self):
        self.historiales = []
        self.errores = []

    def mostrar_historia(self, resumen):
        self.historiales.append(resumen)

    def mostrar_error(self, texto):
        self.errores.append(texto)

    def mostrar_info(self, texto):
        pass

    def mostrar_estado(self, juego):
        pass


class PruebaComandoHistoria(BaseTimeline):
    def test_historia_por_accion(self):
        controlador = self.controlador(k=3)
        jugar(controlador, 8, 3)
        resultado = controlador.consultar_historia("#3")
        esperado = controlador._timeline.resumen(
            controlador._timeline.estado_en_accion(2), "#3"
        )
        self.assertEqual(resultado, esperado)

    def test_historia_en_instante_de_decision(self):
        controlador = self.controlador(k=3)
        jugar(controlador, 8, 3)
        instante = controlador._timeline.acciones[4].tiempo
        resultado = controlador.consultar_historia(str(instante))
        esperado = controlador._timeline.resumen(
            controlador._timeline.estado_en_accion(4), f"t={instante}"
        )
        self.assertEqual(resultado, esperado)

    def test_historia_en_cero(self):
        controlador = self.controlador()
        jugar(controlador, 4, 3)
        resultado = controlador.consultar_historia("0")
        self.assertEqual(resultado.reloj, 0)
        self.assertEqual(resultado.sala, 1)

    def test_rechazos(self):
        controlador = self.controlador()
        jugar(controlador, 4, 3)
        acciones = len(controlador._timeline.acciones)
        for argumento in (
            "#0",
            f"#{acciones + 1}",
            str(controlador.juego.reloj + 1),
            "-1",
            "",
            "abc",
            "#x",
        ):
            with self.assertRaises(ValueError, msg=argumento):
                controlador.consultar_historia(argumento)

    def test_consulta_no_altera_nada(self):
        controlador = self.controlador(k=3, replay=True)
        jugar(controlador, 5, 3)
        ruta = controlador._ruta_log
        tamano = os.path.getsize(ruta)
        reloj = controlador.juego.reloj
        acciones = controlador.juego.jugador.acciones_ejecutadas
        historial = controlador.juego.historial
        antes = (historial.puede_retroceder(), historial.cambios_del_ultimo(), len(historial))
        controlador.consultar_historia("#2")
        self.assertEqual(controlador.juego.reloj, reloj)
        self.assertEqual(controlador.juego.jugador.acciones_ejecutadas, acciones)
        self.assertEqual(
            (historial.puede_retroceder(), historial.cambios_del_ultimo(), len(historial)), antes
        )
        self.assertEqual(os.path.getsize(ruta), tamano)
        controlador.cerrar_recursos()

    def test_procesar_comando_historia(self):
        controlador = self.controlador()
        jugar(controlador, 4, 3)
        vista = _VistaHistoria()
        controlador.vista = vista
        self.assertTrue(
            controlador.procesar_comando(ComandoUsuario(TipoComando.HISTORIA, argumento="#2"))
        )
        self.assertEqual(len(vista.historiales), 1)
        controlador.procesar_comando(
            ComandoUsuario(TipoComando.HISTORIA, argumento="999999")
        )
        self.assertTrue(vista.errores)

    def test_vista_consola_parsea_historia(self):
        vista = VistaConsola()
        comando = vista._interpretar("historia 120", None)
        self.assertIs(comando.tipo, TipoComando.HISTORIA)
        self.assertEqual(comando.argumento, "120")
        comando = vista._interpretar("historia #4", None)
        self.assertIs(comando.tipo, TipoComando.HISTORIA)
        self.assertEqual(comando.argumento, "#4")
        with mock.patch.object(vista, "mostrar_error") as error:
            self.assertIsNone(vista._interpretar("historia", None))
            error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
