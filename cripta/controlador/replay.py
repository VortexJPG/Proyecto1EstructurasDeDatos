"""Modo --replay.                                                      [Persona B]

§4.11 y §6: reproduce una partida completa SIN la vista. Primero compara las
versiones de cripta y catálogo del log con las disponibles; si no coinciden,
lanza ``ErrorReplayIncompatible`` en vez de reproducir con datos distintos.

Con ``--hasta T`` se detiene en el instante T y se imprime el mismo resumen
histórico que ``historia T``. Si el log termina antes de T, se muestra el
estado final e indica que la partida terminó antes.
"""

from __future__ import annotations

from cripta.adaptadores.bitacora_replay import LectorReplay, ErrorReplayIncompatible
from cripta.controlador.controlador import Controlador, OpcionesEjecucion
from cripta.modelo.timeline import ErrorReconstruccion, ResumenHistorico, formatear_resumen


class ReproductorReplay:
    def __init__(self, ruta_log: str, fuente, opciones: OpcionesEjecucion) -> None:
        self.ruta_log = ruta_log
        self.fuente = fuente
        self.opciones = opciones
        self._lector = LectorReplay(ruta_log)
        encabezado = self._lector.encabezado()
        self._encabezado = encabezado
        self._controlador = Controlador(fuente, opciones, None)
        self._hasta: int | None = None
        self._resumen_historico: ResumenHistorico | None = None
        self._termino_antes = False
        self._estado_final: str | None = None
        self._error_hasta: str | None = None

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

    def ejecutar(self, hasta: int | None = None):
        encabezado = self._encabezado
        self.verificar_compatibilidad(encabezado)
        self._controlador.preparar_cripta(encabezado.cripta_id)
        self._controlador.iniciar_partida(encabezado.nombre_jugador, encabezado.semilla, False)
        self._hasta = hasta
        self.acciones_reproducidas = 0
        self.acciones_rechazadas = 0
        for accion in self._lector.acciones():
            juego = self._controlador.juego
            if juego is None:
                break
            if hasta is not None and (juego.reloj >= hasta or juego.esta_terminada()):
                break
            resultado = self._controlador.ejecutar_accion(accion)
            self.acciones_reproducidas += 1
            if not resultado.aceptada:
                # En el log solo hay acciones aceptadas: si alguna se rechaza, la
                # reproducción ya no es fiel y conviene saberlo.
                self.acciones_rechazadas += 1
        if hasta is not None:
            self._preparar_resumen_hasta(hasta)
        self._controlador.cerrar_recursos()  # un replay no suma a la tabla de puntajes
        juego = self._controlador.juego
        return juego.resumen() if juego is not None else None

    def _preparar_resumen_hasta(self, hasta: int) -> None:
        juego = self._controlador.juego
        linea = self._controlador.timeline
        if juego is None or linea is None:
            self._error_hasta = "La línea de tiempo no está disponible en el replay."
            return
        try:
            if juego.reloj > hasta:
                estado = linea.estado_en_tiempo(hasta, juego.reloj)
            else:
                estado = juego
            self._resumen_historico = linea.resumen(estado, f"t={hasta}")
        except ErrorReconstruccion as exc:
            self._error_hasta = str(exc)
            return
        self._termino_antes = juego.reloj < hasta
        self._estado_final = juego.estado.value if juego.esta_terminada() else None

    @property
    def error_hasta(self) -> str | None:
        return self._error_hasta

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

    def describir_hasta(self) -> str:
        """Mismo resumen que ``historia T``, sin la cabecera del replay."""
        if self._error_hasta is not None:
            return self._error_hasta
        if self._resumen_historico is None:
            return "El replay no produjo ninguna partida."
        lineas = [formatear_resumen(self._resumen_historico)]
        if self._termino_antes:
            if self._estado_final:
                lineas.append(f"La partida terminó antes ({self._estado_final}).")
            else:
                lineas.append("El log termina antes del instante pedido; se muestra el estado final.")
        lineas.append(self._controlador.reporte_red())
        return "\n".join(lineas)
