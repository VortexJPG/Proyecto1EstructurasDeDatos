"""Pruebas de integración A ↔ B: controlador, precarga, caché, guardado y replay.

Usan el controlador real con ``FuenteOffline`` sobre ``datos_ejemplo/`` (sin
red) y un directorio temporal para la caché, los logs y las partidas.
"""

import os
import random
import shutil
import tempfile
import unittest

from cripta.adaptadores.fuente_offline import FuenteOffline
from cripta.adaptadores.guardado import GuardadoBinario, GuardadoJSON
from cripta.controlador.controlador import Controlador, OpcionesEjecucion
from cripta.controlador.replay import ReproductorReplay
from cripta.estructuras.ordenamiento import ordenar
from cripta.modelo.acciones import Accion, TipoAccion

DATOS_EJEMPLO = os.path.join(os.path.dirname(__file__), "..", "datos_ejemplo")


def evento_orden(evento):
    return (evento.tiempo, evento.secuencia)


def estado_normalizado(juego):
    estado = juego.exportar_estado("catalogo")
    estado.eventos = ordenar(estado.eventos, clave=evento_orden)
    return estado


class BaseIntegracion(unittest.TestCase):
    def setUp(self):
        self.directorio = tempfile.mkdtemp(prefix="cripta_test_")

    def tearDown(self):
        shutil.rmtree(self.directorio, ignore_errors=True)

    def controlador(self, cache_size=25, vida=None):
        opciones = OpcionesEjecucion(directorio_datos=self.directorio, cache_size=cache_size)
        controlador = Controlador(FuenteOffline(DATOS_EJEMPLO), opciones, None)
        controlador.preparar_cripta("cripta-01")
        if vida is not None:
            controlador._datos.jugador.vida_max = vida
        return controlador


PARTIDA = [
    Accion(TipoAccion.RECOGER, objetivo="o-1-0"),
    Accion(TipoAccion.MOVER, direccion="N"),
    Accion(TipoAccion.RECOGER, objetivo="o-2-0"),
    Accion(TipoAccion.EQUIPAR, objetivo="o-2-0"),
    Accion(TipoAccion.ATACAR, objetivo="e-201"),
    Accion(TipoAccion.ATACAR, objetivo="e-202"),
    Accion(TipoAccion.MOVER, direccion="N"),
    Accion(TipoAccion.RECOGER, objetivo="o-3-0"),
]


class PruebaReplay(BaseIntegracion):
    def test_replay_reproduce_la_misma_partida(self):
        controlador = self.controlador()
        controlador.iniciar_partida("Prueba", 11, registrar_replay=True)
        for accion in PARTIDA[:5]:
            self.assertTrue(controlador.ejecutar_accion(accion).aceptada, accion)
        original = estado_normalizado(controlador.juego)
        ruta_log = controlador._ruta_log
        controlador.cerrar_recursos()

        reproductor = ReproductorReplay(ruta_log, FuenteOffline(DATOS_EJEMPLO),
                                        OpcionesEjecucion(directorio_datos=self.directorio, cache_size=25))
        resumen = reproductor.ejecutar()
        self.assertEqual(reproductor.acciones_rechazadas, 0)
        self.assertEqual(estado_normalizado(reproductor._controlador.juego), original)
        self.assertEqual(resumen.acciones_ejecutadas, 5)


class PruebaGuardado(BaseIntegracion):
    def test_guardar_cargar_y_continuar_igual(self):
        controlador = self.controlador(vida=500)
        controlador.iniciar_partida("Prueba", 5, registrar_replay=False)
        for accion in PARTIDA[:5]:
            self.assertTrue(controlador.ejecutar_accion(accion).aceptada)
        ruta = os.path.join(self.directorio, "partida.sav")
        controlador.guardar_partida(ruta)
        # Binario y JSON guardan el mismo estado.
        self.assertEqual(GuardadoBinario().cargar(ruta), GuardadoJSON().cargar(ruta + ".json"))
        # Una sala se puede leer sola desde el índice del archivo.
        self.assertEqual(GuardadoBinario().cargar_sala(ruta, 2).id, 2)
        self.assertIsNone(GuardadoBinario().cargar_sala(ruta, 999))

        for accion in PARTIDA[5:]:
            controlador.ejecutar_accion(accion)
        continuacion = estado_normalizado(controlador.juego)

        controlador.cargar_partida(ruta)
        for accion in PARTIDA[5:]:
            controlador.ejecutar_accion(accion)
        self.assertEqual(estado_normalizado(controlador.juego), continuacion)
        controlador.cerrar_recursos()


class PruebaVariasPaginas(BaseIntegracion):
    """Ninguna cripta publicada tiene más de una página de esqueleto; la de la
    revisión podría tenerla. Cripta inventada: 5 salas en línea, 2 por página."""

    def crear_paquete(self):
        import json

        paquete = os.path.join(self.directorio, "paquete", "cripta-larga")
        os.makedirs(paquete)

        def escribir(nombre, datos):
            with open(os.path.join(paquete, nombre), "w", encoding="utf-8") as archivo:
                json.dump(datos, archivo, ensure_ascii=False)

        escribir("cripta.json", {
            "id": "cripta-larga", "version": "v1", "salas_total": 5, "paginas": 3, "salas_por_pagina": 2,
            "sala_inicial": 1, "sala_salida": 5, "llave_salida": "itm_llave", "presupuesto_solicitudes": 20,
            "inventario_max": 5, "jugador": {"vida_max": 50, "ataque": 6, "defensa": 2, "velocidad": 100},
        })
        salas = []
        for i in range(1, 6):
            salidas = {}
            if i > 1:
                salidas["S"] = {"sala": i - 1}
            if i < 5:
                salidas["N"] = {"sala": i + 1}
                if i == 4:
                    salidas["N"].update({"cerrada": True, "llave": "itm_llave"})
            salas.append({"id": i, "nombre": f"Sala {i}", "salidas": salidas})
        for pagina in range(1, 4):
            escribir(f"salas_pagina_{pagina}.json",
                     {"pagina": pagina, "total_paginas": 3, "salas": salas[(pagina - 1) * 2: pagina * 2]})
        contenido = [{"sala": i, "enemigos": [], "objetos": [], "trampas": []} for i in range(1, 6)]
        contenido[1]["objetos"] = ["itm_llave"]
        escribir("contenido_1-5.json", {"contenido": contenido})
        escribir("catalogo_lote_1.json", {"entidades": [
            {"id": "itm_llave", "nombre": "Llave", "clase": "llave", "peso": 1, "valor": 0}]})
        escribir("catalogo_version.json", {"version": "c1"})
        return os.path.dirname(paquete)

    def test_esqueleto_en_tres_paginas(self):
        fuente = FuenteOffline(self.crear_paquete())
        controlador = Controlador(fuente, OpcionesEjecucion(directorio_datos=self.directorio, cache_size=25), None)
        controlador.preparar_cripta("cripta-larga")
        self.assertEqual(len(controlador._mapa), 5)
        controlador.iniciar_partida("Prueba", 1, registrar_replay=False)
        for accion in (
            Accion(TipoAccion.MOVER, direccion="N"),
            Accion(TipoAccion.RECOGER, objetivo="o-2-0"),
            Accion(TipoAccion.MOVER, direccion="N"),
            Accion(TipoAccion.MOVER, direccion="N"),
            Accion(TipoAccion.ABRIR, direccion="N"),
            Accion(TipoAccion.MOVER, direccion="N"),
        ):
            self.assertTrue(controlador.ejecutar_accion(accion).aceptada, accion)
        self.assertEqual(controlador.juego.estado.value, "victoria")
        controlador.cerrar_recursos()


class PruebaCacheChica(BaseIntegracion):
    def verificar_fijadas(self, controlador):
        """Toda ficha que el modelo usa está fijada en la LRU de Persona B."""
        juego = controlador.juego
        cache = controlador._catalogo.cache
        for tipo_id, cantidad in juego._fijadas.pares():
            self.assertTrue(cache.esta_fijada(tipo_id), tipo_id)
            self.assertEqual(cache._tabla.obtener(tipo_id).refs, cantidad, tipo_id)

    def test_cache_de_dos_fichas_no_desaloja_las_que_estan_en_uso(self):
        controlador = self.controlador(cache_size=2, vida=500)
        controlador.iniciar_partida("Prueba", 3, registrar_replay=False)
        for accion in PARTIDA:
            controlador.ejecutar_accion(accion)
            self.verificar_fijadas(controlador)
        self.assertGreater(controlador._catalogo.cache.desalojos, 0)
        controlador.cerrar_recursos()

    def test_partida_aleatoria_con_retrocesos(self):
        for semilla in (1, 2, 3):
            controlador = self.controlador(cache_size=3, vida=120)
            controlador.iniciar_partida("Prueba", semilla, registrar_replay=False)
            juego = controlador.juego
            azar = random.Random(semilla)
            for _ in range(150):
                if juego.esta_terminada():
                    break
                sala = juego.jugador.sala
                opciones = [Accion(TipoAccion.ESPERAR), Accion(TipoAccion.RETROCEDER)]
                for direccion in "NSEO":
                    if sala.salida(direccion) is not None:
                        opciones.append(Accion(TipoAccion.MOVER, direccion=direccion))
                        opciones.append(Accion(TipoAccion.ABRIR, direccion=direccion))
                for enemigo in sala.enemigos:
                    opciones.extend([Accion(TipoAccion.ATACAR, objetivo=enemigo.id)] * 3)
                for objeto in sala.objetos_suelo:
                    opciones.append(Accion(TipoAccion.RECOGER, objetivo=objeto.id))
                for objeto in juego.jugador.inventario:
                    opciones.append(Accion(TipoAccion.USAR, objetivo=objeto.id))
                    opciones.append(Accion(TipoAccion.EQUIPAR, objetivo=objeto.id))
                controlador.ejecutar_accion(azar.choice(opciones))
                self.verificar_fijadas(controlador)
            controlador.cerrar_recursos()


if __name__ == "__main__":
    unittest.main()
