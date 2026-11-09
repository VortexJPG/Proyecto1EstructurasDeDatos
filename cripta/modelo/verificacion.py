"""Verificación de resolubilidad de una cripta (Parte II §3.5, §5.4).  [Persona B]

Un único recorrido incremental decide si la cripta puede ganarse y, de paso,
produce el orden de llaves, la frontera bloqueada, las llaves inobtenibles y el
ciclo concreto. Las puertas cerradas se retienen asociadas a su llave; cuando
la llave se obtiene, se liberan solo esas puertas y la expansión continúa sin
reiniciar el recorrido.

Estructuras (constitución I): ``TablaOrdenada``/``ConjuntoOrdenado``,
``ColaEnlazada`` y ``ListaDoble`` propias. No se usa ``dict``, ``set``,
``heapq``, ``bisect``, ``collections`` ni ``networkx``.

Coste esperado: O(salas + salidas + puertas liberadas + llaves·log llaves).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from cripta.constantes import indice_direccion
from cripta.estructuras.cola import ColaEnlazada
from cripta.estructuras.lista_doble import ListaDoble
from cripta.estructuras.ordenamiento import ordenar
from cripta.estructuras.tabla_ordenada import ConjuntoOrdenado, TablaOrdenada
from cripta.modelo.datos import UbicacionLlave

if TYPE_CHECKING:
    from cripta.modelo.datos import DatosCripta
    from cripta.modelo.mapa import Mapa, Puerta, Sala, Salida

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
class _PuertaRetenida:
    puerta_id: str
    llave_id: str
    sala_a: int
    sala_b: int
    direccion_a: str


@dataclass(slots=True)
class _Dependencia:
    puerta_id: str
    llave_requerida: str


class Verificador:
    """Verificador incremental de una cripta ya construida.

    Recibe el ``Mapa`` recién construido con el esqueleto (estado inicial) y la
    respuesta de llaves. No modifica el mapa ni consulta el servicio.
    """

    def __init__(self, datos: DatosCripta, mapa: Mapa, llaves: list[UbicacionLlave]) -> None:
        self.datos = datos
        self.mapa = mapa
        self.llaves = llaves
        # Ubicaciones por llave y llaves por sala, ambas ordenadas por id.
        self._por_llave: TablaOrdenada[str, list[UbicacionLlave]] = TablaOrdenada()
        self._por_sala: TablaOrdenada[int, list[str]] = TablaOrdenada()
        self._indexar_llaves(llaves)
        # Estado del recorrido.
        self._visitadas: ConjuntoOrdenado[int] = ConjuntoOrdenado()
        self._obtenidas: ConjuntoOrdenado[str] = ConjuntoOrdenado()
        self._orden: list[str] = []
        self._cola: ColaEnlazada[int] = ColaEnlazada()
        self._retenidas: TablaOrdenada[str, ListaDoble[_PuertaRetenida]] = TablaOrdenada()
        self._retenidas_ids: ConjuntoOrdenado[str] = ConjuntoOrdenado()

    # --- API ------------------------------------------------------------------

    def verificar(self) -> ResultadoVerificacion:
        self._encolar(self.datos.sala_inicial)
        while not self._cola.esta_vacia():
            self._expandir(self._cola.desencolar())
        return self._construir_resultado()

    # --- recorrido ------------------------------------------------------------

    def _indexar_llaves(self, llaves: list[UbicacionLlave]) -> None:
        for ubicacion in llaves:
            lista = self._por_llave.obtener(ubicacion.id)
            if lista is None:
                lista = []
                self._por_llave.insertar(ubicacion.id, lista)
            lista.append(ubicacion)
        for llave_id, lista in self._por_llave.pares():
            lista = ordenar(lista, clave=lambda u: (u.sala, u.enemigo or ""))
            self._por_llave.insertar(llave_id, lista)
            for ubicacion in lista:
                claves = self._por_sala.obtener(ubicacion.sala)
                if claves is None:
                    claves = []
                    self._por_sala.insertar(ubicacion.sala, claves)
                if llave_id not in claves:  # varias ubicaciones de la misma llave en una sala
                    claves.append(llave_id)
        for sala_id, claves in self._por_sala.pares():
            self._por_sala.insertar(sala_id, ordenar(claves))

    def _encolar(self, sala_id: int) -> None:
        if self._visitadas.agregar(sala_id):
            self._cola.encolar(sala_id)

    def _expandir(self, sala_id: int) -> None:
        sala = self.mapa.sala(sala_id)
        self._obtener_llaves_de(sala_id)
        for salida in sala.salidas:
            if salida is not None:
                self._explorar(sala, salida)

    def _obtener_llaves_de(self, sala_id: int) -> None:
        claves = self._por_sala.obtener(sala_id)
        if claves is None:
            return
        for llave_id in claves:
            if self._obtenidas.agregar(llave_id):
                self._orden.append(llave_id)
                self._liberar(llave_id)

    def _explorar(self, sala: Sala, salida: Salida) -> None:
        puerta = salida.puerta
        if puerta is None or not puerta.cerrada:
            self._encolar(salida.destino.id)
            return
        if puerta.llave is None or self._obtenidas.contiene(puerta.llave):
            self._encolar(salida.destino.id)
            return
        self._retener(puerta, sala.id, salida.destino.id, salida.direccion)

    def _retener(self, puerta: Puerta, desde: int, hacia: int, direccion: str) -> None:
        if not self._retenidas_ids.agregar(puerta.id):
            return
        lista = self._retenidas.obtener(puerta.llave)  # type: ignore[arg-type]
        if lista is None:
            lista = ListaDoble()
            self._retenidas.insertar(puerta.llave, lista)  # type: ignore[arg-type]
        lista.agregar_al_final(
            _PuertaRetenida(puerta.id, puerta.llave, desde, hacia, direccion)  # type: ignore[arg-type]
        )

    def _liberar(self, llave_id: str) -> None:
        lista = self._retenidas.obtener(llave_id)
        if lista is None:
            return
        for retenida in lista:
            self._encolar(retenida.sala_a)
            self._encolar(retenida.sala_b)
        self._retenidas.eliminar(llave_id)

    # --- resultado ------------------------------------------------------------

    def _construir_resultado(self) -> ResultadoVerificacion:
        llave_salida = self.datos.llave_salida
        obtenida = self._obtenidas.contiene(llave_salida)
        por_puerta = self._salida_por_puerta_con_llave()
        resoluble = obtenida and por_puerta
        resultado = ResultadoVerificacion(
            resoluble=resoluble,
            llave_salida_obtenida=obtenida,
            salida_por_puerta_con_llave=por_puerta,
        )
        if resoluble:
            resultado.orden_llaves = list(self._orden)
            return resultado
        resultado.motivo = self._motivo(llave_salida, obtenida, por_puerta)
        frontera = self._frontera()
        componentes = self._componentes()
        bloqueos = self._bloqueos(frontera, componentes)
        resultado.frontera = frontera
        resultado.llaves_inobtenibles = self._inobtenibles(bloqueos, frontera)
        resultado.ciclo = self._ciclo(bloqueos)
        return resultado

    def _salida_por_puerta_con_llave(self) -> bool:
        salida_id = self.datos.sala_salida
        llave = self.datos.llave_salida
        for sala_id in self._visitadas:
            sala = self.mapa.sala(sala_id)
            for salida in sala.salidas:
                if salida is None or salida.destino.id != salida_id:
                    continue
                puerta = salida.puerta
                if puerta is not None and puerta.llave == llave:
                    return True
        return False

    def _motivo(self, llave_salida: str, obtenida: bool, por_puerta: bool) -> str:
        if not self._por_llave.contiene(llave_salida):
            return "la llave de salida no aparece en la consulta de llaves"
        if not obtenida:
            return "la llave de salida no es obtenible"
        if not por_puerta:
            return "no hay una salida a la sala final que requiera la llave de salida"
        return "la cripta no es resoluble"

    def _frontera(self) -> list[PuertaFrontera]:
        resultado: list[PuertaFrontera] = []
        for _, lista in self._retenidas.pares():
            for retenida in lista:
                a_visitada = self._visitadas.contiene(retenida.sala_a)
                b_visitada = self._visitadas.contiene(retenida.sala_b)
                if a_visitada == b_visitada:
                    continue  # las dos alcanzables o ninguna: no es frontera
                if a_visitada:
                    desde, hacia, direccion = retenida.sala_a, retenida.sala_b, retenida.direccion_a
                else:
                    desde, hacia, direccion = (
                        retenida.sala_b,
                        retenida.sala_a,
                        _OPUESTA[indice_direccion(retenida.direccion_a)],
                    )
                resultado.append(
                    PuertaFrontera(
                        puerta_id=retenida.puerta_id,
                        desde_sala=desde,
                        hacia_sala=hacia,
                        direccion=direccion,
                        llave_requerida=retenida.llave_id,
                    )
                )
        return ordenar(resultado, clave=lambda p: (p.desde_sala, p.direccion, p.puerta_id))

    def _componentes(self) -> TablaOrdenada[int, int]:
        """Componente topológica de cada sala NO visitada (ignora puertas)."""
        componente: TablaOrdenada[int, int] = TablaOrdenada()
        siguiente = 0
        for sala in self.mapa:
            if self._visitadas.contiene(sala.id) or componente.contiene(sala.id):
                continue
            cola: ColaEnlazada[int] = ColaEnlazada()
            cola.encolar(sala.id)
            componente.insertar(sala.id, siguiente)
            while not cola.esta_vacia():
                actual = cola.desencolar()
                for salida in self.mapa.sala(actual).salidas:
                    if salida is None:
                        continue
                    destino = salida.destino.id
                    if self._visitadas.contiene(destino) or componente.contiene(destino):
                        continue
                    componente.insertar(destino, siguiente)
                    cola.encolar(destino)
            siguiente += 1
        return componente

    def _bloqueos(
        self, frontera: list[PuertaFrontera], componentes: TablaOrdenada[int, int]
    ) -> TablaOrdenada[str, list[PuertaFrontera]]:
        """Para cada llave inobtenible, las puertas de frontera que la encierran."""
        bloqueos: TablaOrdenada[str, list[PuertaFrontera]] = TablaOrdenada()
        for llave_id in self._por_llave.claves():
            if self._obtenidas.contiene(llave_id):
                continue
            componentes_llave: list[int] = []
            for ubicacion in self._por_llave.obtener(llave_id) or []:
                valor = componentes.obtener(ubicacion.sala)
                if valor is not None and valor not in componentes_llave:
                    componentes_llave.append(valor)
            puertas = [
                puerta
                for puerta in frontera
                if componentes.obtener(puerta.hacia_sala) in componentes_llave
            ]
            bloqueos.insertar(llave_id, puertas)
        return bloqueos

    def _inobtenibles(
        self,
        bloqueos: TablaOrdenada[str, list[PuertaFrontera]],
        frontera: list[PuertaFrontera],
    ) -> list[LlaveInobtenible]:
        resultado: list[LlaveInobtenible] = []
        vistas: ConjuntoOrdenado[str] = ConjuntoOrdenado()
        for llave_id, puertas in bloqueos.pares():
            resultado.append(
                LlaveInobtenible(
                    id=llave_id,
                    ubicaciones=list(self._por_llave.obtener(llave_id) or []),
                    puertas=list(puertas),
                )
            )
            vistas.agregar(llave_id)
        # Una puerta puede exigir una llave que no aparece en la respuesta:
        # también se reporta como no obtenible (FR-022).
        for puerta in frontera:
            llave_id = puerta.llave_requerida
            if self._por_llave.contiene(llave_id) or not vistas.agregar(llave_id):
                continue
            resultado.append(
                LlaveInobtenible(
                    id=llave_id,
                    ubicaciones=[],
                    puertas=[p for p in frontera if p.llave_requerida == llave_id],
                )
            )
        return ordenar(resultado, clave=lambda llave: llave.id)

    def _ciclo(self, bloqueos: TablaOrdenada[str, list[PuertaFrontera]]) -> list[PasoCiclo]:
        dependencia: TablaOrdenada[str, _Dependencia] = TablaOrdenada()
        for llave_id, puertas in bloqueos.pares():
            mejor: PuertaFrontera | None = None
            for puerta in puertas:
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
            if mejor is not None:
                dependencia.insertar(llave_id, _Dependencia(mejor.puerta_id, mejor.llave_requerida))

        sin_ciclo: ConjuntoOrdenado[str] = ConjuntoOrdenado()
        for inicio in bloqueos.claves():
            if sin_ciclo.contiene(inicio) or not dependencia.contiene(inicio):
                continue
            camino: list[str] = []
            posicion: TablaOrdenada[str, int] = TablaOrdenada()
            actual = inicio
            while dependencia.contiene(actual):
                if posicion.contiene(actual):
                    desde = posicion.obtener(actual)
                    claves = camino[desde:]  # type: ignore[index]
                    return [
                        PasoCiclo(
                            llave=llave_id,
                            puerta_id=dependencia.obtener(llave_id).puerta_id,  # type: ignore[union-attr]
                            llave_requerida=dependencia.obtener(llave_id).llave_requerida,  # type: ignore[union-attr]
                        )
                        for llave_id in claves
                    ]
                posicion.insertar(actual, len(camino))
                camino.append(actual)
                actual = dependencia.obtener(actual).llave_requerida  # type: ignore[union-attr]
            for llave_id in camino:
                sin_ciclo.agregar(llave_id)
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
