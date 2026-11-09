"""Pruebas del cliente HTTP (sin red: se simula ``requests.get``) y de ``FuenteOffline``."""

import json
import os
import shutil
import tempfile
import threading
import unittest
from unittest import mock

from cripta.adaptadores.fuente_datos import ErrorFuenteDatos, PresupuestoAgotado
from cripta.adaptadores.fuente_offline import FuenteOffline

try:
    import requests  # noqa: F401

    from cripta.adaptadores import cliente_http
    from cripta.adaptadores.cliente_http import ClienteHTTP

    HAY_REQUESTS = True
except ImportError:
    HAY_REQUESTS = False


class RespuestaFalsa:
    def __init__(self, codigo, cuerpo):
        self.status_code = codigo
        self._cuerpo = cuerpo
        self.text = json.dumps(cuerpo)

    def json(self):
        return self._cuerpo


@unittest.skipUnless(HAY_REQUESTS, "requests no está instalado")
class PruebaClienteHTTP(unittest.TestCase):
    def test_encabezado_y_conteo(self):
        cliente = ClienteHTTP()
        llamadas = []

        def get_falso(url, params=None, headers=None, timeout=None):
            llamadas.append((url, params, headers, timeout))
            return RespuestaFalsa(200, {"version": "abc"})

        with mock.patch.object(cliente_http.requests, "get", side_effect=get_falso):
            self.assertEqual(cliente.version_catalogo(), "abc")
            self.assertEqual(cliente.version_catalogo(), "abc")
        self.assertEqual(cliente.estadisticas().solicitudes_realizadas, 2)
        url, _, headers, timeout = llamadas[0]
        self.assertTrue(url.endswith("/catalogo/version"))
        self.assertEqual(headers["X-Cripta-Client-Id"], cliente.client_id)  # el mismo en toda la ejecución
        self.assertEqual(llamadas[1][2]["X-Cripta-Client-Id"], cliente.client_id)
        self.assertIsNotNone(timeout)

    def test_429_reintenta_y_cuenta_en_el_presupuesto(self):
        cliente = ClienteHTTP()
        cliente.establecer_presupuesto(5)
        respuestas = [RespuestaFalsa(429, {"error": "lento", "reintentar_en": 0}), RespuestaFalsa(200, {"version": "v"})]
        with mock.patch.object(cliente_http.requests, "get", side_effect=respuestas):
            self.assertEqual(cliente.version_catalogo(), "v")
        estadisticas = cliente.estadisticas()
        self.assertEqual(estadisticas.solicitudes_realizadas, 2)
        self.assertEqual(estadisticas.respuestas_429, 1)
        self.assertEqual(cliente.solicitudes_restantes(), 3)

    def test_presupuesto_agotado(self):
        cliente = ClienteHTTP()
        cliente.establecer_presupuesto(1)
        with mock.patch.object(cliente_http.requests, "get", return_value=RespuestaFalsa(200, {"version": "v"})):
            cliente.version_catalogo()
            with self.assertRaises(PresupuestoAgotado):
                cliente.version_catalogo()
        self.assertEqual(cliente.estadisticas().solicitudes_realizadas, 1)

    def test_error_http_con_contexto(self):
        cliente = ClienteHTTP()
        with mock.patch.object(cliente_http.requests, "get", return_value=RespuestaFalsa(404, {"error": "no existe"})):
            with self.assertRaises(ErrorFuenteDatos) as contexto:
                cliente.datos_cripta("cripta-99")
        self.assertEqual(contexto.exception.codigo_http, 404)
        self.assertIn("datos_cripta", str(contexto.exception))

    def test_sin_conexion(self):
        cliente = ClienteHTTP()
        with mock.patch.object(cliente_http.requests, "get", side_effect=requests.ConnectionError("caído")):
            with self.assertRaises(ErrorFuenteDatos) as contexto:
                cliente.listar_criptas()
        self.assertIn("listar_criptas", str(contexto.exception))

    def test_llaves_con_enemigo_y_presupuesto(self):
        cliente = ClienteHTTP()
        cliente.establecer_presupuesto(3)
        cuerpo = {
            "llaves": [
                {"id": "itm_llave_bronce", "sala": 4},
                {"id": "itm_llave_negra", "sala": 12, "enemigo": "e-1203"},
            ]
        }
        with mock.patch.object(cliente_http.requests, "get", return_value=RespuestaFalsa(200, cuerpo)) as get:
            llaves = cliente.llaves("cripta-02")
        self.assertEqual(len(llaves), 2)
        self.assertEqual(llaves[0].id, "itm_llave_bronce")
        self.assertIsNone(llaves[0].enemigo)
        self.assertEqual(llaves[1].enemigo, "e-1203")
        self.assertEqual(cliente.estadisticas().solicitudes_realizadas, 1)
        args, kwargs = get.call_args
        self.assertTrue(args[0].endswith("/criptas/cripta-02/llaves"))
        self.assertIsNone(kwargs.get("params"))
        self.assertIn("X-Cripta-Client-Id", kwargs["headers"])

    def test_llaves_404_con_contexto(self):
        cliente = ClienteHTTP()
        with mock.patch.object(cliente_http.requests, "get", return_value=RespuestaFalsa(404, {"error": "no existe"})):
            with self.assertRaises(ErrorFuenteDatos) as contexto:
                cliente.llaves("cripta-99")
        self.assertEqual(contexto.exception.codigo_http, 404)
        self.assertIn("llaves", str(contexto.exception))

    def test_llaves_presupuesto_agotado(self):
        cliente = ClienteHTTP()
        cliente.establecer_presupuesto(1)
        with mock.patch.object(cliente_http.requests, "get", return_value=RespuestaFalsa(200, {"llaves": []})):
            cliente.llaves("cripta-02")
            with self.assertRaises(PresupuestoAgotado) as contexto:
                cliente.llaves("cripta-02")
        self.assertIn("llaves", str(contexto.exception))
        self.assertEqual(cliente.estadisticas().solicitudes_realizadas, 1)

    def test_dos_hilos_no_exceden_el_presupuesto(self):
        cliente = ClienteHTTP()
        cliente.establecer_presupuesto(50)
        barrera = threading.Barrier(2)
        agotados = []

        def get_falso(url, params=None, headers=None, timeout=None):
            return RespuestaFalsa(200, {"version": "v"})

        def trabajar():
            barrera.wait()
            for _ in range(40):
                try:
                    cliente.version_catalogo()
                except PresupuestoAgotado:
                    agotados.append(1)

        with mock.patch.object(cliente_http.requests, "get", side_effect=get_falso):
            hilos = [threading.Thread(target=trabajar) for _ in range(2)]
            for hilo in hilos:
                hilo.start()
            for hilo in hilos:
                hilo.join()
        self.assertEqual(cliente.estadisticas().solicitudes_realizadas, 50)
        self.assertEqual(len(agotados), 30)


class PruebaFuenteOffline(unittest.TestCase):
    def setUp(self):
        self.directorio = tempfile.mkdtemp(prefix="cripta_offline_")
        for cripta_id, nombre_sala in (("cripta-a", "Sala de A"), ("cripta-b", "Sala de B")):
            carpeta = os.path.join(self.directorio, cripta_id)
            os.makedirs(carpeta)
            self._escribir(carpeta, "cripta.json", {
                "id": cripta_id, "version": f"v-{cripta_id}", "salas_total": 1, "paginas": 1,
                "salas_por_pagina": 50, "sala_inicial": 1, "sala_salida": 1, "llave_salida": "x",
                "presupuesto_solicitudes": 5, "inventario_max": 3,
                "jugador": {"vida_max": 10, "ataque": 1, "defensa": 1, "velocidad": 100},
            })
            self._escribir(carpeta, "salas_pagina_1.json",
                           {"pagina": 1, "total_paginas": 1, "salas": [{"id": 1, "nombre": nombre_sala, "salidas": {}}]})
            self._escribir(carpeta, "contenido_1.json",
                           {"contenido": [{"sala": 1, "enemigos": [], "objetos": [f"itm_{cripta_id}"], "trampas": []}]})
            self._escribir(carpeta, "llaves.json", {"llaves": [
                {"id": f"itm_{cripta_id}", "sala": 1},
                {"id": "itm_especial", "sala": 2, "enemigo": "e-1"},
            ]})

    def tearDown(self):
        shutil.rmtree(self.directorio, ignore_errors=True)

    @staticmethod
    def _escribir(carpeta, nombre, datos):
        with open(os.path.join(carpeta, nombre), "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo)

    def test_no_mezcla_criptas(self):
        fuente = FuenteOffline(self.directorio)
        for cripta_id in ("cripta-a", "cripta-b"):
            self.assertEqual(fuente.datos_cripta(cripta_id).version, f"v-{cripta_id}")
            self.assertEqual(fuente.pagina_esqueleto(cripta_id, 1).salas[0].nombre,
                             "Sala de A" if cripta_id == "cripta-a" else "Sala de B")
            self.assertEqual(fuente.contenido(cripta_id, [1])[0].objetos, [f"itm_{cripta_id}"])
        self.assertEqual(fuente.estadisticas().solicitudes_realizadas, 0)

    def test_cripta_inexistente(self):
        with self.assertRaises(ErrorFuenteDatos):
            FuenteOffline(self.directorio).datos_cripta("cripta-z")

    def test_llaves_offline(self):
        fuente = FuenteOffline(self.directorio)
        llaves = fuente.llaves("cripta-a")
        self.assertEqual([x.id for x in llaves], ["itm_cripta-a", "itm_especial"])
        self.assertEqual(llaves[0].sala, 1)
        self.assertIsNone(llaves[0].enemigo)
        self.assertEqual(llaves[1].enemigo, "e-1")
        self.assertEqual(fuente.estadisticas().solicitudes_realizadas, 0)

    def test_llaves_offline_faltantes(self):
        os.remove(os.path.join(self.directorio, "cripta-b", "llaves.json"))
        with self.assertRaises(ErrorFuenteDatos) as contexto:
            FuenteOffline(self.directorio).llaves("cripta-b")
        self.assertIn("llaves", str(contexto.exception))


class PruebaAlmacenLlaves(unittest.TestCase):
    def setUp(self):
        self.directorio = tempfile.mkdtemp(prefix="cripta_almacen_")
        from cripta.adaptadores.almacen_disco import AlmacenCripta

        self.almacen = AlmacenCripta(self.directorio, "cripta-a")
        self.almacen.validar_version("v1")

    def tearDown(self):
        shutil.rmtree(self.directorio, ignore_errors=True)

    def test_guardar_y_cargar_por_version(self):
        from cripta.modelo.datos import UbicacionLlave

        llaves = [UbicacionLlave("itm_llave", 4), UbicacionLlave("itm_negra", 12, "e-1")]
        self.almacen.guardar_llaves(llaves, "v1")
        cargadas = self.almacen.cargar_llaves("v1")
        self.assertEqual(cargadas, llaves)
        self.assertIsNone(self.almacen.cargar_llaves("v2"))

    def test_la_version_nueva_borra_el_archivo(self):
        from cripta.modelo.datos import UbicacionLlave

        self.almacen.guardar_llaves([UbicacionLlave("itm_llave", 4)], "v1")
        self.assertFalse(self.almacen.validar_version("v2"))
        self.assertIsNone(self.almacen.cargar_llaves("v1"))
        self.assertIsNone(self.almacen.cargar_llaves("v2"))

    def test_el_esqueleto_conserva_el_costo(self):
        from cripta.modelo.datos import DatosSala, DatosSalida

        salas = [DatosSala(1, "Uno", [DatosSalida("N", 2, costo=250), DatosSalida("S", 1)])]
        self.almacen.guardar_esqueleto(salas)
        cargadas = self.almacen.cargar_esqueleto()
        self.assertEqual(cargadas[0].salidas[0].costo, 250)
        self.assertIsNone(cargadas[0].salidas[1].costo)


class PruebaContratoSalida(unittest.TestCase):
    def test_costo_opcional_desde_json(self):
        from cripta.modelo.datos import DatosSala

        sala = DatosSala.desde_json({
            "id": 1,
            "nombre": "Uno",
            "salidas": {"N": {"sala": 2, "costo": 250}, "S": {"sala": 3}},
        })
        self.assertEqual(sala.salidas[0].costo, 250)
        self.assertIsNone(sala.salidas[1].costo)


class _FuenteContada:
    """Fuente falsa: cuenta las solicitudes de contenido contra un presupuesto."""

    def __init__(self, restantes):
        self.restantes = restantes
        self.pedidas = []

    def solicitudes_restantes(self):
        return self.restantes

    def contenido(self, cripta_id, salas):
        from cripta.modelo.datos import ContenidoSala

        self.restantes -= 1
        self.pedidas.append(list(salas))
        return [ContenidoSala(sala) for sala in salas]


class _SinDisco:
    def tiene_contenido(self, sala):
        return False

    def guardar_contenido(self, contenidos):
        pass


class _CatalogoVacio:
    def registrar_necesarios(self, ids):
        pass

    def resolver_pendientes(self):
        pass


class PruebaReservaDePresupuesto(unittest.TestCase):
    """La precarga anticipada no gasta las últimas solicitudes; lo obligatorio sí puede."""

    def planificador(self, fuente):
        from cripta.controlador.precarga import PlanificadorPrecarga

        vecinos = lambda sala: [sala + 1] if sala < 30 else []  # un pasillo de salas 1 → 30
        return PlanificadorPrecarga(fuente, "prueba", _SinDisco(), _CatalogoVacio(), vecinos, lambda contenido: None)

    def test_anticipada_respeta_la_reserva(self):
        from cripta.controlador.precarga import RESERVA_SOLICITUDES

        fuente = _FuenteContada(RESERVA_SOLICITUDES)
        planificador = self.planificador(fuente)
        try:
            planificador.planificar(1)
            self.assertEqual(fuente.pedidas, [])  # solo queda la reserva: no anticipa
        finally:
            planificador.cerrar()
        fuente = _FuenteContada(RESERVA_SOLICITUDES + 1)
        planificador = self.planificador(fuente)
        try:
            planificador.planificar(1)
            planificador.cerrar()
            self.assertEqual(len(fuente.pedidas), 1)  # sí había para anticipar
        finally:
            planificador.cerrar()

    def test_lo_obligatorio_usa_la_reserva(self):
        fuente = _FuenteContada(1)
        planificador = self.planificador(fuente)
        try:
            planificador.asegurar(5)
            self.assertEqual(fuente.pedidas[0][0], 5)
        finally:
            planificador.cerrar()


if __name__ == "__main__":
    unittest.main()
