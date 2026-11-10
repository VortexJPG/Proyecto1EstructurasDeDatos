"""Línea de tiempo de la partida e historia (§3.6, §5.5).        [Persona B]

La línea vigente guarda las acciones del jugador, el contenido nuevo que se
cargó y puntos de control completos cada K acciones. Reconstruir un instante
consiste en tomar el punto de control más cercano y re-simular como máximo K
acciones; no se guarda una copia por acción ni se consulta la red.

El pergamino recorta la línea: las acciones revertidas dejan de existir y los
puntos de control posteriores se descartan.

No usa ``dict``, ``set``, ``heapq``, ``bisect``, ``collections`` ni
``networkx``. La búsqueda del punto de control es binaria y propia.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from cripta.estructuras.tabla_ordenada import ConjuntoOrdenado
from cripta.modelo.acciones import Accion, TipoAccion
from cripta.modelo.datos import ContenidoSala, DatosCripta, DatosSala
from cripta.modelo.guardable import (
    EstadoGuardable,
    LineaGuardable,
    RegistroAccion,
    RegistroCheckpoint,
    RegistroContenido,
)
from cripta.modelo.juego import Juego
from cripta.modelo.mapa import Mapa
from cripta.modelo.puertos import ProveedorFichas

if TYPE_CHECKING:
    from cripta.modelo.efectos import Efecto

K_POR_DEFECTO = 50  # provisional: se ajusta con --bench timeline


class ErrorReconstruccion(Exception):
    """La línea no pudo reconstruir el estado pedido."""


class ProveedorSoloLectura(ProveedorFichas):
    """Delega ``obtener`` y neutraliza ``fijar``/``liberar``.

    La reconstrucción comparte la caché del juego vivo; no debe cambiar sus
    pines.
    """

    def __init__(self, proveedor: ProveedorFichas) -> None:
        self._proveedor = proveedor

    def obtener(self, tipo_id: str):
        return self._proveedor.obtener(tipo_id)

    def fijar(self, tipo_id: str) -> None:
        return None

    def liberar(self, tipo_id: str) -> None:
        return None


@dataclass(slots=True)
class AccionRegistrada:
    indice: int  # 1-based
    tiempo: int  # reloj al que empieza la acción
    accion: Accion


@dataclass(slots=True)
class ContenidoNuevo:
    indice_accion: int  # acciones completadas cuando se cargó
    contenido: ContenidoSala


@dataclass(slots=True)
class PuntoControl:
    indice_accion: int  # 0 = estado inicial
    tiempo: int
    estado: EstadoGuardable


@dataclass(slots=True)
class ObjetoResumen:
    id: str
    nombre: str


@dataclass(slots=True)
class EfectoResumen:
    tipo: str
    magnitud: int
    fin: int | None


@dataclass(slots=True)
class EnemigoResumen:
    id: str
    nombre: str
    vida: int
    vida_max: int
    activo: bool


@dataclass(slots=True)
class ResumenHistorico:
    etiqueta: str
    reloj: int
    sala: int
    nombre_sala: str
    vida: int
    vida_max: int
    ataque: int
    defensa: int
    velocidad: int
    inventario: list[ObjetoResumen] = field(default_factory=list)
    efectos: list[EfectoResumen] = field(default_factory=list)
    enemigos: list[EnemigoResumen] = field(default_factory=list)
    mapa_conocido: list[int] = field(default_factory=list)
    terminada: str | None = None


class LineaTiempo:
    """Línea vigente de una partida y reconstrucción de estados pasados."""

    def __init__(
        self,
        datos: DatosCripta,
        esqueleto: list[DatosSala],
        fichas: ProveedorFichas,
        semilla: int,
        version_catalogo: str,
        k: int = K_POR_DEFECTO,
    ) -> None:
        if k < 1:
            raise ValueError("checkpoint_cada debe ser >= 1")
        self.datos = datos
        self.esqueleto = esqueleto
        self._fichas = ProveedorSoloLectura(fichas)
        self.semilla = semilla
        self.version_catalogo = version_catalogo
        self.k = k
        self.acciones: list[AccionRegistrada] = []
        self.contenidos: list[ContenidoNuevo] = []
        self.checkpoints: list[PuntoControl] = []
        self.conocimiento: str = ""
        self._vistas_contenido: ConjuntoOrdenado[int] = ConjuntoOrdenado()
        self._mapa_recon: Mapa | None = None

    # --- registro -------------------------------------------------------------

    def registrar_inicio(self, juego: Juego) -> None:
        """Punto de control 0: el estado justo después de iniciar la partida."""
        self.checkpoints = [
            PuntoControl(0, juego.reloj, juego.exportar_estado(self.version_catalogo))
        ]

    def registrar_accion(self, juego: Juego, accion: Accion, tiempo_inicio: int) -> None:
        indice = len(self.acciones) + 1
        self.acciones.append(AccionRegistrada(indice, tiempo_inicio, accion))
        if juego.jugador.acciones_ejecutadas % self.k == 0:
            self.checkpoints.append(
                PuntoControl(
                    juego.jugador.acciones_ejecutadas,
                    juego.reloj,
                    juego.exportar_estado(self.version_catalogo),
                )
            )

    def registrar_contenidos(self, contenidos: list[ContenidoSala], indice_accion: int) -> None:
        for contenido in contenidos:
            if self._vistas_contenido.agregar(contenido.sala):
                self.contenidos.append(ContenidoNuevo(indice_accion, contenido))

    def recortar(self, acciones_vigentes: int) -> None:
        """Recorte por pergamino: acciones revertidas y checkpoints posteriores."""
        if acciones_vigentes < 0:
            acciones_vigentes = 0
        if acciones_vigentes > len(self.acciones):
            acciones_vigentes = len(self.acciones)
        del self.acciones[acciones_vigentes:]
        # El contenido cargado no se descarga al retroceder: se reubica en el
        # punto de recorte para que la reconstrucción del estado actual lo vea.
        for contenido in self.contenidos:
            if contenido.indice_accion > acciones_vigentes:
                contenido.indice_accion = acciones_vigentes
        self.checkpoints = [
            punto for punto in self.checkpoints if punto.indice_accion <= acciones_vigentes
        ]

    # --- reconstrucción -------------------------------------------------------

    def estado_en_accion(self, acciones: int) -> Juego:
        """Estado justo antes de la acción ``acciones + 1`` (0 = inicial).

        Aplica como máximo K acciones desde el punto de control anterior.
        """
        if acciones < 0 or acciones > len(self.acciones):
            raise ValueError(f"Acción fuera de rango: {acciones} (hay {len(self.acciones)})")
        punto = self._checkpoint_cercano(acciones)
        juego = self._reconstruir(punto.estado)
        self._aplicar_contenidos(juego, punto.indice_accion)
        for i in range(punto.indice_accion, acciones):
            self._aplicar_contenidos(juego, i)
            resultado = juego.ejecutar_accion(self.acciones[i].accion)
            if not resultado.aceptada:
                raise ErrorReconstruccion(
                    f"la acción {i + 1} no se pudo re-simular: {resultado.motivo}"
                )
        self._aplicar_contenidos(juego, acciones)
        return juego

    def estado_en_tiempo(self, tiempo: int, reloj_actual: int) -> Juego:
        """Estado en ``tiempo``.

        Para instantes entre dos decisiones hace falta ``Juego.avanzar_hasta``
        (interfaz con A). Si la re-simulación ya se pasó del instante, se
        informa en vez de devolver un estado incorrecto.
        """
        if tiempo < 0 or tiempo > reloj_actual:
            raise ValueError(f"Instante fuera de rango: {tiempo} (reloj actual {reloj_actual})")
        acciones = self._acciones_hasta(tiempo)
        juego = self.estado_en_accion(acciones)
        if juego.reloj > tiempo:
            raise ErrorReconstruccion(
                "el instante cae entre decisiones; hace falta Juego.avanzar_hasta (interfaz A)"
            )
        if juego.reloj < tiempo:
            self._avanzar_hasta(juego, tiempo)
        return juego

    def _checkpoint_cercano(self, acciones: int) -> PuntoControl:
        if not self.checkpoints:
            raise ErrorReconstruccion("la línea no tiene puntos de control")
        bajo = 0
        alto = len(self.checkpoints) - 1
        mejor = 0
        while bajo <= alto:
            medio = (bajo + alto) // 2
            if self.checkpoints[medio].indice_accion <= acciones:
                mejor = medio
                bajo = medio + 1
            else:
                alto = medio - 1
        return self.checkpoints[mejor]

    def _acciones_hasta(self, tiempo: int) -> int:
        """Número de acciones cuyo reloj de inicio es **anterior** a ``tiempo``.

        Una acción que empieza exactamente en ``tiempo`` todavía no se ha
        tomado: el estado que se muestra es el de justo antes de esa decisión.
        """
        bajo = 0
        alto = len(self.acciones) - 1
        mejor = 0
        while bajo <= alto:
            medio = (bajo + alto) // 2
            if self.acciones[medio].tiempo < tiempo:
                mejor = medio + 1
                bajo = medio + 1
            else:
                alto = medio - 1
        return mejor

    def _reconstruir(self, estado: EstadoGuardable) -> Juego:
        if self._mapa_recon is None:
            self._mapa_recon = Mapa.construir(self.datos, self.esqueleto)
        return Juego.desde_estado(estado, self.datos, self._mapa_recon, self._fichas)

    def _aplicar_contenidos(self, juego: Juego, hasta: int) -> None:
        for registro in self.contenidos:
            if registro.indice_accion <= hasta:
                juego.mapa.incorporar_contenido(registro.contenido, self._fichas)

    @staticmethod
    def _avanzar_hasta(juego: Juego, tiempo: int) -> None:
        """Avanza eventos hasta ``tiempo`` (soporte temporal mientras llega A)."""
        from cripta.modelo.eventos import TipoEvento

        while not juego.esta_terminada():
            evento = juego.agenda.ver_siguiente()
            if evento is None or evento.tiempo > tiempo:
                return
            if evento.tipo is TipoEvento.TURNO_JUGADOR:
                juego._asignar(juego, "reloj", evento.tiempo)
                return
            juego.agenda.extraer_siguiente()
            juego._asignar(juego, "reloj", evento.tiempo)
            juego._despachar(evento)

    # --- resumen --------------------------------------------------------------

    def resumen(self, juego: Juego, etiqueta: str) -> ResumenHistorico:
        jugador = juego.jugador
        return ResumenHistorico(
            etiqueta=etiqueta,
            reloj=juego.reloj,
            sala=jugador.sala.id,
            nombre_sala=jugador.sala.nombre,
            vida=jugador.vida,
            vida_max=jugador.vida_max,
            ataque=jugador.ataque,
            defensa=jugador.defensa,
            velocidad=jugador.velocidad,
            inventario=[
                ObjetoResumen(objeto.id, juego.nombre_de_tipo(objeto.tipo_id))
                for objeto in jugador.inventario
            ],
            efectos=self._efectos(jugador),
            enemigos=[
                EnemigoResumen(
                    enemigo.id,
                    enemigo.etiqueta(),
                    enemigo.vida,
                    enemigo.vida_max,
                    enemigo.activo,
                )
                for enemigo in jugador.sala.enemigos
            ],
            mapa_conocido=[sala.id for sala in juego.mapa if sala.visitada],
            terminada=None if not juego.esta_terminada() else juego.estado.value,
        )

    @staticmethod
    def _efectos(jugador) -> list[EfectoResumen]:
        resultado: list[EfectoResumen] = []
        for ranura in ("veneno", "efecto_velocidad", "regeneracion", "antorcha"):
            efecto: Efecto | None = getattr(jugador, ranura)
            if efecto is not None:
                resultado.append(
                    EfectoResumen(str(efecto.tipo.value), efecto.magnitud, efecto.fin)
                )
        return resultado

    # --- persistencia ---------------------------------------------------------

    def exportar(self) -> LineaGuardable:
        return LineaGuardable(
            k=self.k,
            acciones=[
                RegistroAccion(
                    indice=registro.indice,
                    tiempo=registro.tiempo,
                    tipo=registro.accion.tipo.value,
                    direccion=registro.accion.direccion or "",
                    objetivo=registro.accion.objetivo or "",
                )
                for registro in self.acciones
            ],
            contenidos=[
                RegistroContenido(registro.indice_accion, registro.contenido)
                for registro in self.contenidos
            ],
            checkpoints=[
                RegistroCheckpoint(punto.indice_accion, punto.tiempo, punto.estado)
                for punto in self.checkpoints
            ],
            conocimiento=self.conocimiento,
        )

    @staticmethod
    def desde_guardable(
        linea: LineaGuardable,
        datos: DatosCripta,
        esqueleto: list[DatosSala],
        fichas: ProveedorFichas,
        semilla: int,
        version_catalogo: str,
    ) -> LineaTiempo:
        resultado = LineaTiempo(
            datos, esqueleto, fichas, semilla, version_catalogo, linea.k
        )
        for registro in linea.acciones:
            try:
                tipo = TipoAccion(registro.tipo)
            except ValueError as exc:
                raise ErrorReconstruccion(
                    f"tipo de acción desconocido en la partida guardada: {registro.tipo!r}"
                ) from exc
            accion = Accion(
                tipo,
                direccion=registro.direccion or None,
                objetivo=registro.objetivo or None,
            )
            resultado.acciones.append(AccionRegistrada(registro.indice, registro.tiempo, accion))
        for registro in linea.contenidos:
            resultado.contenidos.append(
                ContenidoNuevo(registro.indice_accion, registro.contenido)
            )
            resultado._vistas_contenido.agregar(registro.contenido.sala)
        for registro in linea.checkpoints:
            resultado.checkpoints.append(
                PuntoControl(registro.indice_accion, registro.tiempo, registro.estado)
            )
        resultado.conocimiento = linea.conocimiento
        return resultado


def formatear_resumen(resumen: ResumenHistorico) -> str:
    """Texto legible del resumen histórico (sin depender de la vista)."""
    lineas = [
        f"Historia {resumen.etiqueta} (t={resumen.reloj})",
        f"Sala: {resumen.sala} — {resumen.nombre_sala}",
        f"Vida: {resumen.vida}/{resumen.vida_max}   Ataque: {resumen.ataque}   "
        f"Defensa: {resumen.defensa}   Velocidad: {resumen.velocidad}",
    ]
    if resumen.inventario:
        lineas.append("Inventario: " + ", ".join(o.nombre for o in resumen.inventario))
    else:
        lineas.append("Inventario: (vacío)")
    if resumen.efectos:
        lineas.append(
            "Efectos: "
            + ", ".join(
                f"{e.tipo} (magnitud {e.magnitud}, fin {e.fin})" for e in resumen.efectos
            )
        )
    if resumen.enemigos:
        lineas.append("Enemigos en la sala:")
        for enemigo in resumen.enemigos:
            estado = "activo" if enemigo.activo else "dormido"
            lineas.append(
                f"  - {enemigo.nombre}: {enemigo.vida}/{enemigo.vida_max} ({estado})"
            )
    else:
        lineas.append("Enemigos en la sala: ninguno")
    if resumen.mapa_conocido:
        lineas.append("Mapa conocido: salas " + ", ".join(str(s) for s in resumen.mapa_conocido))
    else:
        lineas.append("Mapa conocido: (ninguna sala)")
    if resumen.terminada:
        lineas.append(f"Partida terminada: {resumen.terminada}")
    return "\n".join(lineas)
