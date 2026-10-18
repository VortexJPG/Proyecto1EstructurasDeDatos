"""Modo --replay.                                                      [Persona B]

§4.11 y §6: reproduce una partida completa SIN la vista. Primero compara las
versiones de cripta y catálogo del log con las disponibles; si no coinciden,
lanza ``ErrorReplayIncompatible`` en vez de reproducir con datos distintos.
"""

from __future__ import annotations

from cripta.adaptadores.bitacora_replay import LectorReplay, ErrorReplayIncompatible
from cripta.controlador.controlador import Controlador, OpcionesEjecucion


class ReproductorReplay:
    def __init__(self, ruta_log: str, fuente, opciones: OpcionesEjecucion) -> None:
        self.ruta_log = ruta_log
        self.fuente = fuente
        self.opciones = opciones
        self._lector = LectorReplay(ruta_log)
        encabezado = self._lector.encabezado()
        self._encabezado = encabezado
        self._controlador = Controlador(fuente, opciones, None)

    def verificar_compatibilidad(self, encabezado) -> None:
        # versiones disponibles desde la fuente
        try:
            version_cripta = self.fuente.version_cripta(encabezado.cripta_id)
        except Exception as exc:
            raise ErrorReplayIncompatible(f"no se pudo verificar versión de cripta: {exc}")
        try:
            version_catalogo = self.fuente.version_catalogo()
        except Exception as exc:
            raise ErrorReplayIncompatible(f"no se pudo verificar versión de catálogo: {exc}")
        if version_cripta != encabezado.version_cripta:
            raise ErrorReplayIncompatible(
                f"versión de cripta incompatible: log={encabezado.version_cripta}, disponible={version_cripta}"
            )
        if version_catalogo != encabezado.version_catalogo:
            raise ErrorReplayIncompatible(
                f"versión de catálogo incompatible: log={encabezado.version_catalogo}, disponible={version_catalogo}"
            )

    def ejecutar(self):
        encabezado = self._encabezado
        self.verificar_compatibilidad(encabezado)
        self._controlador.preparar_cripta(encabezado.cripta_id)
        self._controlador.iniciar_partida(encabezado.nombre_jugador, encabezado.semilla, False)
        self.acciones_reproducidas = 0
        self.acciones_rechazadas = 0
        for accion in self._lector.acciones():
            resultado = self._controlador.ejecutar_accion(accion)
            self.acciones_reproducidas += 1
            if not resultado.aceptada:
                # En el log solo hay acciones aceptadas: si alguna se rechaza, la
                # reproducción ya no es fiel y conviene saberlo.
                self.acciones_rechazadas += 1
        self._controlador.cerrar_recursos()  # un replay no suma a la tabla de puntajes
        juego = self._controlador.juego
        return juego.resumen() if juego is not None else None

    def describir(self, resumen) -> str:
        """Resumen legible para la terminal."""
        if resumen is None:
            return "El replay no produjo ninguna partida."
        lineas = [
            f"Replay de {self.ruta_log}",
            f"  Cripta {resumen.cripta_id} (versión {resumen.version_cripta}), semilla {self._encabezado.semilla}",
            f"  Acciones reproducidas: {self.acciones_reproducidas}",
            f"  Resultado: {resumen.estado.value} | reloj final: {resumen.tiempo_final} | "
            f"acciones del jugador: {resumen.acciones_ejecutadas} | enemigos derrotados: {resumen.enemigos_derrotados}",
            f"  {self._controlador.reporte_red()}",
        ]
        if self.acciones_rechazadas:
            lineas.append(f"  ATENCIÓN: {self.acciones_rechazadas} acciones del log fueron rechazadas; la reproducción no es fiel.")
        return "\n".join(lineas)
