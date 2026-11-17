"""Pruebas de los contratos A↔B de la Parte II (lo que A entrega a B).

- 004/contracts/interfaz-a-b.md: costo de salida, cazador con rango (T048 de 004).
- 005/contracts/interfaz-a-b-timeline.md: ``avanzar_hasta`` / ``ejecutar_accion(hasta=)``
  y conocimiento en la línea de tiempo (T016, T030..T032, T053, T054, T056 de 005).
- 003/contracts/interfaz-a-b-conocimiento.md: conocimiento en el estado guardable.
"""

import os
import unittest

from cripta.adaptadores.fuente_offline import FuenteOffline
from cripta.bench.sinteticos import FichasEnMemoria
from cripta.modelo.acciones import Accion, TipoAccion
from cripta.modelo.actores import Comportamiento
from cripta.modelo.datos import DatosSala
from cripta.modelo.mapa import Mapa
from cripta.modelo.timeline import LineaTiempo
from tests.apoyo_p2 import CriptaPrueba, salida

DATOS_P2 = os.path.join(os.path.dirname(__file__), "..", "datos_ejemplo_p2")


def mover(direccion):
    return Accion(TipoAccion.MOVER, direccion=direccion)


class LineaManual:
    """Juego + línea de tiempo sin controlador (como hace el controlador)."""

    def __init__(self, cripta, k=3):
        self.cripta = cripta
        self.juego = cripta.juego()
        self.linea = LineaTiempo(cripta.datos, cripta.esqueleto, FichasEnMemoria(cripta.fichas), 1, "v", k)
        self.linea.registrar_inicio(self.juego)

    def accion(self, accion):
        juego = self.juego
        inicio = juego.reloj
        resultado = juego.ejecutar_accion(accion)
        if resultado.aceptada:
            if accion.tipo is TipoAccion.RETROCEDER:
                self.linea.recortar(juego.jugador.acciones_ejecutadas)
            else:
                self.linea.registrar_accion(juego, accion, inicio)
        return resultado


class PruebaCostoYCazadorDesdeElServicio(unittest.TestCase):
    """004/T048 y criterio de aceptación de 004/contracts/interfaz-a-b.md §5."""

    def test_costo_250_y_sin_costo_100_desde_el_esqueleto(self):
        datos = CriptaPrueba([(1, [salida("E", 2, 250)]), (2, [salida("O", 1)]), (3, [])]).datos
        salas = [DatosSala.desde_json({"id": 1, "nombre": "A", "salidas": {"E": {"sala": 2, "costo": 250}, "S": {"sala": 3}}}),
                 DatosSala.desde_json({"id": 2, "nombre": "B", "salidas": {"O": {"sala": 1}}}),
                 DatosSala.desde_json({"id": 3, "nombre": "C", "salidas": {"N": {"sala": 1}}})]
        mapa = Mapa.construir(datos, salas)
        self.assertEqual(mapa.sala(1).salida("E").costo, 250)
        self.assertEqual(mapa.sala(1).salida("S").costo, 100)

    @unittest.skipUnless(os.path.isdir(os.path.join(DATOS_P2, "cripta-06")), "falta datos_ejemplo_p2/")
    def test_cazadores_reales_de_la_referencia(self):
        """Las fichas reales de cazador (rango 600 y 2400) llegan al enemigo con su rango."""
        fuente = FuenteOffline(DATOS_P2)
        fichas = fuente.catalogo(["ent_sabueso_oseo", "ent_espectro_acechador"])
        self.assertEqual(sorted(f.rango for f in fichas), [600, 2400])
        sala = Mapa.construir(CriptaPrueba([(1, [])]).datos, [DatosSala(1, "S", [])]).sala(1)
        from cripta.modelo.actores import Enemigo
        for ficha in fichas:
            enemigo = Enemigo("e-x", ficha, None, 0, sala)
            self.assertIs(enemigo.comportamiento, Comportamiento.CAZADOR)
            self.assertEqual(enemigo.rango, ficha.rango)


class PruebaReporteAlIniciar(unittest.TestCase):
    """004/contracts/interfaz-a-b.md §3 (vista de A): el reporte se muestra al iniciar (FR-013, FR-010)."""

    @unittest.skipUnless(os.path.isdir(os.path.join(DATOS_P2, "cripta-05")), "falta datos_ejemplo_p2/")
    def test_consola_no_resoluble_muestra_reporte_y_deja_elegir_otra(self):
        """AC-006-05 / 006/FR-009: la terminal muestra el reporte y vuelve a la lista."""
        import io
        import tempfile
        from contextlib import redirect_stdout
        from cripta.controlador.controlador import Controlador, OpcionesEjecucion
        from cripta.vista.vista_consola import VistaConsola

        entradas = iter(["1", "2", "Ana", "salir"])  # cripta-05 (no resoluble), luego cripta-06
        vista = VistaConsola()
        vista._entrada = lambda mensaje="": next(entradas)
        with tempfile.TemporaryDirectory() as carpeta:
            controlador = Controlador(
                FuenteOffline(DATOS_P2), OpcionesEjecucion(directorio_datos=carpeta, cache_size=25), vista)
            texto = io.StringIO()
            with redirect_stdout(texto):
                codigo = controlador.ejecutar_interactivo()
        salida = texto.getvalue()
        self.assertEqual(codigo, 0)
        self.assertIn("NO RESOLUBLE", salida)
        self.assertIn("Esta cripta no se puede ganar", salida)
        self.assertEqual(controlador.juego.datos.id, "cripta-06")

    def test_con_cripta_fija_sigue_saliendo_con_codigo_3(self):
        """AC-006-06 / 006/FR-010: con --cripta y sin --forzar no hay lista a la que volver: código 3 (AC-004-04)."""
        import io
        import tempfile
        from contextlib import redirect_stdout
        from cripta.controlador.aplicacion import main

        with tempfile.TemporaryDirectory() as carpeta, redirect_stdout(io.StringIO()):
            codigo = main(["--offline", DATOS_P2, "--cripta", "cripta-05", "--datos", carpeta, "--nombre", "A"])
        self.assertEqual(codigo, 3)


class PruebaAvanzarHasta(unittest.TestCase):
    """005/T016, T030..T032, T054 (AC-005-03): un instante entre decisiones."""

    def cripta(self):
        # El jugador cruza una salida de costo 250 en t=0; dos errantes activos en la sala 1
        # actúan los DOS en t=100 (mismo instante) y se van a la sala 2 (única salida).
        return (CriptaPrueba([(1, [salida("E", 2, 250)]), (2, [salida("O", 1, 250)])])
                .con_enemigo(1, "e-a", "ent_errante").con_enemigo(1, "e-b", "ent_errante"))

    def test_avanzar_hasta_no_toma_la_decision(self):
        juego = self.cripta().juego()
        juego.ejecutar_accion(mover("E"), hasta=150)
        self.assertEqual(juego.reloj, 100)  # el último evento <= 150 fue en t=100
        self.assertEqual([juego.enemigos.obtener(i).sala.id for i in ("e-a", "e-b")], [2, 2])
        juego.avanzar_hasta(400)
        self.assertEqual(juego.reloj, 250)  # se detiene en la decisión del jugador, sin tomarla
        with self.assertRaises(ValueError):
            juego.avanzar_hasta(10)

    def test_ac_005_03_varios_eventos_en_el_mismo_instante(self):
        """AC-005-03: historia <t> muestra el estado DESPUÉS de todos los eventos con tiempo t."""
        manual = LineaManual(self.cripta())
        manual.accion(mover("E"))
        manual.accion(Accion(TipoAccion.ESPERAR))
        reloj = manual.juego.reloj
        en_100 = manual.linea.estado_en_tiempo(100, reloj)
        self.assertEqual([en_100.enemigos.obtener(i).sala.id for i in ("e-a", "e-b")], [2, 2])
        en_99 = manual.linea.estado_en_tiempo(99, reloj)
        self.assertEqual([en_99.enemigos.obtener(i).sala.id for i in ("e-a", "e-b")], [1, 1])
        # Una decisión en t muestra el estado justo antes de tomarla (T032, FR-003).
        en_250 = manual.linea.estado_en_tiempo(250, reloj)
        self.assertEqual((en_250.reloj, en_250.jugador.acciones_ejecutadas), (250, 1))


class PruebaConocimientoEnLaLinea(unittest.TestCase):
    """005/T053 y T056: el conocimiento viaja en los puntos de control y el pergamino lo revierte."""

    def test_t056_pergamino_con_antorcha_y_historia(self):
        cripta = (CriptaPrueba([
            (1, [salida("N", 2, 100), salida("S", 4, 100)]),
            (2, [salida("S", 1), salida("N", 5, 100)]),
            (4, [salida("N", 1)]),
            (5, [salida("S", 2)]),
        ]).con_objeto(1, "itm_antorcha").con_objeto(1, "itm_pergamino"))
        manual = LineaManual(cripta, k=2)
        juego = manual.juego
        for tipo in ("itm_antorcha", "itm_pergamino"):
            objeto = [o for o in juego.jugador.sala.objetos_suelo if o.tipo_id == tipo][0]
            manual.accion(Accion(TipoAccion.RECOGER, objetivo=objeto.id))
        antorcha = juego.jugador.inventario.buscar_por_tipo("itm_antorcha")
        manual.accion(Accion(TipoAccion.USAR, objetivo=antorcha.id))
        antes = juego.serializar_conocimiento()
        manual.accion(mover("N"))  # con antorcha: explora 1 y 5
        self.assertNotEqual(juego.serializar_conocimiento(), antes)
        manual.accion(Accion(TipoAccion.RETROCEDER))
        self.assertEqual(juego.serializar_conocimiento(), antes)
        # La línea quedó recortada: el estado de "ahora" según la línea coincide con el vivo.
        reconstruido = manual.linea.estado_en_accion(len(manual.linea.acciones))
        self.assertEqual(reconstruido.serializar_conocimiento(), antes)
        resumen = manual.linea.resumen(reconstruido, "ahora")
        self.assertEqual(resumen.mapa_conocido, [1])

    def test_t053_checkpoints_guardan_el_conocimiento(self):
        cripta = CriptaPrueba([(1, [salida("E", 2)]), (2, [salida("O", 1), salida("E", 3)]), (3, [salida("O", 2)])])
        manual = LineaManual(cripta, k=1)
        manual.accion(mover("E"))
        manual.accion(mover("E"))
        for punto in manual.linea.checkpoints:
            self.assertTrue(punto.estado.conocimiento)
        self.assertEqual(manual.linea.checkpoints[-1].estado.conocimiento, manual.juego.serializar_conocimiento())


if __name__ == "__main__":
    unittest.main()
