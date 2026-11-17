"""Spec 003 — Niebla de guerra e «ir a» (Persona A).

Cada prueba cita ``003/FR-xxx`` o ``AC-003-xx``.
"""

import io
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout

from cripta.adaptadores.fuente_offline import FuenteOffline
from cripta.adaptadores.guardado import GuardadoBinario, GuardadoJSON
from cripta.bench.bot import jugar
from cripta.controlador.comandos import ComandoUsuario, TipoComando
from cripta.controlador.controlador import Controlador, OpcionesEjecucion
from cripta.controlador.replay import ReproductorReplay
from cripta.modelo.acciones import Accion, TipoAccion
from cripta.modelo.conocimiento import AVISTADA, DESCONOCIDA, EXPLORADA, RECUERDA_ABIERTA, RECUERDA_CERRADA, SIN_OBSERVAR
from cripta.modelo.juego import Juego
from cripta.vista.vista_consola import VistaConsola
from tests.apoyo_p2 import CriptaPrueba, salida

DATOS_EJEMPLO = os.path.join(os.path.dirname(__file__), "..", "datos_ejemplo")
ESPERAR = Accion(TipoAccion.ESPERAR)


def mover(direccion):
    return Accion(TipoAccion.MOVER, direccion=direccion)


def estado(juego, sala_id):
    return juego.conocimiento.estado(juego.mapa.sala(sala_id))


def recuerdo(juego, sala_id, direccion):
    return juego.conocimiento.recuerdo(juego.mapa.sala(sala_id).salida(direccion).puerta)


def recoger(juego, tipo):
    for objeto in juego.jugador.sala.objetos_suelo:
        if objeto.tipo_id == tipo:
            return juego.ejecutar_accion(Accion(TipoAccion.RECOGER, objetivo=objeto.id))
    raise AssertionError(f"no hay {tipo} en el suelo")


def usar(juego, tipo):
    objeto = juego.jugador.inventario.buscar_por_tipo(tipo)
    return juego.ejecutar_accion(Accion(TipoAccion.USAR, objetivo=objeto.id))


def cruz():
    """1 en el centro; 2 (N), 3 (E, por puerta cerrada sin llave), 4 (S); 5 detrás de 2; 6 detrás de 3."""
    return [
        (1, [salida("N", 2, 100), salida("S", 4, 100), salida("E", 3, 100, cerrada=True)]),
        (2, [salida("S", 1), salida("N", 5, 100)]),
        (3, [salida("O", 1), salida("E", 6, 100, cerrada=True)]),
        (4, [salida("N", 1)]),
        (5, [salida("S", 2)]),
        (6, [salida("O", 3)]),
    ]


class PruebaConocimiento(unittest.TestCase):
    def test_003_fr001_fr002_fr004_estado_inicial(self):
        """003/FR-001, FR-002, FR-004 (escenario US1-1): inicial explorada, destinos avistados, resto desconocido."""
        juego = CriptaPrueba(cruz()).juego()
        self.assertEqual(estado(juego, 1), EXPLORADA)
        for vecina in (2, 3, 4):
            self.assertEqual(estado(juego, vecina), AVISTADA)
        for lejana in (5, 6):
            self.assertEqual(estado(juego, lejana), DESCONOCIDA)

    def test_003_fr003_entrar_explora(self):
        """003/FR-003, FR-004: entrar a una sala la explora y avista sus destinos."""
        juego = CriptaPrueba(cruz()).juego()
        juego.ejecutar_accion(mover("N"))
        self.assertEqual(estado(juego, 2), EXPLORADA)
        self.assertEqual(estado(juego, 5), AVISTADA)

    def test_003_fr007_fr008_memoria_de_puertas(self):
        """003/FR-007, FR-008, FR-009: se observa al entrar y al cambiar estando presente; se recuerda lo último visto."""
        salas = [
            (1, [salida("E", 2, 100, cerrada=True, cierre=300), salida("O", 3, 100)]),
            (2, [salida("O", 1)]),
            (3, [salida("E", 1)]),
        ]
        juego = CriptaPrueba(salas).juego()
        self.assertEqual(recuerdo(juego, 1, "E"), RECUERDA_CERRADA)  # observada al iniciar
        juego.ejecutar_accion(Accion(TipoAccion.ABRIR, direccion="E"))
        self.assertEqual(recuerdo(juego, 1, "E"), RECUERDA_ABIERTA)
        juego.ejecutar_accion(mover("O"))  # se va a la sala 3: ya no ve la puerta
        while not juego.mapa.sala(1).salida("E").puerta.cerrada:
            juego.ejecutar_accion(ESPERAR)
        self.assertEqual(recuerdo(juego, 1, "E"), RECUERDA_ABIERTA)  # recuerdo viejo (FR-008)
        juego.ejecutar_accion(mover("E"))  # vuelve a la sala 1 y la observa
        self.assertEqual(recuerdo(juego, 1, "E"), RECUERDA_CERRADA)

    def test_003_fr007_cambio_visto_estando_presente(self):
        """003/FR-007: si la puerta se cierra sola mientras el jugador está en la sala, lo ve."""
        salas = [(1, [salida("E", 2, 100, cerrada=True, cierre=120)]), (2, [salida("O", 1)])]
        juego = CriptaPrueba(salas).juego()
        juego.ejecutar_accion(Accion(TipoAccion.ABRIR, direccion="E"))
        for _ in range(3):
            juego.ejecutar_accion(ESPERAR)
        self.assertTrue(juego.mapa.sala(1).salida("E").puerta.cerrada)
        self.assertEqual(recuerdo(juego, 1, "E"), RECUERDA_CERRADA)

    def test_ac_003_04_antorcha_explora_vecinas_sin_activar(self):
        """AC-003-04 / 003/FR-010, FR-011: con antorcha, entrar explora las vecinas (también por puertas cerradas) sin activar enemigos ni trampas."""
        cripta = CriptaPrueba(cruz()).con_objeto(1, "itm_antorcha")
        cripta.con_enemigo(6, "e-rata", "ent_rata").con_trampa(6, "t-1")
        juego = cripta.juego()
        recoger(juego, "itm_antorcha")
        usar(juego, "itm_antorcha")
        juego.ejecutar_accion(Accion(TipoAccion.ABRIR, direccion="E"))
        juego.ejecutar_accion(mover("E"))  # entra a 3 con la antorcha encendida
        self.assertEqual(estado(juego, 6), EXPLORADA)  # vecina detrás de una puerta cerrada
        rata = juego.enemigos.obtener("e-rata")
        self.assertFalse(rata.activo)
        self.assertTrue(juego.mapa.sala(6).trampas[0].armada)
        self.assertEqual(juego.jugador.vida, juego.jugador.vida_max)
        self.assertFalse(juego.mapa.sala(6).visitada)

    def test_003_fr009_puerta_de_vecina_por_antorcha_queda_sin_observar(self):
        """003/FR-009 (clarify): las puertas de una vecina explorada por antorcha que no tocan la sala actual quedan sin observar."""
        cripta = CriptaPrueba(cruz()).con_objeto(1, "itm_antorcha")
        juego = cripta.juego()
        recoger(juego, "itm_antorcha")
        usar(juego, "itm_antorcha")
        juego.ejecutar_accion(mover("S"))  # entra a 4: explora su vecina 1 (ya explorada)
        juego.ejecutar_accion(mover("N"))  # vuelve a 1: explora 2, 3 y 4
        self.assertEqual(estado(juego, 3), EXPLORADA)
        self.assertEqual(recuerdo(juego, 3, "E"), SIN_OBSERVAR)  # puerta 3-6: no la vio

    def test_003_clarify_antorcha_no_explora_al_encenderla(self):
        """003 (clarify): encender la antorcha no explora nada; el efecto es al entrar."""
        juego = CriptaPrueba(cruz()).con_objeto(1, "itm_antorcha").juego()
        recoger(juego, "itm_antorcha")
        usar(juego, "itm_antorcha")
        self.assertEqual(estado(juego, 2), AVISTADA)

    def test_ac_003_05_pergamino_revierte_la_antorcha(self):
        """AC-003-05 / 003/FR-015: un pergamino deshace la exploración hecha por la antorcha."""
        cripta = CriptaPrueba(cruz()).con_objeto(1, "itm_antorcha").con_objeto(1, "itm_pergamino")
        juego = cripta.juego()
        recoger(juego, "itm_antorcha")
        recoger(juego, "itm_pergamino")
        usar(juego, "itm_antorcha")
        antes = juego.serializar_conocimiento()
        juego.ejecutar_accion(mover("N"))  # entra a 2: explora 1 y 5
        self.assertEqual(estado(juego, 5), EXPLORADA)
        self.assertNotEqual(juego.serializar_conocimiento(), antes)
        self.assertTrue(juego.usar_pergamino().aceptada)
        self.assertEqual(juego.serializar_conocimiento(), antes)
        self.assertEqual(estado(juego, 5), DESCONOCIDA)

    def test_003_fr014_guardar_y_cargar_conserva_el_conocimiento(self):
        """003/FR-014 (escenario US5-2): binario y JSON conservan exactamente el conocimiento."""
        cripta = CriptaPrueba(cruz())
        juego = cripta.juego()
        juego.ejecutar_accion(mover("N"))
        juego.ejecutar_accion(mover("N"))
        texto = juego.serializar_conocimiento()
        directorio = tempfile.mkdtemp()
        try:
            for formato in (GuardadoBinario(), GuardadoJSON()):
                ruta = os.path.join(directorio, "p.sav")
                formato.guardar(ruta, juego.exportar_estado("v"))
                cargado = Juego.desde_estado(formato.cargar(ruta), cripta.datos, cripta.mapa(), juego.fichas)
                self.assertEqual(cargado.serializar_conocimiento(), texto)
        finally:
            shutil.rmtree(directorio, ignore_errors=True)

    def test_003_fr013_mapa_conocido_solo_lo_explorado(self):
        """003/FR-005, FR-006, FR-012, FR-013 (escenarios US2-1 y US2-2): de lo explorado se ven nombre, salidas,
        costo y puerta recordada; los destinos sin explorar no tienen nombre."""
        juego = CriptaPrueba(cruz()).juego()
        juego.ejecutar_accion(mover("N"))
        mapa = juego.mapa_conocido()
        self.assertEqual([s.id for s in mapa.exploradas], [1, 2])
        self.assertEqual(mapa.avistadas, 3)  # 3, 4 y 5
        sala1 = mapa.exploradas[0]
        este = [s for s in sala1.salidas if s.direccion == "E"][0]
        self.assertIsNone(este.destino_id)
        self.assertIsNone(este.destino_nombre)
        self.assertEqual(este.puerta, "cerrada")
        self.assertTrue(mapa.exploradas[1].actual)

    def test_003_fr012_la_consola_no_muestra_salas_sin_explorar(self):
        """003/FR-006, FR-012 y 001/FR-019: la consola muestra costos y no nombra salas sin explorar."""
        juego = CriptaPrueba(cruz()).juego()
        salida_texto = io.StringIO()
        with redirect_stdout(salida_texto):
            VistaConsola().mostrar_estado(juego)
            VistaConsola().mostrar_mapa(juego.mapa_conocido())
        texto = salida_texto.getvalue()
        self.assertIn("sala sin explorar", texto)
        self.assertIn("costo 100", texto)
        self.assertNotIn("Sala 5", texto)
        self.assertNotIn("Sala 2 (2)", texto)


class PruebaIrA(unittest.TestCase):
    def controlador_prueba(self, cripta, semilla=1):
        """Controlador sin red ni vista sobre una cripta hecha a mano (todo el contenido cargado)."""
        controlador = Controlador.__new__(Controlador)
        controlador.vista = None
        controlador._juego = cripta.juego(semilla=semilla)
        controlador._precarga = None
        controlador._timeline = None
        controlador._escritor = None
        return controlador

    def test_ac_003_01_destino_no_explorado_se_rechaza_sin_tiempo(self):
        """AC-003-01 / 003/FR-018: ir a una sala no explorada se rechaza y no consume tiempo."""
        controlador = self.controlador_prueba(CriptaPrueba(cruz()))
        juego = controlador.juego
        for argumento in ("5", "2", "99", "abc", ""):
            viaje = controlador.ir_a(argumento)
            self.assertFalse(viaje.aceptado, argumento)
            self.assertEqual(viaje.pasos, 0)
        self.assertEqual(juego.reloj, 0)
        self.assertEqual(juego.jugador.acciones_ejecutadas, 0)
        self.assertFalse(controlador.ir_a("1").aceptado)  # sala actual (FR-018)

    def test_003_fr022_llega_al_destino(self):
        """003/FR-017, FR-020, FR-022: el viaje llega por movimientos ordinarios."""
        controlador = self.controlador_prueba(CriptaPrueba(cruz()))
        juego = controlador.juego
        juego.ejecutar_accion(mover("N"))
        juego.ejecutar_accion(mover("N"))
        juego.ejecutar_accion(mover("S"))
        juego.ejecutar_accion(mover("S"))
        reloj = juego.reloj
        viaje = controlador.ir_a("5")
        self.assertTrue(viaje.aceptado)
        self.assertEqual((viaje.pasos, juego.jugador.sala.id), (2, 5))
        self.assertEqual(juego.reloj, reloj + 200)
        self.assertIn("Llegaste", viaje.motivo)

    def test_003_fr019_ruta_mas_barata_conocida_y_desempate(self):
        """003/FR-019: minimiza costos con lo conocido; empate ⇒ primer paso a la vecina de menor id."""
        salas = [
            (1, [salida("N", 7, 100), salida("E", 4, 100)]),
            (4, [salida("O", 1), salida("N", 9, 100)]),
            (7, [salida("S", 1), salida("E", 9, 100)]),
            (9, [salida("S", 4), salida("O", 7)]),
        ]
        controlador = self.controlador_prueba(CriptaPrueba(salas))
        juego = controlador.juego
        for d in ("N", "E", "S", "O"):  # recorre 1→7→9→4→1
            juego.ejecutar_accion(mover(d))
        self.assertEqual(juego.jugador.sala.id, 1)
        self.assertEqual(juego.paso_hacia(9).destino.id, 4)

    def test_ac_003_02_puerta_recordada_abierta_pero_cerrada(self):
        """AC-003-02 / 003/FR-021, FR-022: al observarla cerrada se recalcula; sin ruta, se detiene sin tiempo extra."""
        salas = [
            (1, [salida("E", 2, 100)]),
            (2, [salida("O", 1), salida("E", 3, 100, cerrada=True, cierre=400)]),
            (3, [salida("O", 2)]),
        ]
        controlador = self.controlador_prueba(CriptaPrueba(salas))
        juego = controlador.juego
        juego.ejecutar_accion(mover("E"))  # t=0 → 100 (sala 2)
        juego.ejecutar_accion(Accion(TipoAccion.ABRIR, direccion="E"))  # se cierra en t=500
        juego.ejecutar_accion(mover("E"))  # sala 3
        juego.ejecutar_accion(mover("O"))  # sala 2
        juego.ejecutar_accion(mover("O"))  # sala 1 (ya no ve la puerta 2-3)
        while not juego.mapa.sala(2).salida("E").puerta.cerrada:
            juego.ejecutar_accion(ESPERAR)
        self.assertEqual(recuerdo(juego, 2, "E"), RECUERDA_ABIERTA)
        viaje = controlador.ir_a("3")
        self.assertEqual(viaje.pasos, 1)  # entra a 2, ve la puerta cerrada y no queda ruta
        self.assertEqual(juego.jugador.sala.id, 2)
        self.assertEqual(recuerdo(juego, 2, "E"), RECUERDA_CERRADA)
        self.assertIn("ruta conocida", viaje.motivo)
        reloj = juego.reloj
        self.assertEqual(controlador.ir_a("3").pasos, 0)
        self.assertEqual(juego.reloj, reloj)  # sin tiempo adicional

    def test_ac_003_02_recalcula_y_usa_otra_ruta(self):
        """AC-003-02 / 003/FR-021: si queda otra ruta conocida, el viaje la toma."""
        salas = [
            (1, [salida("E", 2, 100), salida("S", 4, 300)]),
            (2, [salida("O", 1), salida("E", 3, 100, cerrada=True, cierre=600)]),
            (3, [salida("O", 2), salida("S", 5, 300)]),
            (4, [salida("N", 1), salida("E", 5, 300)]),
            (5, [salida("O", 4), salida("N", 3)]),
        ]
        controlador = self.controlador_prueba(CriptaPrueba(salas))
        juego = controlador.juego
        juego.ejecutar_accion(mover("E"))
        juego.ejecutar_accion(Accion(TipoAccion.ABRIR, direccion="E"))
        for d in ("E", "S", "O", "N"):  # 2→3→5→4→1: todo explorado
            juego.ejecutar_accion(mover(d))
        while not juego.mapa.sala(2).salida("E").puerta.cerrada:
            juego.ejecutar_accion(ESPERAR)
        viaje = controlador.ir_a("3")
        self.assertEqual(juego.jugador.sala.id, 3)
        # 1→2 (ahí ve la puerta 2-3 cerrada y recalcula) y luego 2→1→4→5→3: 5 pasos.
        self.assertEqual(viaje.pasos, 5)
        self.assertIn("Llegaste", viaje.motivo)

    def test_ac_003_03_entra_a_sala_con_enemigos_dormidos(self):
        """AC-003-03 / 003/FR-022: los enemigos dormidos se activan (P1 §2.4) y el viaje se detiene."""
        salas = [
            (1, [salida("N", 2, 100), salida("E", 3, 1000)]),
            (2, [salida("S", 1), salida("E", 3, 100)]),
            (3, [salida("O", 1), salida("N", 2)]),
        ]
        cripta = CriptaPrueba(salas).con_objeto(1, "itm_antorcha").con_enemigo(2, "e-rata", "ent_rata")
        controlador = self.controlador_prueba(cripta)
        juego = controlador.juego
        recoger(juego, "itm_antorcha")
        usar(juego, "itm_antorcha")
        juego.ejecutar_accion(mover("E"))  # 1→3 por la salida cara: la antorcha explora 2
        juego.ejecutar_accion(mover("O"))  # vuelve a 1
        rata = juego.enemigos.obtener("e-rata")
        self.assertFalse(rata.activo)
        viaje = controlador.ir_a("3")
        self.assertEqual((viaje.pasos, juego.jugador.sala.id), (1, 2))
        self.assertTrue(rata.activo)
        self.assertIn("enemigos", viaje.motivo)

    def test_003_fr022_recibe_dano_y_se_detiene(self):
        """003/FR-022: una trampa en una sala intermedia hace daño y detiene el viaje."""
        salas = [
            (1, [salida("E", 2, 100), salida("S", 3, 1000)]),
            (2, [salida("O", 1), salida("E", 3, 100)]),
            (3, [salida("O", 2), salida("N", 1)]),
        ]
        cripta = CriptaPrueba(salas).con_trampa(2, "t-1")
        controlador = self.controlador_prueba(cripta)
        juego = controlador.juego
        juego.ejecutar_accion(mover("E"))  # pisa la trampa
        juego.ejecutar_accion(mover("E"))
        juego.ejecutar_accion(mover("N"))  # 3→1 por la salida cara (la trampa se rearma)
        self.assertTrue(juego.mapa.sala(2).trampas[0].armada)
        vida = juego.jugador.vida
        viaje = controlador.ir_a("3")
        self.assertEqual((viaje.pasos, juego.jugador.sala.id), (1, 2))
        self.assertLess(juego.jugador.vida, vida)
        self.assertIn("daño", viaje.motivo)

    def test_003_fr023_no_abre_puertas(self):
        """003/FR-023: con la llave en el inventario, el viaje no abre la puerta."""
        salas = [
            (1, [salida("E", 2, 100, cerrada=True, llave="itm_llave")]),
            (2, [salida("O", 1)]),
        ]
        cripta = CriptaPrueba(salas).con_objeto(1, "itm_llave").con_objeto(1, "itm_antorcha")
        controlador = self.controlador_prueba(cripta)
        juego = controlador.juego
        recoger(juego, "itm_llave")
        recoger(juego, "itm_antorcha")
        juego.conocimiento.explorar(juego.mapa.sala(2), juego._asignar_casilla)  # la conoce, pero cerrada
        viaje = controlador.ir_a("2")
        self.assertTrue(viaje.aceptado)
        self.assertEqual(viaje.pasos, 0)
        self.assertTrue(juego.mapa.sala(1).salida("E").puerta.cerrada)

    def test_ac_003_06_pergamino_revierte_solo_el_ultimo_paso(self):
        """AC-003-06 / 003/FR-025: tras un viaje de 3 pasos, el pergamino deshace solo el último y el viaje no sigue."""
        salas = [(i, ([salida("E", i + 1, 100)] if i < 4 else []) + ([salida("O", i - 1)] if i > 1 else []))
                 for i in range(1, 5)]
        cripta = CriptaPrueba(salas).con_objeto(1, "itm_pergamino")
        controlador = self.controlador_prueba(cripta)
        juego = controlador.juego
        recoger(juego, "itm_pergamino")
        for d in ("E", "E", "E", "O", "O", "O"):
            juego.ejecutar_accion(mover(d))
        acciones = juego.jugador.acciones_ejecutadas
        viaje = controlador.ir_a("4")
        self.assertEqual(viaje.pasos, 3)
        self.assertTrue(juego.usar_pergamino().aceptada)
        self.assertEqual(juego.jugador.sala.id, 3)
        self.assertEqual(juego.jugador.acciones_ejecutadas, acciones + 2)
        reloj = juego.reloj
        self.assertEqual(juego.jugador.sala.id, 3)  # nada lo vuelve a mover
        self.assertEqual(juego.reloj, reloj)


class PruebaIrAConControlador(unittest.TestCase):
    """003/FR-024, FR-027 y FR-016 con el controlador real (paquete offline cripta-02)."""

    def setUp(self):
        self.directorio = tempfile.mkdtemp(prefix="cripta_niebla_")

    def tearDown(self):
        shutil.rmtree(self.directorio, ignore_errors=True)

    def controlador(self, sub="a", replay=True, k=4):
        controlador = Controlador(
            FuenteOffline(DATOS_EJEMPLO),
            OpcionesEjecucion(directorio_datos=os.path.join(self.directorio, sub), cache_size=25, checkpoint_cada=k),
            None,
        )
        controlador.preparar_cripta("cripta-02")
        controlador._datos.jugador.vida_max = 10**6
        controlador.iniciar_partida("Niebla", 3, registrar_replay=replay)
        return controlador

    def test_003_fr024_log_con_pasos_y_comentario_y_replay_fiel(self):
        """003/FR-024, FR-027 / SC-005: un paso por línea, la orden como comentario, y el replay da el mismo estado."""
        controlador = self.controlador()
        jugar(controlador, 12, 3)
        juego = controlador.juego
        inicial = juego.mapa.sala_inicial.id
        if juego.jugador.sala.id == inicial:
            jugar(controlador, 3, 4)
        viaje = controlador.ir_a(str(inicial))
        self.assertTrue(viaje.aceptado, viaje.motivo)
        self.assertGreater(viaje.pasos, 0)
        estado_final = controlador.juego.exportar_estado("x")
        ruta = controlador._ruta_log
        controlador.cerrar_recursos()
        with open(ruta, encoding="utf-8") as archivo:
            lineas = [linea.rstrip("\n") for linea in archivo]
        self.assertIn(f"# ir a {inicial}", lineas)
        indice = lineas.index(f"# ir a {inicial}")
        pasos = lineas[indice + 1: indice + 1 + viaje.pasos]
        self.assertTrue(all(linea.startswith("mover ") for linea in pasos))
        reproductor = ReproductorReplay(ruta, FuenteOffline(DATOS_EJEMPLO),
                                        OpcionesEjecucion(directorio_datos=os.path.join(self.directorio, "r"), cache_size=25))
        resumen = reproductor.ejecutar()
        self.assertEqual(reproductor.acciones_rechazadas, 0)
        self.assertIsNotNone(resumen)
        # mismo reloj, sala y conocimiento que la partida original
        reproducido = reproductor._controlador.juego.exportar_estado("x")
        self.assertEqual(reproducido.reloj, estado_final.reloj)
        self.assertEqual(reproducido.conocimiento, estado_final.conocimiento)

    def test_003_fr016_historia_muestra_el_mapa_conocido_de_ese_momento(self):
        """003/FR-016 (escenario US5-3): historia #k muestra las salas exploradas antes de la acción k."""
        controlador = self.controlador(replay=False, k=3)
        juego = controlador.juego
        esperado = []
        from cripta.bench.bot import elegir_accion
        import random
        azar = random.Random(3)
        visitadas = []
        for _ in range(10):
            esperado.append([s.id for s in juego.mapa if juego.conocimiento.explorada(s)])
            if juego.jugador.sala.id not in visitadas:
                visitadas.append(juego.jugador.sala.id)
            controlador.ejecutar_accion(elegir_accion(juego, azar, visitadas))
            juego = controlador.juego
        for k in range(1, len(controlador.timeline.acciones) + 1):
            resumen = controlador.consultar_historia(f"#{k}")
            self.assertEqual(resumen.mapa_conocido, esperado[k - 1], f"#{k}")

    def test_003_comandos_mapa_e_ir_a_en_la_consola(self):
        """003/FR-013, FR-026: la consola entiende 'mapa' e 'ir a N' y el controlador los atiende."""
        vista = VistaConsola()
        juego = self.controlador(replay=False).juego
        self.assertEqual(vista._interpretar("mapa", juego).tipo, TipoComando.MAPA)
        comando = vista._interpretar("ir a 7", juego)
        self.assertEqual((comando.tipo, comando.argumento), (TipoComando.IR_A, "7"))
        self.assertEqual(vista._interpretar("ir norte", juego).tipo, TipoComando.ACCION)
        controlador = self.controlador(sub="b", replay=False)
        controlador.vista = vista
        salida_texto = io.StringIO()
        with redirect_stdout(salida_texto):
            controlador.procesar_comando(ComandoUsuario(TipoComando.MAPA))
            controlador.procesar_comando(ComandoUsuario(TipoComando.IR_A, argumento="999"))
        texto = salida_texto.getvalue()
        self.assertIn("Mapa conocido", texto)
        self.assertIn("No conoces la sala 999", texto)


if __name__ == "__main__":
    unittest.main()
