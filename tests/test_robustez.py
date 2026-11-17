"""Partidas al azar sobre todas las criptas del paquete offline (robustez).

Respuesta a la revisión de la Parte I ("se encontró un bug que no logré
reproducir"): en vez de probar casos sueltos, se juegan partidas con acciones
al azar (mover, abrir, atacar, recoger, usar, equipar, soltar, esperar,
retroceder, «ir a», guardar/cargar e ``historia``) y se revisan invariantes:

1. Ninguna excepción.
2. El pergamino deja el estado EXACTAMENTE como antes de la acción revertida
   (sin contar lo que §2.11 excluye: pergaminos, números "#n" de enemigos y el
   contador de objetos soltados; los eventos se comparan por (tiempo, secuencia)).
3. Guardar y cargar no cambia el estado.
4. ``historia`` nunca falla para instantes y acciones válidos.
5. El ``partida.log`` se reproduce con ``--replay`` y da el mismo estado final.

Es determinista: mismas semillas ⇒ mismas partidas. El fuzz largo
(25 semillas x 250 acciones por cripta) se corrió aparte sin errores.
"""

import copy
import os
import random
import shutil
import tempfile
import unittest

from cripta.adaptadores.fuente_offline import FuenteOffline
from cripta.controlador.controlador import Controlador, OpcionesEjecucion
from cripta.controlador.replay import ReproductorReplay
from cripta.modelo.acciones import Accion, TipoAccion
from cripta.modelo.objetos import ClaseObjeto

RAIZ = os.path.join(os.path.dirname(__file__), "..")
PAQUETES = [(os.path.join(RAIZ, "datos_ejemplo"), c) for c in ("cripta-01", "cripta-02", "cripta-03", "cripta-04")] + \
           [(os.path.join(RAIZ, "datos_ejemplo_p2"), c) for c in ("cripta-05", "cripta-06")]


def normalizado(juego):
    estado = copy.deepcopy(juego.exportar_estado("x"))
    pergaminos = []
    for objeto in list(estado.jugador.inventario) + [o for s in estado.salas for o in s.objetos_suelo]:
        if objeto.tipo not in pergaminos and juego.fichas.obtener(objeto.tipo).clase == ClaseObjeto.PERGAMINO.value:
            pergaminos.append(objeto.tipo)
    estado.jugador.inventario = [o for o in estado.jugador.inventario if o.tipo not in pergaminos]
    for sala in estado.salas:
        sala.objetos_suelo = [o for o in sala.objetos_suelo if o.tipo not in pergaminos]
        for enemigo in sala.enemigos:
            enemigo.numero = 0
    estado.objetos_generados = 0
    estado.eventos = sorted(estado.eventos, key=lambda e: (e.tiempo, e.secuencia))
    estado.linea = None
    return estado


def accion_al_azar(juego, azar):
    jugador = juego.jugador
    sala = jugador.sala
    tirada = azar.random()
    if tirada < 0.40:
        salidas = [s for s in sala.salidas if s is not None]
        if salidas:
            return Accion(TipoAccion.MOVER, direccion=azar.choice(salidas).direccion)
    if tirada < 0.47:
        cerradas = [s for s in sala.salidas if s is not None and s.puerta is not None and s.puerta.cerrada]
        if cerradas:
            return Accion(TipoAccion.ABRIR, direccion=azar.choice(cerradas).direccion)
    if tirada < 0.62:
        enemigos = juego.enemigos_en_sala()
        if enemigos:
            return Accion(TipoAccion.ATACAR, objetivo=azar.choice(enemigos).id)
    if tirada < 0.72:
        suelo = sala.objetos_suelo.a_lista()
        if suelo:
            return Accion(TipoAccion.RECOGER, objetivo=azar.choice(suelo).id)
    if tirada < 0.84:
        inventario = [o for o in jugador.inventario]
        if inventario:
            tipo = azar.choice((TipoAccion.USAR, TipoAccion.EQUIPAR, TipoAccion.SOLTAR))
            return Accion(tipo, objetivo=azar.choice(inventario).id)
    if tirada < 0.90:
        return Accion(TipoAccion.RETROCEDER)
    return Accion(TipoAccion.ESPERAR)


class PruebaPartidasAlAzar(unittest.TestCase):
    SEMILLAS = (1, 2)
    PASOS = 120

    def jugar(self, paquete, cripta, semilla, directorio):
        controlador = Controlador(
            FuenteOffline(paquete),
            OpcionesEjecucion(directorio_datos=os.path.join(directorio, "d"), cache_size=8, forzar=True, checkpoint_cada=7),
            None,
        )
        controlador.preparar_cripta(cripta)
        controlador._datos.jugador.vida_max = max(controlador._datos.jugador.vida_max, 400)
        controlador.iniciar_partida("Azar", semilla, True)
        azar = random.Random(semilla * 31 + 7)
        pila = []
        cargo = False
        for paso in range(self.PASOS):
            juego = controlador.juego
            if juego.esta_terminada():
                break
            tirada = azar.random()
            if tirada < 0.05:
                exploradas = [s.id for s in juego.mapa if juego.conocimiento.explorada(s)]
                antes = juego.jugador.acciones_ejecutadas
                controlador.ir_a(str(azar.choice(exploradas)))
                if controlador.juego.jugador.acciones_ejecutadas != antes:
                    pila.clear()
                continue
            if tirada < 0.08 and not cargo:
                ruta = os.path.join(directorio, "p.sav")
                antes = normalizado(controlador.juego)
                controlador.guardar_partida(ruta)
                controlador.cargar_partida(ruta)
                self.assertEqual(normalizado(controlador.juego), antes, f"paso {paso}: guardar/cargar")
                cargo = True
                pila.clear()
                continue
            if tirada < 0.11 and controlador.timeline.acciones:
                controlador.consultar_historia(f"#{azar.randint(1, len(controlador.timeline.acciones))}")
                continue
            if tirada < 0.13:
                controlador.consultar_historia(str(azar.randint(0, controlador.juego.reloj)))
                continue
            accion = accion_al_azar(juego, azar)
            foto = normalizado(juego) if accion.tipo is not TipoAccion.RETROCEDER else None
            if not controlador.ejecutar_accion(accion).aceptada:
                continue
            if accion.tipo is TipoAccion.RETROCEDER:
                if pila:
                    self.assertEqual(normalizado(controlador.juego), pila.pop(), f"paso {paso}: retroceso")
            else:
                pila.append(foto)
                if len(pila) > 5:
                    pila.pop(0)
        ruta_log = controlador._ruta_log
        final = normalizado(controlador.juego)
        controlador.cerrar_recursos()
        if not cargo:  # cargar cierra el log (P1 §4.11), así que solo se reproduce si no hubo carga
            reproductor = ReproductorReplay(
                ruta_log, FuenteOffline(paquete),
                OpcionesEjecucion(directorio_datos=os.path.join(directorio, "r"), cache_size=8, forzar=True),
            )
            reproductor.ejecutar()
            self.assertEqual(reproductor.acciones_rechazadas, 0)
            self.assertEqual(normalizado(reproductor._controlador.juego), final, "replay")

    def test_partidas_al_azar_sin_errores(self):
        for paquete, cripta in PAQUETES:
            for semilla in self.SEMILLAS:
                with self.subTest(cripta=cripta, semilla=semilla):
                    directorio = tempfile.mkdtemp(prefix="cripta_azar_")
                    try:
                        self.jugar(paquete, cripta, semilla, directorio)
                    finally:
                        shutil.rmtree(directorio, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
