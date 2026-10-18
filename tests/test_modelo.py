"""Pruebas del modelo (Persona A).

Usan dos criptas:
- ``cripta-01`` real (``datos_ejemplo/``), leída con los ``desde_json`` de
  ``modelo/datos.py`` (Persona B).
- Una cripta de prueba construida aquí con los DTOs, con todos los efectos de
  §2.10: veneno, velocidad, antorcha, regeneración, trampas y cierre de puerta.

Dependen de ``TablaOrdenada`` y ``ordenar`` (Persona B): hasta que estén
implementados, estas pruebas fallan con NotImplementedError.
"""

import json
import os
import random
import unittest

from cripta.estructuras.ordenamiento import ordenar
from cripta.estructuras.tabla_ordenada import TablaOrdenada
from cripta.modelo.acciones import Accion, TipoAccion
from cripta.modelo.datos import (
    ColocacionEnemigo,
    ColocacionTrampa,
    ContenidoSala,
    DatosCripta,
    DatosSala,
    DatosSalida,
    EstadisticasIniciales,
    Ficha,
    PaginaEsqueleto,
)
from cripta.modelo.eventos import TipoEvento
from cripta.modelo.juego import EstadoPartida, Juego
from cripta.modelo.mapa import Mapa
from cripta.modelo.objetos import ClaseObjeto
from cripta.modelo.puertos import FichaNoDisponible, ProveedorFichas

DIRECTORIO_CRIPTA_01 = os.path.join(os.path.dirname(__file__), "..", "datos_ejemplo", "cripta-01")


# =============================================================================
# Utilidades
# =============================================================================


class ProveedorContador(ProveedorFichas):
    """Fichas en memoria que además cuentan fijar / liberar (para verificar §4.4)."""

    def __init__(self, fichas):
        self._fichas = TablaOrdenada()
        self.fijaciones = TablaOrdenada()
        for ficha in fichas:
            self._fichas.insertar(ficha.id, ficha)

    def obtener(self, tipo_id):
        ficha = self._fichas.obtener(tipo_id)
        if ficha is None:
            raise FichaNoDisponible(tipo_id)
        return ficha

    def fijar(self, tipo_id):
        self.fijaciones.insertar(tipo_id, self.fijaciones.obtener(tipo_id, 0) + 1)

    def liberar(self, tipo_id):
        cantidad = self.fijaciones.obtener(tipo_id, 0)
        if cantidad <= 0:
            raise AssertionError(f"liberar sin fijar: {tipo_id}")
        self.fijaciones.insertar(tipo_id, cantidad - 1)


def ficha(id, clase, nombre, **campos):
    resultado = Ficha(id, clase, nombre)
    for campo, valor in campos.items():
        setattr(resultado, campo, valor)
    return resultado


def salida(direccion, destino, cerrada=False, llave=None, cierre=None):
    return DatosSalida(direccion, destino, cerrada, llave, cierre)


FICHAS_PRUEBA = [
    ficha("ent_arana", "enemigo", "Araña", vida_max=10, ataque=3, defensa=0, velocidad=100,
          comportamiento="errante", veneno=2, regeneracion=1, suelta=["itm_pergamino", "itm_pocion"]),
    ficha("ent_lobo", "enemigo", "Lobo", vida_max=8, ataque=4, defensa=0, velocidad=120,
          comportamiento="rastreador", suelta=["itm_pocion"]),
    ficha("ent_golem", "enemigo", "Gólem", vida_max=30, ataque=2, defensa=3, velocidad=80,
          comportamiento="guardián", regeneracion=2),
    ficha("ent_murcielago", "enemigo", "Murciélago", vida_max=5, ataque=1, defensa=0, velocidad=200,
          comportamiento="errante"),
    ficha("itm_pergamino", "pergamino_retroceso", "Pergamino", peso=1, valor=40),
    ficha("itm_pocion", "pocion", "Poción", peso=1, valor=10, cura=10),
    ficha("itm_pocion_vel", "pocion", "Poción veloz", peso=1, valor=30, modificador_velocidad=50, duracion=300),
    ficha("itm_antidoto", "antidoto", "Antídoto", peso=1, valor=12),
    ficha("itm_antorcha", "antorcha", "Antorcha", peso=2, valor=5, duracion=500),
    ficha("itm_espada", "arma", "Espada", peso=5, valor=50, ataque_bonus=4),
    ficha("itm_escudo", "armadura", "Escudo", peso=6, valor=35, defensa_bonus=2),
    ficha("llave_azul", "llave", "Llave azul", peso=1, valor=0),
    ficha("llave_oro", "llave", "Llave de oro", peso=1, valor=0),
    ficha("trp_pinchos", "trampa", "Pinchos", dano=2),
    ficha("trp_dardo", "trampa", "Dardo envenenado", dano=1, veneno=1, rearme=150),
]


def esqueleto_prueba():
    return [
        DatosSala(1, "Inicio", [salida("N", 2), salida("E", 3)]),
        DatosSala(2, "Norte", [salida("S", 1), salida("N", 4, cerrada=True, llave="llave_azul", cierre=300)]),
        DatosSala(3, "Este", [salida("O", 1), salida("E", 5)]),
        DatosSala(4, "Bóveda", [salida("S", 2), salida("E", 6, cerrada=True, llave="llave_oro")]),
        DatosSala(5, "Pasillo", [salida("O", 3)]),
        DatosSala(6, "Salida", [salida("O", 4)]),
    ]


def contenido_prueba():
    return [
        ContenidoSala(1, [], ["itm_pergamino", "itm_pergamino", "itm_pocion_vel", "itm_antidoto", "itm_antorcha"], []),
        ContenidoSala(2, [ColocacionEnemigo("a-1", "ent_arana")], ["llave_azul", "itm_espada"],
                      [ColocacionTrampa("t-1", "trp_pinchos")]),
        ContenidoSala(3, [ColocacionEnemigo("l-2", "ent_lobo"), ColocacionEnemigo("l-1", "ent_lobo", 5)],
                      ["itm_pocion"], []),
        ContenidoSala(4, [ColocacionEnemigo("g-1", "ent_golem", 20)], ["llave_oro"], []),
        ContenidoSala(5, [ColocacionEnemigo("m-1", "ent_murcielago")], ["itm_escudo"],
                      [ColocacionTrampa("t-2", "trp_dardo")]),
        ContenidoSala(6, [], [], []),
    ]


def datos_prueba(vida=60, inventario_max=4):
    return DatosCripta("prueba", "v1", 6, 1, 50, 1, 6, "llave_oro", 99, inventario_max,
                       EstadisticasIniciales(vida, 6, 1, 100))


def crear_juego_prueba(semilla=1, vida=60, inventario_max=4):
    datos = datos_prueba(vida, inventario_max)
    proveedor = ProveedorContador(FICHAS_PRUEBA)
    mapa = Mapa.construir(datos, esqueleto_prueba())
    for contenido in contenido_prueba():
        mapa.incorporar_contenido(contenido, proveedor)
    juego = Juego(datos, mapa, proveedor, semilla, "Prueba")
    juego.iniciar()
    return juego, proveedor


def leer_json(nombre):
    with open(os.path.join(DIRECTORIO_CRIPTA_01, nombre), encoding="utf-8") as archivo:
        return json.load(archivo)


def crear_juego_cripta01(semilla=1, vida=None):
    datos = DatosCripta.desde_json(leer_json("cripta.json"))
    if vida is not None:
        datos.jugador.vida_max = vida
    pagina = PaginaEsqueleto.desde_json(leer_json("salas_pagina_1.json"))
    entidades = leer_json("catalogo_lote_1.json")["entidades"] + leer_json("catalogo_lote_2.json")["entidades"]
    proveedor = ProveedorContador([Ficha.desde_json(e) for e in entidades])
    mapa = Mapa.construir(datos, pagina.salas)
    for contenido in leer_json("contenido_1-6.json")["contenido"]:
        mapa.incorporar_contenido(ContenidoSala.desde_json(contenido), proveedor)
    juego = Juego(datos, mapa, proveedor, semilla, "Prueba")
    juego.iniciar()
    return juego, proveedor


def tiempo_y_secuencia(evento):
    return (evento.tiempo, evento.secuencia)


def estado_comparable(juego):
    """``exportar_estado`` normalizado para comparar dos momentos de la partida.

    - El número "#n" de los enemigos es solo de interfaz y no se revierte.
    - ``objetos_generados`` no se revierte (ver objetos.py).
    - Los eventos se ordenan: el orden interno del montículo puede variar.
    """
    estado = juego.exportar_estado("catalogo")
    for sala in estado.salas:
        for enemigo in sala.enemigos:
            enemigo.numero = 0
    estado.eventos = ordenar(estado.eventos, clave=tiempo_y_secuencia)
    estado.objetos_generados = 0
    return estado


def accion(tipo, direccion=None, objetivo=None):
    return Accion(tipo, direccion, objetivo)


# =============================================================================
# Pruebas
# =============================================================================


class PruebaReglasBasicas(unittest.TestCase):
    def test_inicio(self):
        juego, _ = crear_juego_prueba()
        self.assertEqual(juego.reloj, 0)
        self.assertEqual(juego.jugador.sala.id, 1)
        self.assertEqual(juego.jugador.sala.rastro, 0)
        self.assertEqual(juego.jugador.tiempo_siguiente, 0)
        self.assertEqual(juego.jugador.vida, 60)

    def test_puerta_compartida_cripta01(self):
        juego, _ = crear_juego_cripta01()
        ida = juego.mapa.sala(2).salida("E")
        vuelta = juego.mapa.sala(5).salida("O")
        self.assertIsNotNone(ida.puerta)
        self.assertIs(ida.puerta, vuelta.puerta)
        self.assertTrue(ida.puerta.cerrada)
        self.assertEqual(juego.mapa.vecinos(2), [3, 1, 5])

    def test_activacion_en_orden_de_id(self):
        juego, _ = crear_juego_prueba()
        self.assertTrue(juego.ejecutar_accion(accion(TipoAccion.MOVER, "E")).aceptada)
        l1 = juego.enemigos.obtener("l-1")
        l2 = juego.enemigos.obtener("l-2")
        self.assertTrue(l1.activo and l2.activo)
        self.assertEqual((l1.numero, l2.numero), (1, 2))
        self.assertEqual(juego.jugador.tiempo_siguiente, 100)
        # Velocidad 120 → primera acción en 0 + 100*100//120 = 83; luego 83 + 83.
        self.assertEqual(l1.tiempo_siguiente, 166)
        self.assertLess(l1.evento_turno.secuencia, l2.evento_turno.secuencia)
        self.assertEqual(juego.mapa.sala(3).rastro, 0)

    def test_rechazos_no_consumen_tiempo(self):
        juego, _ = crear_juego_prueba(vida=500)
        antes = estado_comparable(juego)
        for invalida in (
            accion(TipoAccion.ABRIR, "N"),  # no hay puerta
            accion(TipoAccion.MOVER, "S"),  # no hay salida
            accion(TipoAccion.ATACAR, objetivo="a-1"),  # no está en la sala
            accion(TipoAccion.RECOGER, objetivo="o-2-0"),  # no está en este suelo
            accion(TipoAccion.SOLTAR, objetivo="o-1-0"),  # no está en el inventario
            accion(TipoAccion.RETROCEDER),  # no hay pergaminos
        ):
            resultado = juego.ejecutar_accion(invalida)
            self.assertFalse(resultado.aceptada, invalida)
            self.assertTrue(resultado.motivo)
        self.assertEqual(estado_comparable(juego), antes)
        # Abrir sin la llave correcta.
        juego.ejecutar_accion(accion(TipoAccion.MOVER, "N"))
        antes = estado_comparable(juego)
        resultado = juego.ejecutar_accion(accion(TipoAccion.ABRIR, "N"))
        self.assertFalse(resultado.aceptada)
        self.assertEqual(estado_comparable(juego), antes)

    def test_inventario_lleno(self):
        juego, _ = crear_juego_prueba(inventario_max=2)
        juego.ejecutar_accion(accion(TipoAccion.RECOGER, objetivo="o-1-2"))
        juego.ejecutar_accion(accion(TipoAccion.RECOGER, objetivo="o-1-3"))
        reloj = juego.reloj
        resultado = juego.ejecutar_accion(accion(TipoAccion.RECOGER, objetivo="o-1-4"))
        self.assertFalse(resultado.aceptada)
        self.assertEqual(juego.reloj, reloj)
        self.assertEqual(juego.jugador.acciones_ejecutadas, 2)

    def test_movimiento_pide_contenido(self):
        datos = datos_prueba()
        proveedor = ProveedorContador(FICHAS_PRUEBA)
        mapa = Mapa.construir(datos, esqueleto_prueba())
        mapa.incorporar_contenido(contenido_prueba()[0], proveedor)
        juego = Juego(datos, mapa, proveedor, 1, "Prueba")
        juego.iniciar()
        self.assertEqual(juego.sala_destino("e").id, 3)
        resultado = juego.ejecutar_accion(accion(TipoAccion.MOVER, "E"))
        self.assertFalse(resultado.aceptada)
        self.assertEqual(resultado.requiere_sala, 3)
        self.assertEqual(juego.reloj, 0)
        mapa.incorporar_contenido(contenido_prueba()[2], proveedor)
        self.assertTrue(juego.ejecutar_accion(accion(TipoAccion.MOVER, "E")).aceptada)

    def test_victoria_cripta01(self):
        juego, _ = crear_juego_cripta01(vida=1000)
        for paso in (
            accion(TipoAccion.MOVER, "N"),
            accion(TipoAccion.MOVER, "N"),
            accion(TipoAccion.MOVER, "N"),
            accion(TipoAccion.RECOGER, objetivo="o-4-0"),  # llave negra
            accion(TipoAccion.ABRIR, "E"),
            accion(TipoAccion.MOVER, "E"),
        ):
            self.assertTrue(juego.ejecutar_accion(paso).aceptada, paso)
        self.assertIs(juego.estado, EstadoPartida.VICTORIA)
        resumen = juego.resumen()
        self.assertEqual(resumen.acciones_ejecutadas, 6)
        self.assertFalse(juego.ejecutar_accion(accion(TipoAccion.ESPERAR)).aceptada)

    def test_derrota(self):
        juego, _ = crear_juego_cripta01(semilla=3)
        for _ in range(50):
            if juego.esta_terminada():
                break
            enemigos = juego.enemigos_en_sala()
            if juego.jugador.sala.id == 1:
                juego.ejecutar_accion(accion(TipoAccion.MOVER, "N"))
            elif enemigos:
                juego.ejecutar_accion(accion(TipoAccion.ESPERAR))
        self.assertIs(juego.estado, EstadoPartida.DERROTA)
        self.assertEqual(juego.jugador.vida, 0)
        self.assertIsNone(juego.jugador.evento_turno)


class PruebaInventario(unittest.TestCase):
    def test_equipar_mueve_al_frente_y_vistas(self):
        juego, _ = crear_juego_prueba(inventario_max=5)
        for objeto_id in ("o-1-4", "o-1-2", "o-1-3"):  # antorcha (2), poción veloz (1), antídoto (1)
            juego.ejecutar_accion(accion(TipoAccion.RECOGER, objetivo=objeto_id))
        juego.ejecutar_accion(accion(TipoAccion.MOVER, "N"))
        juego.ejecutar_accion(accion(TipoAccion.RECOGER, objetivo="o-2-1"))  # espada
        real = [objeto.id for objeto in juego.jugador.inventario]
        self.assertEqual(real, ["o-1-4", "o-1-2", "o-1-3", "o-2-1"])
        por_peso = [objeto.id for objeto in juego.vista_inventario("peso")]
        self.assertEqual(por_peso, ["o-1-2", "o-1-3", "o-1-4", "o-2-1"])  # estable en empates
        por_nombre = [objeto.id for objeto in juego.vista_inventario("nombre")]
        self.assertEqual(por_nombre, ["o-1-4", "o-1-3", "o-2-1", "o-1-2"])
        self.assertEqual([objeto.id for objeto in juego.jugador.inventario], real)  # sin cambios
        ataque = juego.jugador.ataque
        juego.ejecutar_accion(accion(TipoAccion.EQUIPAR, objetivo="o-2-1"))
        self.assertEqual(juego.jugador.inventario.actual().id, "o-1-4")
        self.assertEqual([objeto.id for objeto in juego.jugador.inventario][0], "o-2-1")
        self.assertEqual(juego.jugador.ataque, ataque + 4)
        juego.ejecutar_accion(accion(TipoAccion.SOLTAR, objetivo="o-2-1"))
        self.assertEqual(juego.jugador.ataque, ataque)
        self.assertIsNone(juego.jugador.arma)

    def test_cursor_da_la_vuelta(self):
        juego, _ = crear_juego_prueba()
        for objeto_id in ("o-1-2", "o-1-3", "o-1-4"):
            juego.ejecutar_accion(accion(TipoAccion.RECOGER, objetivo=objeto_id))
        inventario = juego.jugador.inventario
        self.assertEqual(inventario.actual().id, "o-1-2")
        self.assertEqual(inventario.retroceder().id, "o-1-4")
        self.assertEqual(inventario.avanzar().id, "o-1-2")
        inventario.ir_a("o-1-3")
        juego.ejecutar_accion(accion(TipoAccion.SOLTAR, objetivo="o-1-3"))
        self.assertEqual(inventario.actual().id, "o-1-4")


class PruebaEfectos(unittest.TestCase):
    def test_veneno_cinco_pulsos(self):
        juego, _ = crear_juego_prueba()
        juego.efectos.aplicar_veneno(juego.jugador, 3)
        for _ in range(7):
            juego.ejecutar_accion(accion(TipoAccion.ESPERAR))
        # Pulsos en 80, 160, 240, 320 y 400 → 15 de daño; después nada.
        self.assertEqual(juego.jugador.vida, 45)
        self.assertIsNone(juego.jugador.veneno)

    def test_antidoto_cancela_pulsos_futuros(self):
        juego, _ = crear_juego_prueba()
        juego.efectos.aplicar_veneno(juego.jugador, 3)
        juego.ejecutar_accion(accion(TipoAccion.ESPERAR))  # pulso en 80
        juego.ejecutar_accion(accion(TipoAccion.RECOGER, objetivo="o-1-3"))
        juego.ejecutar_accion(accion(TipoAccion.USAR, objetivo="o-1-3"))
        self.assertIsNone(juego.jugador.veneno)
        vida = juego.jugador.vida
        for _ in range(6):
            juego.ejecutar_accion(accion(TipoAccion.ESPERAR))
        self.assertEqual(juego.jugador.vida, vida)
        for evento in juego.agenda.pendientes():
            self.assertIsNot(evento.tipo, TipoEvento.PULSO_VENENO)

    def test_trampa_con_veneno_y_rearme(self):
        juego, _ = crear_juego_prueba(vida=500)
        juego.ejecutar_accion(accion(TipoAccion.MOVER, "E"))  # t=0
        juego.ejecutar_accion(accion(TipoAccion.MOVER, "E"))  # t=100, sala 5: dardo envenenado
        trampa = juego.mapa.sala(5).trampas[0]
        self.assertFalse(trampa.armada)
        self.assertIsNotNone(juego.jugador.veneno)
        self.assertEqual(trampa.evento_rearme.tiempo, 100 + 150)  # rearme de la ficha
        while juego.reloj <= 250:
            juego.ejecutar_accion(accion(TipoAccion.ESPERAR))
        self.assertTrue(trampa.armada)

    def test_velocidad_reescala_turno_pendiente(self):
        juego, _ = crear_juego_prueba(vida=500)
        juego.ejecutar_accion(accion(TipoAccion.MOVER, "E"))  # t=0; lobos actúan en 83
        lobo = juego.enemigos.obtener("l-1")
        self.assertEqual((juego.reloj, lobo.tiempo_siguiente), (100, 166))
        secuencia = lobo.evento_turno.secuencia
        juego.efectos.aplicar_velocidad(lobo, 30, 1000)  # 120 → 150
        self.assertEqual(lobo.tiempo_siguiente, 100 + (66 * 120 // 150))
        self.assertGreater(lobo.evento_turno.secuencia, secuencia)
        juego.efectos.terminar_velocidad(lobo.efecto_velocidad)  # 150 → 120
        self.assertEqual(lobo.tiempo_siguiente, 100 + (52 * 150 // 120))

    def test_pocion_de_velocidad_del_jugador(self):
        juego, _ = crear_juego_prueba()
        juego.ejecutar_accion(accion(TipoAccion.RECOGER, objetivo="o-1-2"))  # t=0 → 25
        juego.ejecutar_accion(accion(TipoAccion.USAR, objetivo="o-1-2"))  # vel 150 → 25 + 33
        self.assertEqual(juego.reloj, 58)
        for esperado in (124, 190, 256, 322):
            juego.ejecutar_accion(accion(TipoAccion.ESPERAR))
            self.assertEqual(juego.reloj, esperado)
        # En 325 termina el efecto: el turno de 388 se reescala a 325 + 63*150//100.
        juego.ejecutar_accion(accion(TipoAccion.ESPERAR))
        self.assertEqual(juego.reloj, 325 + 63 * 150 // 100)
        self.assertEqual(juego.jugador.velocidad, 100)

    def test_regeneracion_no_supera_maximo(self):
        juego, _ = crear_juego_prueba()
        golem = juego.enemigos.obtener("g-1")
        juego._activar_enemigos(juego.mapa.sala(4))
        self.assertEqual(golem.vida, 20)
        for _ in range(25):
            juego.ejecutar_accion(accion(TipoAccion.ESPERAR))
        self.assertEqual(golem.vida, golem.vida_max)

    def test_puerta_se_cierra_sola(self):
        juego, _ = crear_juego_prueba(vida=500)
        juego.ejecutar_accion(accion(TipoAccion.MOVER, "N"))
        juego.ejecutar_accion(accion(TipoAccion.RECOGER, objetivo="o-2-0"))  # llave azul
        abierta_en = juego.reloj
        self.assertTrue(juego.ejecutar_accion(accion(TipoAccion.ABRIR, "N")).aceptada)
        puerta = juego.mapa.sala(2).salida("N").puerta
        self.assertFalse(puerta.cerrada)
        self.assertEqual(puerta.evento_cierre.tiempo, abierta_en + 300)
        while juego.reloj <= abierta_en + 300:
            juego.ejecutar_accion(accion(TipoAccion.ESPERAR))
        self.assertTrue(puerta.cerrada)
        self.assertIs(juego.mapa.sala(4).salida("S").puerta, puerta)

    def test_rastreador_empate_menor_id(self):
        juego, _ = crear_juego_prueba()
        sala1, sala2, sala3 = juego.mapa.sala(1), juego.mapa.sala(2), juego.mapa.sala(3)
        sala2.rastro = 50
        sala3.rastro = 50
        self.assertIs(juego.ia.elegir_sala_por_rastro(sala1, 100), sala2)
        sala3.rastro = 60
        self.assertIs(juego.ia.elegir_sala_por_rastro(sala1, 100), sala3)
        self.assertIsNone(juego.ia.elegir_sala_por_rastro(sala1, 460))  # antigüedad >= 400

    def test_bitacora_maximo_20(self):
        juego, _ = crear_juego_prueba()
        for _ in range(40):
            juego.ejecutar_accion(accion(TipoAccion.ESPERAR))
        self.assertEqual(len(juego.mensajes), 20)
        self.assertEqual(len(list(juego.mensajes.ultimos())), 20)


class PruebaRetroceso(unittest.TestCase):
    def test_pergamino_excluido(self):
        juego, proveedor = crear_juego_prueba()
        juego.ejecutar_accion(accion(TipoAccion.RECOGER, objetivo="o-1-0"))
        juego.ejecutar_accion(accion(TipoAccion.RECOGER, objetivo="o-1-1"))
        self.assertEqual(juego.pergaminos_disponibles(), 2)
        self.assertTrue(juego.usar_pergamino().aceptada)
        # Se revirtió la segunda recolección, pero el pergamino recogido NO
        # vuelve al suelo: la cantidad solo refleja el que se usó (Apéndice B).
        self.assertEqual(juego.reloj, 25)
        self.assertEqual(juego.pergaminos_disponibles(), 1)
        self.assertIsNone(juego.mapa.sala(1).buscar_objeto_suelo("o-1-1"))
        self.assertEqual(juego.jugador.acciones_ejecutadas, 1)
        self.assertEqual(juego.reloj, juego.jugador.tiempo_siguiente)
        verificar_fijaciones(self, juego, proveedor)

    def test_dos_pergaminos_seguidos(self):
        juego, _ = crear_juego_prueba()
        juego.ejecutar_accion(accion(TipoAccion.RECOGER, objetivo="o-1-0"))
        juego.ejecutar_accion(accion(TipoAccion.RECOGER, objetivo="o-1-1"))
        juego.ejecutar_accion(accion(TipoAccion.ESPERAR))
        juego.ejecutar_accion(accion(TipoAccion.ESPERAR))
        self.assertEqual(juego.reloj, 250)
        self.assertTrue(juego.ejecutar_accion(accion(TipoAccion.RETROCEDER)).aceptada)
        self.assertEqual(juego.reloj, 150)
        self.assertTrue(juego.ejecutar_accion(accion(TipoAccion.RETROCEDER)).aceptada)
        self.assertEqual(juego.reloj, 50)
        self.assertEqual(juego.pergaminos_disponibles(), 0)
        self.assertFalse(juego.ejecutar_accion(accion(TipoAccion.RETROCEDER)).aceptada)

    def test_pergamino_soltado_por_enemigo_sobrevive(self):
        juego, proveedor = crear_juego_prueba(vida=500)
        juego.ejecutar_accion(accion(TipoAccion.RECOGER, objetivo="o-1-0"))
        juego.ejecutar_accion(accion(TipoAccion.RECOGER, objetivo="o-1-1"))
        juego.ejecutar_accion(accion(TipoAccion.MOVER, "N"))
        arana = juego.enemigos.obtener("a-1")
        while arana.esta_vivo():
            juego.ejecutar_accion(accion(TipoAccion.ATACAR, objetivo="a-1"))
        soltado = [o for o in juego.jugador.sala.objetos_suelo if o.es_pergamino()][0]
        juego.ejecutar_accion(accion(TipoAccion.RECOGER, objetivo=soltado.id))
        self.assertEqual(juego.pergaminos_disponibles(), 3)
        juego.ejecutar_accion(accion(TipoAccion.RETROCEDER))  # deshace la recolección
        juego.ejecutar_accion(accion(TipoAccion.RETROCEDER))  # deshace el golpe mortal
        self.assertTrue(arana.esta_vivo())
        # El pergamino soltado sobrevive en el inventario (§2.11) ...
        self.assertTrue(juego.jugador.inventario.contiene(soltado.id))
        self.assertEqual(juego.pergaminos_disponibles(), 1)
        # ... y si la araña vuelve a morir, lo que suelta recibe ids NUEVOS.
        while arana.esta_vivo():
            juego.ejecutar_accion(accion(TipoAccion.ATACAR, objetivo="a-1"))
        nuevo = [o for o in juego.jugador.sala.objetos_suelo if o.es_pergamino()][0]
        self.assertNotEqual(nuevo.id, soltado.id)
        juego.ejecutar_accion(accion(TipoAccion.RECOGER, objetivo=nuevo.id))
        self.assertEqual(juego.pergaminos_disponibles(), 2)
        verificar_fijaciones(self, juego, proveedor)
        verificar_invariantes(self, juego)

    def test_retroceso_completo_de_combate(self):
        juego, proveedor = crear_juego_cripta01(vida=1000)
        juego.ejecutar_accion(accion(TipoAccion.MOVER, "N"))  # ratas + trampa
        antes = estado_comparable(juego)
        juego.ejecutar_accion(accion(TipoAccion.ATACAR, objetivo="e-201"))
        despues = estado_comparable(juego)
        self.assertNotEqual(antes, despues)
        self.assertTrue(juego.historial.retroceder(juego))
        juego._reconciliar_fijaciones()
        self.assertEqual(estado_comparable(juego), antes)
        verificar_fijaciones(self, juego, proveedor)
        # El azar también se restauró: repetir la acción da exactamente lo mismo.
        juego.ejecutar_accion(accion(TipoAccion.ATACAR, objetivo="e-201"))
        self.assertEqual(estado_comparable(juego), despues)

    def test_maximo_cinco_intervalos(self):
        juego, _ = crear_juego_prueba()
        for _ in range(8):
            juego.ejecutar_accion(accion(TipoAccion.ESPERAR))
        self.assertEqual(len(juego.historial), 5)


def verificar_fijaciones(prueba, juego, proveedor):
    """Lo que el modelo tiene fijado coincide con el estado y con el proveedor."""
    deseadas = juego._fijaciones_deseadas()
    for tipo_id, cantidad in deseadas.pares():
        prueba.assertEqual(juego._fijadas.obtener(tipo_id, 0), cantidad, tipo_id)
    for tipo_id, cantidad in juego._fijadas.pares():
        prueba.assertEqual(deseadas.obtener(tipo_id, 0), cantidad, tipo_id)
    for tipo_id, cantidad in proveedor.fijaciones.pares():
        prueba.assertEqual(juego._fijadas.obtener(tipo_id, 0), cantidad, tipo_id)


def verificar_invariantes(prueba, juego):
    """Coherencia interna: agenda, listas de sala, inventario y efectos."""
    pendientes = list(juego.agenda.pendientes())
    prueba.assertEqual(len(pendientes), len(juego.agenda))
    turnos_jugador = [e for e in pendientes if e.tipo is TipoEvento.TURNO_JUGADOR]
    if not juego.esta_terminada():
        prueba.assertEqual(len(turnos_jugador), 1)
        prueba.assertIs(turnos_jugador[0], juego.jugador.evento_turno)
    turnos_enemigo = TablaOrdenada()
    for evento in pendientes:
        prueba.assertGreaterEqual(evento.tiempo, juego.reloj)
        if evento.tipo is TipoEvento.TURNO_ENEMIGO:
            prueba.assertFalse(turnos_enemigo.contiene(evento.objetivo.id), "dos turnos para un enemigo")
            turnos_enemigo.insertar(evento.objetivo.id, evento)
        elif evento.tipo in (TipoEvento.PULSO_VENENO, TipoEvento.PULSO_REGENERACION,
                             TipoEvento.FIN_VELOCIDAD, TipoEvento.APAGAR_ANTORCHA):
            prueba.assertTrue(evento.objetivo.activo, evento)
            prueba.assertTrue(evento.objetivo.portador.esta_vivo(), evento)
    for enemigo in juego.enemigos.valores():
        turno = turnos_enemigo.obtener(enemigo.id)
        if enemigo.esta_vivo():
            nodo = enemigo.nodo_en_sala
            prueba.assertIsNotNone(nodo, enemigo)
            prueba.assertIs(nodo.valor, enemigo)
            prueba.assertIn(enemigo, enemigo.sala.enemigos.a_lista())
            if enemigo.activo:
                prueba.assertIs(turno, enemigo.evento_turno, enemigo)
            else:
                prueba.assertIsNone(turno)
        else:
            prueba.assertIsNone(enemigo.nodo_en_sala)
            prueba.assertIsNone(turno)
            prueba.assertIsNone(enemigo.evento_turno)
    ids = TablaOrdenada()
    for sala in juego.mapa:
        for enemigo in sala.enemigos:
            prueba.assertIs(enemigo.sala, sala)
            prueba.assertTrue(enemigo.esta_vivo())
        for objeto in sala.objetos_suelo:
            prueba.assertFalse(ids.contiene(objeto.id), f"id repetido {objeto.id}")
            ids.insertar(objeto.id, True)
    inventario = juego.jugador.inventario
    for objeto in inventario:
        prueba.assertFalse(ids.contiene(objeto.id), f"id repetido {objeto.id}")
        ids.insertar(objeto.id, True)
        prueba.assertIs(inventario.obtener(objeto.id), objeto)
    for equipado in (juego.jugador.arma, juego.jugador.armadura):
        if equipado is not None:
            prueba.assertIs(inventario.obtener(equipado.id), equipado)


def acciones_candidatas(juego):
    """Todas las acciones que se le ocurrirían a un jugador (válidas o no)."""
    jugador = juego.jugador
    sala = jugador.sala
    candidatas = [accion(TipoAccion.ESPERAR), accion(TipoAccion.RETROCEDER), accion(TipoAccion.ATACAR, objetivo="x")]
    for direccion in "NSEO":
        if sala.salida(direccion) is not None:
            candidatas.append(accion(TipoAccion.MOVER, direccion))
            candidatas.append(accion(TipoAccion.ABRIR, direccion))
    for enemigo in sala.enemigos:
        candidatas.extend([accion(TipoAccion.ATACAR, objetivo=enemigo.id)] * 3)
    for objeto in sala.objetos_suelo:
        candidatas.append(accion(TipoAccion.RECOGER, objetivo=objeto.id))
    for objeto in jugador.inventario:
        for tipo in (TipoAccion.SOLTAR, TipoAccion.USAR, TipoAccion.EQUIPAR):
            candidatas.append(accion(tipo, objetivo=objeto.id))
    return candidatas


def mueve_pergamino(juego, elegida):
    """True si la acción recoge o suelta un pergamino (cambio que no se revierte)."""
    if elegida.tipo is TipoAccion.RECOGER:
        nodo = juego.jugador.sala.buscar_objeto_suelo(elegida.objetivo)
        return nodo is not None and nodo.valor.es_pergamino()
    if elegida.tipo is TipoAccion.SOLTAR:
        objeto = juego.jugador.inventario.obtener(elegida.objetivo)
        return objeto is not None and objeto.clase is ClaseObjeto.PERGAMINO
    return False


def partida_aleatoria(prueba, semilla, pasos):
    """Juega al azar verificando invariantes; devuelve el juego al final."""
    juego, proveedor = crear_juego_prueba(semilla=semilla, vida=120)
    azar = random.Random(semilla * 1000)
    for _ in range(pasos):
        if juego.esta_terminada():
            break
        antes = estado_comparable(juego)
        elegida = azar.choice(acciones_candidatas(juego))
        pergamino = mueve_pergamino(juego, elegida)
        generados = juego.objetos_generados
        resultado = juego.ejecutar_accion(elegida)
        if not resultado.aceptada:
            prueba.assertEqual(estado_comparable(juego), antes, f"rechazada pero cambió el estado: {elegida}")
            continue
        verificar_fijaciones(prueba, juego, proveedor)
        verificar_invariantes(prueba, juego)
        if elegida.tipo is TipoAccion.RETROCEDER or juego.esta_terminada() or pergamino:
            continue
        if azar.random() < 0.4:
            despues = estado_comparable(juego)
            genero_objetos = juego.objetos_generados != generados
            prueba.assertTrue(juego.historial.retroceder(juego))
            juego._reconciliar_fijaciones()
            prueba.assertEqual(estado_comparable(juego), antes, f"el retroceso no restauró: {elegida}")
            verificar_fijaciones(prueba, juego, proveedor)
            prueba.assertTrue(juego.ejecutar_accion(elegida).aceptada)
            if not genero_objetos:
                prueba.assertEqual(estado_comparable(juego), despues, f"rehacer dio otro resultado: {elegida}")
    return juego


class PruebaAleatoria(unittest.TestCase):
    def test_retroceso_y_rechazos_en_partidas_aleatorias(self):
        for semilla in range(1, 9):
            partida_aleatoria(self, semilla, 300)

    def test_determinismo(self):
        for semilla in (11, 12):
            primera = partida_aleatoria(self, semilla, 200)
            segunda = partida_aleatoria(self, semilla, 200)
            self.assertEqual(primera.exportar_estado("c"), segunda.exportar_estado("c"))
            self.assertEqual(list(primera.mensajes.ultimos()), list(segunda.mensajes.ultimos()))


class PruebaGuardado(unittest.TestCase):
    def test_exportar_y_reconstruir(self):
        juego, _ = crear_juego_prueba(vida=500)
        pasos = [
            accion(TipoAccion.RECOGER, objetivo="o-1-2"),
            accion(TipoAccion.USAR, objetivo="o-1-2"),  # efecto de velocidad activo
            accion(TipoAccion.MOVER, "N"),
            accion(TipoAccion.RECOGER, objetivo="o-2-1"),
            accion(TipoAccion.EQUIPAR, objetivo="o-2-1"),
            accion(TipoAccion.RECOGER, objetivo="o-2-0"),
            accion(TipoAccion.ABRIR, "N"),  # cierre automático pendiente
        ]
        for paso in pasos:
            self.assertTrue(juego.ejecutar_accion(paso).aceptada, paso)
        estado = juego.exportar_estado("catalogo")

        proveedor = ProveedorContador(FICHAS_PRUEBA)
        mapa = Mapa.construir(juego.datos, esqueleto_prueba())
        cargado = Juego.desde_estado(estado, juego.datos, mapa, proveedor)
        self.assertEqual(estado_comparable(cargado), estado_comparable(juego))
        verificar_fijaciones(self, cargado, proveedor)
        # Las dos partidas siguen exactamente igual.
        for paso in (accion(TipoAccion.MOVER, "N"), accion(TipoAccion.ESPERAR), accion(TipoAccion.ESPERAR)):
            juego.ejecutar_accion(paso)
            cargado.ejecutar_accion(paso)
            self.assertEqual(estado_comparable(cargado), estado_comparable(juego))


if __name__ == "__main__":
    unittest.main()
