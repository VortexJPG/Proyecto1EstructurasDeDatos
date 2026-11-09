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

from cripta.adaptadores.fuente_offline import FuenteOffline
from cripta.adaptadores.guardado import GuardadoBinario, GuardadoJSON, ErrorFormatoIncompatible
from cripta.bench.bot import jugar
from cripta.controlador.aplicacion import main
from cripta.controlador.controlador import Controlador, OpcionesEjecucion
from cripta.modelo.acciones import Accion, TipoAccion

DATOS_EJEMPLO = os.path.join(os.path.dirname(__file__), "..", "datos_ejemplo")


class BaseTimeline(unittest.TestCase):
    def setUp(self):
        self.directorio = tempfile.mkdtemp(prefix="cripta_tl_")

    def tearDown(self):
        shutil.rmtree(self.directorio, ignore_errors=True)

    def controlador(self, k=4, sub="a", cripta="cripta-02", semilla=3, vida=None):
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
        controlador.iniciar_partida("Tl", semilla, registrar_replay=False)
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


if __name__ == "__main__":
    unittest.main()
