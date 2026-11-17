"""Conocimiento del mapa del jugador: niebla de guerra (spec 003).    [Persona A]

§3.3 de la Parte II. Para el jugador cada sala está EXPLORADA (entró, o la
iluminó la antorcha), AVISTADA (no explorada pero destino de una salida de una
explorada) o DESCONOCIDA. Cada puerta se recuerda como la vio la última vez
(abierta o cerrada) o queda SIN OBSERVAR.

Estructura (research R1-R3 de la spec 003): dos arreglos de enteros pequeños
indexados por posición, ``estado_sala[Sala.indice]`` y
``recuerdo_puerta[Puerta.indice]``. Consultar cuesta O(1) sin importar cuánto
se conoce (§5.3). Explorar una sala cuesta O(grado): su casilla pasa a 2 y sus
destinos que estaban en 0 pasan a 1. "Avistada" se guarda en vez de calcularse
en cada consulta: una sala avistada nunca vuelve a desconocida salvo por
retroceso, y el retroceso restaura el valor exacto anterior.

Retroceso: el conocimiento NO cambia directamente. Cada cambio de casilla pasa
por la función ``asignar(arreglo, indice, valor)`` que entrega el ``Juego``;
esa función registra un ``CambioCasilla`` en el historial (valor anterior), así
el pergamino lo invierte en O(1) por cambio. Revertir la exploración de cinco
salas con antorcha cuesta exactamente las casillas que cambiaron.

Guardado y línea de tiempo: ``serializar`` produce un texto con un dígito por
sala (orden del esqueleto), ``|`` y un dígito por puerta. Va dentro del
``EstadoGuardable``, así que también viaja en los puntos de control.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from cripta.modelo.mapa import Mapa, Puerta, Sala, Salida

DESCONOCIDA = 0
AVISTADA = 1
EXPLORADA = 2

SIN_OBSERVAR = 0
RECUERDA_ABIERTA = 1
RECUERDA_CERRADA = 2

# Texto de cada valor para la vista (índice = valor).
NOMBRE_ESTADO_SALA: tuple[str, ...] = ("desconocida", "avistada", "explorada")
NOMBRE_RECUERDO: tuple[str, ...] = ("sin observar", "abierta", "cerrada")

Asignador = Callable[[list, int, int], None]


@dataclass(slots=True)
class SalidaConocida:
    direccion: str
    costo: int
    puerta: str  # "sin puerta" | "abierta" | "cerrada" | "sin observar"
    destino_id: int | None  # solo si el destino está explorado
    destino_nombre: str | None


@dataclass(slots=True)
class SalaConocida:
    id: int
    nombre: str
    actual: bool
    salidas: list[SalidaConocida] = field(default_factory=list)


@dataclass(slots=True)
class MapaConocido:
    """Vista neutra del conocimiento (para la interfaz y para ``historia``)."""

    exploradas: list[SalaConocida] = field(default_factory=list)
    avistadas: int = 0


class ConocimientoMapa:
    """Lo que el jugador sabe del mapa. Toda modificación pasa por ``asignar``."""

    __slots__ = ("estado_sala", "recuerdo_puerta", "_mapa")

    def __init__(self, mapa: Mapa) -> None:
        self._mapa = mapa
        self.estado_sala: list[int] = [DESCONOCIDA] * len(mapa)
        self.recuerdo_puerta: list[int] = [SIN_OBSERVAR] * len(mapa.lista_puertas)

    # --- consultas O(1) ---------------------------------------------------------

    def estado(self, sala: Sala) -> int:
        return self.estado_sala[sala.indice]

    def explorada(self, sala: Sala) -> bool:
        return self.estado_sala[sala.indice] == EXPLORADA

    def recuerdo(self, puerta: Puerta) -> int:
        return self.recuerdo_puerta[puerta.indice]

    def salida_conocida_abierta(self, salida: Salida) -> bool:
        """Sin puerta: siempre abierta. Con puerta: solo si se recuerda abierta."""
        puerta = salida.puerta
        return puerta is None or self.recuerdo_puerta[puerta.indice] == RECUERDA_ABIERTA

    def transitable_conocida(self, salida: Salida) -> bool:
        """Filtro de «ir a» (FR-019): de explorada a explorada y recordada abierta."""
        estados = self.estado_sala
        if estados[salida.destino.indice] != EXPLORADA or estados[salida.origen.indice] != EXPLORADA:
            return False
        puerta = salida.puerta
        return puerta is None or self.recuerdo_puerta[puerta.indice] == RECUERDA_ABIERTA

    def describir_puerta(self, salida: Salida) -> str:
        if salida.puerta is None:
            return "sin puerta"
        return NOMBRE_RECUERDO[self.recuerdo_puerta[salida.puerta.indice]]

    # --- cambios (registrados con ``asignar``) -------------------------------------

    def explorar(self, sala: Sala, asignar: Asignador) -> bool:
        """Deja ``sala`` explorada y avista sus destinos. True si era nueva. O(grado)."""
        estados = self.estado_sala
        nueva = estados[sala.indice] != EXPLORADA
        if nueva:
            asignar(estados, sala.indice, EXPLORADA)
        for salida in sala.salidas:
            if salida is not None and estados[salida.destino.indice] == DESCONOCIDA:
                asignar(estados, salida.destino.indice, AVISTADA)
        return nueva

    def observar(self, puerta: Puerta, asignar: Asignador) -> None:
        """El jugador ve la puerta: el recuerdo pasa a ser su estado real."""
        valor = RECUERDA_CERRADA if puerta.cerrada else RECUERDA_ABIERTA
        if self.recuerdo_puerta[puerta.indice] != valor:
            asignar(self.recuerdo_puerta, puerta.indice, valor)

    def observar_sala(self, sala: Sala, asignar: Asignador) -> None:
        """Observa todas las puertas de ``sala`` (el jugador está en ella)."""
        for salida in sala.salidas:
            if salida is not None and salida.puerta is not None:
                self.observar(salida.puerta, asignar)

    # --- guardado ---------------------------------------------------------------

    def serializar(self) -> str:
        """``"<dígito por sala>|<dígito por puerta>"`` en orden del esqueleto y de creación."""
        return "".join(str(v) for v in self.estado_sala) + "|" + "".join(str(v) for v in self.recuerdo_puerta)

    def restaurar(self, texto: str) -> None:
        """Inverso de ``serializar``. ValueError si no corresponde a este mapa."""
        if "|" not in texto:
            raise ValueError("conocimiento con formato inválido (falta '|')")
        salas, puertas = texto.split("|", 1)
        if len(salas) != len(self.estado_sala) or len(puertas) != len(self.recuerdo_puerta):
            raise ValueError(
                f"el conocimiento guardado es de otro mapa ({len(salas)} salas / {len(puertas)} puertas; "
                f"se esperaban {len(self.estado_sala)} / {len(self.recuerdo_puerta)})"
            )
        for i in range(len(salas)):
            valor = ord(salas[i]) - 48
            if valor < DESCONOCIDA or valor > EXPLORADA:
                raise ValueError(f"estado de sala inválido en el conocimiento: {salas[i]!r}")
            self.estado_sala[i] = valor
        for i in range(len(puertas)):
            valor = ord(puertas[i]) - 48
            if valor < SIN_OBSERVAR or valor > RECUERDA_CERRADA:
                raise ValueError(f"recuerdo de puerta inválido en el conocimiento: {puertas[i]!r}")
            self.recuerdo_puerta[i] = valor

    def reiniciar(self) -> None:
        for i in range(len(self.estado_sala)):
            self.estado_sala[i] = DESCONOCIDA
        for i in range(len(self.recuerdo_puerta)):
            self.recuerdo_puerta[i] = SIN_OBSERVAR

    # --- vista ------------------------------------------------------------------

    def contar(self, estado: int) -> int:
        """Cuántas salas tienen ese estado. O(V); solo para mostrar."""
        total = 0
        for valor in self.estado_sala:
            if valor == estado:
                total += 1
        return total

    def mapa_conocido(self, sala_actual: Sala | None) -> MapaConocido:
        """Salas exploradas con sus salidas y cantidad de avistadas (FR-013)."""
        resultado = MapaConocido()
        estados = self.estado_sala
        for sala in self._mapa:
            valor = estados[sala.indice]
            if valor == AVISTADA:
                resultado.avistadas += 1
                continue
            if valor != EXPLORADA:
                continue
            conocida = SalaConocida(sala.id, sala.nombre, sala is sala_actual)
            for salida in sala.salidas:
                if salida is None:
                    continue
                destino = salida.destino
                explorado = estados[destino.indice] == EXPLORADA
                conocida.salidas.append(
                    SalidaConocida(
                        salida.direccion,
                        salida.costo,
                        self.describir_puerta(salida),
                        destino.id if explorado else None,
                        destino.nombre if explorado else None,
                    )
                )
            resultado.exploradas.append(conocida)
        return resultado
