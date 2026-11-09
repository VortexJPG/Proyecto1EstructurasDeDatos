"""Verificación de resolubilidad de una cripta (Parte II §3.5, §5.4).  [Persona B]

Un único recorrido incremental decide si la cripta puede ganarse y, de paso,
produce el orden de llaves, la frontera bloqueada, las llaves inobtenibles y el
ciclo concreto. Las puertas cerradas se retienen asociadas a su llave; cuando
la llave se obtiene, se liberan solo esas puertas y la expansión continúa sin
reiniciar el recorrido.

Estructuras (constitución I): ``ColaEnlazada`` para la expansión y arreglos
indexados por id para salas, puertas y llaves (se preparan una vez). No se usa
``dict``, ``set``, ``heapq``, ``bisect``, ``collections`` ni ``networkx``.

Coste esperado: O(salas + salidas + puertas liberadas + K log K).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from cripta.constantes import indice_direccion
from cripta.estructuras.cola import ColaEnlazada
from cripta.estructuras.ordenamiento import ordenar
from cripta.estructuras.tabla_ordenada import ConjuntoOrdenado, TablaOrdenada
from cripta.modelo.datos import UbicacionLlave

if TYPE_CHECKING:
    from cripta.modelo.datos import DatosCripta
    from cripta.modelo.mapa import Mapa, Sala

# Dirección opuesta, indexada con indice_direccion (N↔S, E↔O).
_OPUESTA: tuple[str, ...] = ("S", "N", "O", "E")


@dataclass(slots=True)
class PuertaFrontera:
    puerta_id: str
    desde_sala: int
    hacia_sala: int
    direccion: str
    llave_requerida: str


@dataclass(slots=True)
class LlaveInobtenible:
    id: str
    ubicaciones: list[UbicacionLlave] = field(default_factory=list)
    puertas: list[PuertaFrontera] = field(default_factory=list)


@dataclass(slots=True)
class PasoCiclo:
    llave: str
    puerta_id: str
    llave_requerida: str


@dataclass(slots=True)
class ResultadoVerificacion:
    resoluble: bool
    motivo: str = ""
    orden_llaves: list[str] = field(default_factory=list)
    llaves_inobtenibles: list[LlaveInobtenible] = field(default_factory=list)
    frontera: list[PuertaFrontera] = field(default_factory=list)
    ciclo: list[PasoCiclo] = field(default_factory=list)
    llave_salida_obtenida: bool = False
    salida_por_puerta_con_llave: bool = False


@dataclass(slots=True)
class _Arista:
    destino: int
    direccion: str
    puerta_id: str | None
    cerrada: bool
    llave_id: str | None
    llave: int | None


@dataclass(slots=True)
class _PuertaRetenida:
    puerta_id: str
    llave_id: str
    llave: int | None
    sala_a: int
    sala_b: int
    direccion_a: str


class Verificador:
    """Verificador incremental de una cripta ya construida.

    Recibe el ``Mapa`` recién construido con el esqueleto (estado inicial) y la
    respuesta de llaves. No modifica el mapa ni consulta el servicio.
    """

    def __init__(self, datos: DatosCripta, mapa: Mapa, llaves: list[UbicacionLlave]) -> None:
        self.datos = datos
        self.mapa = mapa
        # Salas indexadas 0..N-1 en orden de id. Si los ids son densos (1..N,
        # el caso del servicio) el índice es un arreglo; si no, una tabla.
        pares = list(mapa.salas.pares())
        self._sala_por_indice: list[Sala] = [sala for _, sala in pares]
        ids_salas = [sala_id for sala_id, _ in pares]
        maximo = max(ids_salas) if ids_salas else 0
        self._tabla_sala: TablaOrdenada[int, int] | None = None
        if ids_salas and maximo <= 4 * len(ids_salas) + 1000:
            self._indice_sala: list[int] = [-1] * (maximo + 1)
            for indice, sala_id in enumerate(ids_salas):
                self._indice_sala[sala_id] = indice
        else:
            self._indice_sala = []
            self._tabla_sala = TablaOrdenada()
            for indice, sala_id in enumerate(ids_salas):
                self._tabla_sala.insertar(sala_id, indice)
        # Llaves indexadas 0..K-1 por id ordenado.
        ids = ConjuntoOrdenado[str]()
        for ubicacion in llaves:
            ids.agregar(ubicacion.id)
        self._llave_ids: list[str] = list(ids)
        self._indice_llave: TablaOrdenada[str, int] = TablaOrdenada()
        for indice in range(len(self._llave_ids)):
            self._indice_llave.insertar(self._llave_ids[indice], indice)
        self._por_llave: list[list[UbicacionLlave]] = [[] for _ in self._llave_ids]
        for ubicacion in llaves:
            indice = self._indice_llave.obtener(ubicacion.id)
            if indice is not None:
                self._por_llave[indice].append(ubicacion)
        for indice in range(len(self._por_llave)):
            self._por_llave[indice] = ordenar(
                self._por_llave[indice], clave=lambda u: (u.sala, u.enemigo or "")
            )
        # Llaves por sala (ya ordenadas por id de llave).
        self._por_sala: list[list[int]] = [[] for _ in self._sala_por_indice]
        for indice_llave in range(len(self._llave_ids)):
            for ubicacion in self._por_llave[indice_llave]:
                indice_sala = self._indice_de_sala(ubicacion.sala)
                if indice_sala is not None and indice_llave not in self._por_sala[indice_sala]:
                    self._por_sala[indice_sala].append(indice_llave)
        # Adyacencia preparada: destino, puerta y llave ya resueltos.
        self._adyacencia: list[list[_Arista]] = []
        for sala in self._sala_por_indice:
            aristas: list[_Arista] = []
            for salida in sala.salidas:
                if salida is None:
                    continue
                destino = self._indice_de_sala(salida.destino.id)
                if destino is None:
                    continue
                puerta = salida.puerta
                llave_id = None if puerta is None else puerta.llave
                aristas.append(
                    _Arista(
                        destino=destino,
                        direccion=salida.direccion,
                        puerta_id=None if puerta is None else puerta.id,
                        cerrada=False if puerta is None else puerta.cerrada,
                        llave_id=llave_id,
                        llave=None
                        if llave_id is None
                        else self._indice_llave.obtener(llave_id),
                    )
                )
            self._adyacencia.append(aristas)
        self._sala_inicial = self._indice_de_sala(datos.sala_inicial)
        self._sala_salida = self._indice_de_sala(datos.sala_salida)
        self._llave_salida = self._indice_llave.obtener(datos.llave_salida)
        # Estado del recorrido.
        total_salas = len(self._sala_por_indice)
        total_llaves = len(self._llave_ids)
        self._visitadas: list[bool] = [False] * total_salas
        self._obtenidas: list[bool] = [False] * total_llaves
        self._orden: list[int] = []
        self._cola: ColaEnlazada[int] = ColaEnlazada()
        self._retenidas: list[list[_PuertaRetenida]] = [[] for _ in range(total_llaves)]
        self._retenidas_faltantes: list[_PuertaRetenida] = []
        self._retenidas_ids: ConjuntoOrdenado[str] = ConjuntoOrdenado()

    # --- API ------------------------------------------------------------------

    def verificar(self) -> ResultadoVerificacion:
        if self._sala_inicial is None:
            raise ValueError(
                f"La sala inicial {self.datos.sala_inicial} no está en el esqueleto"
            )
        self._encolar(self._sala_inicial)
        while not self._cola.esta_vacia():
            self._expandir(self._cola.desencolar())
        return self._construir_resultado()

    def _indice_de_sala(self, sala_id: int) -> int | None:
        if self._tabla_sala is not None:
            return self._tabla_sala.obtener(sala_id)
        if 0 <= sala_id < len(self._indice_sala):
            indice = self._indice_sala[sala_id]
            return None if indice < 0 else indice
        return None

    # --- recorrido ------------------------------------------------------------

    def _encolar(self, indice: int) -> None:
        if not self._visitadas[indice]:
            self._visitadas[indice] = True
            self._cola.encolar(indice)

    def _expandir(self, indice: int) -> None:
        self._obtener_llaves_de(indice)
        for arista in self._adyacencia[indice]:
            self._explorar(indice, arista)

    def _obtener_llaves_de(self, indice_sala: int) -> None:
        for indice_llave in self._por_sala[indice_sala]:
            if not self._obtenidas[indice_llave]:
                self._obtenidas[indice_llave] = True
                self._orden.append(indice_llave)
                self._liberar(indice_llave)

    def _explorar(self, desde: int, arista: _Arista) -> None:
        if arista.puerta_id is None or not arista.cerrada:
            self._encolar(arista.destino)
            return
        if arista.llave_id is None or (
            arista.llave is not None and self._obtenidas[arista.llave]
        ):
            self._encolar(arista.destino)
            return
        self._retener(desde, arista)

    def _retener(self, desde: int, arista: _Arista) -> None:
        assert arista.puerta_id is not None and arista.llave_id is not None
        if not self._retenidas_ids.agregar(arista.puerta_id):
            return
        retenida = _PuertaRetenida(
            puerta_id=arista.puerta_id,
            llave_id=arista.llave_id,
            llave=arista.llave,
            sala_a=desde,
            sala_b=arista.destino,
            direccion_a=arista.direccion,
        )
        if arista.llave is None:
            self._retenidas_faltantes.append(retenida)
        else:
            self._retenidas[arista.llave].append(retenida)

    def _liberar(self, indice_llave: int) -> None:
        for retenida in self._retenidas[indice_llave]:
            self._encolar(retenida.sala_a)
            self._encolar(retenida.sala_b)
        self._retenidas[indice_llave] = []

    # --- resultado ------------------------------------------------------------

    def _construir_resultado(self) -> ResultadoVerificacion:
        obtenida = self._llave_salida is not None and self._obtenidas[self._llave_salida]
        por_puerta = self._salida_por_puerta_con_llave()
        resoluble = obtenida and por_puerta
        resultado = ResultadoVerificacion(
            resoluble=resoluble,
            llave_salida_obtenida=obtenida,
            salida_por_puerta_con_llave=por_puerta,
        )
        if resoluble:
            resultado.orden_llaves = [self._llave_ids[k] for k in self._orden]
            return resultado
        resultado.motivo = self._motivo(obtenida, por_puerta)
        frontera = self._frontera()
        componentes = self._componentes()
        bloqueos = self._bloqueos(frontera, componentes)
        resultado.frontera = frontera
        resultado.llaves_inobtenibles = self._inobtenibles(bloqueos, frontera)
        resultado.ciclo = self._ciclo(bloqueos)
        return resultado

    def _salida_por_puerta_con_llave(self) -> bool:
        if self._llave_salida is None or self._sala_salida is None:
            return False
        for indice in range(len(self._sala_por_indice)):
            if not self._visitadas[indice]:
                continue
            for arista in self._adyacencia[indice]:
                if arista.destino == self._sala_salida and arista.llave == self._llave_salida:
                    return True
        return False

    def _motivo(self, obtenida: bool, por_puerta: bool) -> str:
        if self._llave_salida is None:
            return "la llave de salida no aparece en la consulta de llaves"
        if not obtenida:
            return "la llave de salida no es obtenible"
        if not por_puerta:
            return "no hay una salida a la sala final que requiera la llave de salida"
        return "la cripta no es resoluble"

    def _frontera(self) -> list[PuertaFrontera]:
        resultado: list[PuertaFrontera] = []
        for lista in self._retenidas:
            for retenida in lista:
                self._agregar_frontera(resultado, retenida)
        for retenida in self._retenidas_faltantes:
            self._agregar_frontera(resultado, retenida)
        return ordenar(resultado, clave=lambda p: (p.desde_sala, p.direccion, p.puerta_id))

    def _agregar_frontera(
        self, resultado: list[PuertaFrontera], retenida: _PuertaRetenida
    ) -> None:
        a_visitada = self._visitadas[retenida.sala_a]
        b_visitada = self._visitadas[retenida.sala_b]
        if a_visitada == b_visitada:
            return  # las dos alcanzables o ninguna: no es frontera
        if a_visitada:
            desde, hacia, direccion = retenida.sala_a, retenida.sala_b, retenida.direccion_a
        else:
            desde = retenida.sala_b
            hacia = retenida.sala_a
            direccion = _OPUESTA[indice_direccion(retenida.direccion_a)]
        resultado.append(
            PuertaFrontera(
                puerta_id=retenida.puerta_id,
                desde_sala=self._sala_por_indice[desde].id,
                hacia_sala=self._sala_por_indice[hacia].id,
                direccion=direccion,
                llave_requerida=retenida.llave_id,
            )
        )

    def _componentes(self) -> list[int]:
        """Componente topológica de cada sala NO visitada (ignora puertas)."""
        total = len(self._sala_por_indice)
        componente = [-1] * total
        siguiente = 0
        for inicio in range(total):
            if self._visitadas[inicio] or componente[inicio] != -1:
                continue
            cola: ColaEnlazada[int] = ColaEnlazada()
            cola.encolar(inicio)
            componente[inicio] = siguiente
            while not cola.esta_vacia():
                actual = cola.desencolar()
                for arista in self._adyacencia[actual]:
                    destino = arista.destino
                    if self._visitadas[destino] or componente[destino] != -1:
                        continue
                    componente[destino] = siguiente
                    cola.encolar(destino)
            siguiente += 1
        return componente

    def _bloqueos(
        self, frontera: list[PuertaFrontera], componentes: list[int]
    ) -> list[list[PuertaFrontera]]:
        """Para cada llave inobtenible, las puertas de frontera que la encierran."""
        bloqueos: list[list[PuertaFrontera]] = [[] for _ in self._llave_ids]
        for indice_llave in range(len(self._llave_ids)):
            if self._obtenidas[indice_llave]:
                continue
            componentes_llave: list[int] = []
            for ubicacion in self._por_llave[indice_llave]:
                indice_sala = self._indice_de_sala(ubicacion.sala)
                if indice_sala is None:
                    continue
                valor = componentes[indice_sala]
                if valor != -1 and valor not in componentes_llave:
                    componentes_llave.append(valor)
            for puerta in frontera:
                indice_sala = self._indice_de_sala(puerta.hacia_sala)
                if indice_sala is None:
                    continue
                if componentes[indice_sala] in componentes_llave:
                    bloqueos[indice_llave].append(puerta)
        return bloqueos

    def _inobtenibles(
        self,
        bloqueos: list[list[PuertaFrontera]],
        frontera: list[PuertaFrontera],
    ) -> list[LlaveInobtenible]:
        resultado: list[LlaveInobtenible] = []
        vistas: ConjuntoOrdenado[str] = ConjuntoOrdenado()
        for indice_llave in range(len(self._llave_ids)):
            if self._obtenidas[indice_llave]:
                continue
            llave_id = self._llave_ids[indice_llave]
            resultado.append(
                LlaveInobtenible(
                    id=llave_id,
                    ubicaciones=list(self._por_llave[indice_llave]),
                    puertas=list(bloqueos[indice_llave]),
                )
            )
            vistas.agregar(llave_id)
        # Una puerta puede exigir una llave que no aparece en la respuesta:
        # también se reporta como no obtenible (FR-022).
        for puerta in frontera:
            llave_id = puerta.llave_requerida
            if self._indice_llave.contiene(llave_id) or not vistas.agregar(llave_id):
                continue
            resultado.append(
                LlaveInobtenible(
                    id=llave_id,
                    ubicaciones=[],
                    puertas=[p for p in frontera if p.llave_requerida == llave_id],
                )
            )
        return ordenar(resultado, clave=lambda llave: llave.id)

    def _ciclo(self, bloqueos: list[list[PuertaFrontera]]) -> list[PasoCiclo]:
        total = len(self._llave_ids)
        dependencia: list[int | None] = [None] * total
        puerta_dependencia: list[str | None] = [None] * total
        for indice_llave in range(total):
            mejor: PuertaFrontera | None = None
            for puerta in bloqueos[indice_llave]:
                if mejor is None or (
                    puerta.llave_requerida,
                    puerta.desde_sala,
                    puerta.direccion,
                    puerta.puerta_id,
                ) < (
                    mejor.llave_requerida,
                    mejor.desde_sala,
                    mejor.direccion,
                    mejor.puerta_id,
                ):
                    mejor = puerta
            if mejor is None:
                continue
            requerida = self._indice_llave.obtener(mejor.llave_requerida)
            if requerida is not None:
                dependencia[indice_llave] = requerida
                puerta_dependencia[indice_llave] = mejor.puerta_id
        sin_ciclo: list[bool] = [False] * total
        for inicio in range(total):
            if sin_ciclo[inicio] or dependencia[inicio] is None:
                continue
            camino: list[int] = []
            posicion = [-1] * total
            actual: int | None = inicio
            while actual is not None:
                if posicion[actual] != -1:
                    claves = camino[posicion[actual]:]
                    return [
                        PasoCiclo(
                            llave=self._llave_ids[indice],
                            puerta_id=puerta_dependencia[indice] or "",
                            llave_requerida=self._llave_ids[dependencia[indice]],  # type: ignore[index]
                        )
                        for indice in claves
                    ]
                posicion[actual] = len(camino)
                camino.append(actual)
                actual = dependencia[actual]
            for indice in camino:
                sin_ciclo[indice] = True
        return []


def formatear_resultado(resultado: ResultadoVerificacion) -> str:
    """Texto legible del reporte, sin depender de la vista."""
    lineas: list[str] = [
        "Veredicto: RESOLUBLE" if resultado.resoluble else "Veredicto: NO RESOLUBLE"
    ]
    if resultado.resoluble:
        lineas.append("Orden de llaves: " + ", ".join(resultado.orden_llaves))
        return "\n".join(lineas)
    lineas.append(f"Motivo: {resultado.motivo}")
    if resultado.llaves_inobtenibles:
        lineas.append("")
        lineas.append("Llaves inobtenibles:")
        for llave in resultado.llaves_inobtenibles:
            sitios = "; ".join(
                f"sala {ubicacion.sala}"
                + (f" (enemigo {ubicacion.enemigo})" if ubicacion.enemigo else "")
                for ubicacion in llave.ubicaciones
            )
            lineas.append(f"  - {llave.id}: {sitios}")
    if resultado.frontera:
        lineas.append("")
        lineas.append("Frontera bloqueada:")
        for puerta in resultado.frontera:
            lineas.append(
                f"  - {puerta.puerta_id}: sala {puerta.desde_sala} -> sala {puerta.hacia_sala} "
                f"({puerta.direccion}), requiere {puerta.llave_requerida}"
            )
    if resultado.ciclo:
        lineas.append("")
        lineas.append("Ciclo:")
        pasos = " -> ".join(
            f"{paso.llave} -> {paso.puerta_id} (requiere {paso.llave_requerida})"
            for paso in resultado.ciclo
        )
        lineas.append(f"  {pasos} -> {resultado.ciclo[0].llave}")
    return "\n".join(lineas)
