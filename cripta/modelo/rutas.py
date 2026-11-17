"""Rutas de costo mínimo: cazador (spec 001/002) e «ir a» (spec 003). [Persona A]

``BuscadorRutas`` calcula el costo mínimo de cada sala HACIA un objetivo
(Dijkstra en sentido inverso: se recorren las ``entradas`` de cada sala). Con
eso, la decisión de cualquier actor que quiera llegar al objetivo cuesta
O(grado): mirar las vecinas y aplicar el desempate de §3.2.

Estructuras (todas propias, §6.2 de la Parte II):
- ``MonticuloMin`` de la Parte I para escoger la siguiente sala. Borrado
  perezoso: una sala puede entrar varias veces; al salir se descarta si ya
  estaba finalizada. La clave es UN entero ``dist * V + indice`` (comparar
  enteros es más barato que comparar tuplas y el orden queda total).
- Arreglos de tamaño V indexados por ``Sala.indice`` para la distancia, la
  marca de validez y la marca de finalizada. Cada búsqueda incrementa la
  ``generacion``: un valor solo vale si su marca es la generación actual. Así
  una búsqueda que toca 5 salas no paga O(V) por limpiar arreglos (§5.1:
  "un rango pequeño no debe costar proporcionalmente al tamaño de la cripta").

Desempate (§3.2, research R4 de la spec 001): la búsqueda SOLO calcula
distancias exactas; el paso se elige después, recorriendo las salidas en
orden N, S, E, O y quedándose con la vecina de menor id que cumple
``costo(u, v) + dist(v) = d``. Así el resultado no depende del orden en que el
montículo saca salas empatadas. Las vecinas que cumplen la igualdad tienen
``dist(v) < d`` (costos >= 1), así que ya están finalizadas cuando se
finaliza ``u``: basta mirar distancias finalizadas.

``RutasCazadores`` decide por cada cazador con una de cuatro estrategias
(spec 002). La de juego es ``COMPARTIDA``: un solo cálculo desde la sala del
jugador, reutilizado por todos los cazadores y por los turnos siguientes
mientras siga siendo válido. La caché NO es estado del juego: no se guarda,
no se revierte, y se invalida sola (ver ``puerta_cambio`` y la comparación de
la sala del jugador en ``decidir``).
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Callable

from cripta.estructuras.monticulo import MonticuloMin

if TYPE_CHECKING:
    from cripta.modelo.actores import Enemigo
    from cripta.modelo.mapa import Mapa, Puerta, Sala, Salida

# Alcance "sin límite" (mayor que cualquier suma de costos realista).
SIN_LIMITE = 1 << 60


def salida_abierta(salida: Salida) -> bool:
    """Filtro del cazador: salidas abiertas en este instante (sin puerta o puerta abierta)."""
    puerta = salida.puerta
    return puerta is None or not puerta.cerrada


class BuscadorRutas:
    """Dijkstra inverso acotado, con arreglos reutilizables entre búsquedas."""

    __slots__ = (
        "_n", "_salas", "_dist", "_marca", "_final", "_generacion", "_monticulo",
        "objetivo", "alcance", "salas_examinadas", "busquedas",
    )

    def __init__(self, mapa: Mapa) -> None:
        n = len(mapa)
        self._n = max(1, n)
        # Índice → sala (Sala.indice es la posición en el esqueleto).
        self._salas: list[Sala] = [sala for sala in mapa]
        self._dist: list[int] = [0] * self._n
        self._marca: list[int] = [0] * self._n
        self._final: list[int] = [0] * self._n
        self._generacion = 0
        self._monticulo: MonticuloMin[int] = MonticuloMin()
        self.objetivo: Sala | None = None
        self.alcance = 0
        # Contadores para --bench (no afectan el juego).
        self.salas_examinadas = 0
        self.busquedas = 0

    def calcular(
        self,
        objetivo: Sala,
        alcance: int,
        transitable: Callable[[Salida], bool],
        parar_en: Sala | None = None,
    ) -> None:
        """Distancias exactas hacia ``objetivo`` para las salas con costo <= ``alcance``.

        Solo cruza salidas que cumplen ``transitable``. Si se pasa ``parar_en``,
        se detiene en cuanto esa sala queda finalizada (todas las vecinas que
        podrían empezar una ruta mínima desde ella ya lo están).
        """
        self._generacion += 1
        generacion = self._generacion
        n = self._n
        dist = self._dist
        marca = self._marca
        final = self._final
        monticulo = self._monticulo
        monticulo.reconstruir([])  # vacía lo que haya quedado de la búsqueda anterior
        self.objetivo = objetivo
        self.alcance = alcance
        self.busquedas += 1
        examinadas = 0
        inicio = objetivo.indice
        dist[inicio] = 0
        marca[inicio] = generacion
        monticulo.insertar(inicio)  # clave 0 * n + indice
        salas = self._salas
        while not monticulo.esta_vacio():
            clave = monticulo.extraer_min()
            d, indice = divmod(clave, n)
            if final[indice] == generacion or d != dist[indice]:
                continue  # entrada vieja (borrado perezoso)
            if d > alcance:
                break  # todo lo que queda está fuera del alcance
            final[indice] = generacion
            examinadas += 1
            sala = salas[indice]
            if parar_en is not None and sala is parar_en:
                break
            for entrada in sala.entradas:
                if not transitable(entrada):
                    continue
                origen = entrada.origen
                j = origen.indice
                if final[j] == generacion:
                    continue
                nueva = d + entrada.costo
                if nueva > alcance:
                    continue
                if marca[j] != generacion or nueva < dist[j]:
                    dist[j] = nueva
                    marca[j] = generacion
                    monticulo.insertar(nueva * n + j)
        self.salas_examinadas += examinadas

    def distancia(self, sala: Sala) -> int | None:
        """Costo mínimo de ``sala`` al objetivo, si quedó finalizada en la última búsqueda."""
        if self._final[sala.indice] == self._generacion and self._generacion > 0:
            return self._dist[sala.indice]
        return None

    def en_region(self, sala: Sala) -> bool:
        """True si ``sala`` quedó finalizada (dentro del alcance) en la última búsqueda."""
        return self._generacion > 0 and self._final[sala.indice] == self._generacion

    def primer_paso(self, origen: Sala, transitable: Callable[[Salida], bool]) -> Salida | None:
        """Salida por la que ``origen`` empieza una ruta mínima (desempate §3.2), o None.

        Entre las vecinas ``v`` con ``costo(u, v) + dist(v) = d`` gana la de menor
        id; para la misma vecina, la primera salida en N, S, E, O.
        """
        d = self.distancia(origen)
        if d is None or d == 0:
            return None
        mejor: Salida | None = None
        for salida in origen.salidas:  # orden N, S, E, O
            if salida is None or not transitable(salida):
                continue
            dv = self.distancia(salida.destino)
            if dv is None or salida.costo + dv != d:
                continue
            if mejor is None or salida.destino.id < mejor.destino.id:
                mejor = salida
        return mejor

    def ultima_generacion(self) -> int:
        return self._generacion


class EstrategiaCazador(Enum):
    """Cómo se calculan las rutas de los cazadores (spec 002). Todas deciden igual."""

    COMPARTIDA = "compartida"  # un cálculo desde el jugador, reutilizado con invalidación fina
    COMPARTIDA_GRUESA = "gruesa"  # igual, pero cualquier cambio de puerta invalida
    RECALCULAR_SIEMPRE = "recalcular"  # un cálculo desde el jugador en cada turno de cazador
    INDIVIDUAL = "individual"  # un cálculo por turno, acotado por el rango del cazador

    @staticmethod
    def desde_texto(texto: str) -> EstrategiaCazador:
        for estrategia in EstrategiaCazador:
            if estrategia.value == texto:
                return estrategia
        raise ValueError(f"Estrategia de cazador desconocida: {texto!r}")


class RutasCazadores:
    """Decisión de movimiento de los cazadores, con caché e invalidación (spec 002)."""

    def __init__(self, mapa: Mapa, estrategia: EstrategiaCazador = EstrategiaCazador.COMPARTIDA) -> None:
        self.estrategia = estrategia
        self._buscador = BuscadorRutas(mapa)
        self._valida = False
        self._objetivo: Sala | None = None
        self._alcance = 0
        self._mayor_rango = 0
        # Contadores para --bench y pruebas (no son estado del juego).
        self.calculos = 0
        self.reutilizados = 0
        self.invalidaciones = 0

    @property
    def buscador(self) -> BuscadorRutas:
        return self._buscador

    def decidir(self, cazador: Enemigo, sala_jugador: Sala) -> Salida | None:
        """Salida por la que se mueve ``cazador``, o None si debe esperar (FR-010..FR-013)."""
        u = cazador.sala
        rango = cazador.rango
        buscador = self._buscador
        estrategia = self.estrategia
        if estrategia is EstrategiaCazador.INDIVIDUAL:
            buscador.calcular(sala_jugador, rango, salida_abierta, parar_en=u)
            self.calculos += 1
        elif estrategia is EstrategiaCazador.RECALCULAR_SIEMPRE:
            if rango > self._mayor_rango:
                self._mayor_rango = rango
            buscador.calcular(sala_jugador, self._mayor_rango, salida_abierta)
            self.calculos += 1
        else:
            if rango > self._mayor_rango:
                self._mayor_rango = rango
            if not self._valida or self._objetivo is not sala_jugador or rango > self._alcance:
                buscador.calcular(sala_jugador, self._mayor_rango, salida_abierta)
                self._valida = True
                self._objetivo = sala_jugador
                self._alcance = self._mayor_rango
                self.calculos += 1
            else:
                self.reutilizados += 1
        d = buscador.distancia(u)
        if d is None or d > rango:
            return None  # sin ruta o fuera de rango: espera (FR-011)
        return buscador.primer_paso(u, salida_abierta)

    def puerta_cambio(self, puerta: Puerta) -> None:
        """Oyente de ``Puerta.cerrada`` (spec 002, research R2).

        Invalida solo si la puerta toca la región del cálculo vigente (una de sus
        salas quedó finalizada dentro del alcance). La gruesa invalida siempre.
        """
        if not self._valida:
            return
        if self.estrategia is EstrategiaCazador.COMPARTIDA_GRUESA:
            self._invalidar()
            return
        salas = puerta.salas
        if salas is None:
            self._invalidar()
            return
        buscador = self._buscador
        if buscador.en_region(salas[0]) or buscador.en_region(salas[1]):
            self._invalidar()

    def invalidar(self) -> None:
        """Descarta el cálculo (p. ej. tras cargar una partida en el mismo mapa)."""
        if self._valida:
            self._invalidar()

    def _invalidar(self) -> None:
        self._valida = False
        self.invalidaciones += 1
