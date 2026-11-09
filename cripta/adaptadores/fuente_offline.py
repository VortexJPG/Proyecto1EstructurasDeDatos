"""Fuente de datos sin conexión (--offline).                           [Persona B]

§3.4: lee respuestas guardadas en disco y devuelve los MISMOS DTOs que
``ClienteHTTP``; el modelo no se entera de dónde vienen los datos. Las
lecturas offline no cuentan como solicitudes de red (§5.1).

Formato (el de ``datos_ejemplo/``): una carpeta por cripta con
``cripta.json``, ``salas_pagina_N.json``, ``contenido_*.json`` y
``catalogo_*.json``. Esqueleto y contenido se leen SOLO de la carpeta de esa
cripta (las salas de criptas distintas usan los mismos ids). El catálogo es
compartido entre criptas. Cuando el curso publique su paquete offline puede
hacer falta ajustar los nombres de archivo.
"""

from __future__ import annotations

import glob
import json
import os
from typing import Any

from cripta.adaptadores.fuente_datos import (
    ErrorFuenteDatos,
    EstadisticasRed,
    FuenteDatos,
)
from cripta.estructuras.ordenamiento import ordenar
from cripta.estructuras.tabla_ordenada import ConjuntoOrdenado, TablaOrdenada
from cripta.modelo.datos import (
    ContenidoSala,
    DatosCripta,
    Ficha,
    PaginaEsqueleto,
    ResumenCripta,
)


def _nombres_ordenados(nombres: list[str]) -> list[str]:
    """Nombres de archivo en orden alfabético (``os.listdir`` y ``glob`` no garantizan orden)."""
    return ordenar(list(nombres))


class FuenteOffline(FuenteDatos):
    def __init__(self, directorio: str) -> None:
        self.directorio = directorio
        self._presupuesto: int | None = None

    def _leer_json(self, ruta: str, operacion: str) -> Any:
        if not os.path.exists(ruta):
            raise ErrorFuenteDatos(operacion, f"archivo no encontrado: {ruta}")
        try:
            with open(ruta, "r", encoding="utf-8") as archivo:
                return json.load(archivo)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise ErrorFuenteDatos(operacion, str(exc)) from exc

    def _encontrar_archivo(self, nombre: str) -> str | None:
        # busca en directorio y subdirectorios de primer nivel
        candidatos = [os.path.join(self.directorio, nombre)]
        try:
            for entrada in os.listdir(self.directorio):
                sub = os.path.join(self.directorio, entrada)
                if os.path.isdir(sub):
                    candidatos.append(os.path.join(sub, nombre))
        except OSError:
            pass
        for ruta in candidatos:
            if os.path.exists(ruta):
                return ruta
        # búsqueda glob recursiva
        for ruta in glob.glob(os.path.join(self.directorio, "**", nombre), recursive=True):
            return ruta
        return None

    def _directorio_de(self, cripta_id: str) -> str:
        """Carpeta con las respuestas de UNA cripta.

        Esqueleto y contenido nunca se buscan fuera de esta carpeta: si hubiera
        varias criptas en el paquete, sus salas (que usan los mismos ids) se
        mezclarían. Se acepta:
        - ``<directorio>/<cripta_id>/`` (como ``datos_ejemplo/cripta-01/``),
        - ``<directorio>`` mismo, si su ``cripta.json`` es de esa cripta,
        - cualquier subcarpeta cuyo ``cripta.json`` tenga ese id.
        """
        candidatas = [os.path.join(self.directorio, cripta_id), self.directorio]
        try:
            for entrada in _nombres_ordenados(os.listdir(self.directorio)):
                sub = os.path.join(self.directorio, entrada)
                if os.path.isdir(sub):
                    candidatas.append(sub)
        except OSError:
            pass
        for carpeta in candidatas:
            ruta = os.path.join(carpeta, "cripta.json")
            if os.path.exists(ruta):
                datos = self._leer_json(ruta, "datos_cripta")
                if isinstance(datos, dict) and datos.get("id") == cripta_id:
                    return carpeta
        raise ErrorFuenteDatos("datos_cripta", f"no hay respuestas guardadas de {cripta_id} en {self.directorio}")

    def listar_criptas(self) -> list[ResumenCripta]:
        ruta = self._encontrar_archivo("criptas.json")
        if ruta is None:
            raise ErrorFuenteDatos("listar_criptas", "no se encontró criptas.json")
        datos = self._leer_json(ruta, "listar_criptas")
        items = datos.get("criptas", datos) if isinstance(datos, dict) else datos
        return [ResumenCripta.desde_json(x) for x in (items or [])]

    def datos_cripta(self, cripta_id: str) -> DatosCripta:
        ruta = os.path.join(self._directorio_de(cripta_id), "cripta.json")
        return DatosCripta.desde_json(self._leer_json(ruta, "datos_cripta"))

    def pagina_esqueleto(self, cripta_id: str, pagina: int) -> PaginaEsqueleto:
        ruta = os.path.join(self._directorio_de(cripta_id), f"salas_pagina_{pagina}.json")
        if not os.path.exists(ruta):
            raise ErrorFuenteDatos("pagina_esqueleto", f"no se encontró la página {pagina} de {cripta_id}")
        return PaginaEsqueleto.desde_json(self._leer_json(ruta, "pagina_esqueleto"))

    def _cargar_contenido_todo(self, cripta_id: str) -> list[ContenidoSala]:
        carpeta = self._directorio_de(cripta_id)
        archivos = _nombres_ordenados(glob.glob(os.path.join(carpeta, "contenido*.json")))
        resultado: list[ContenidoSala] = []
        vistos: ConjuntoOrdenado[int] = ConjuntoOrdenado()
        for ruta in archivos:
            datos = self._leer_json(ruta, "contenido")
            items = datos.get("contenido", datos) if isinstance(datos, dict) else datos
            for item in items or []:
                cs = ContenidoSala.desde_json(item)
                if vistos.agregar(cs.sala):
                    resultado.append(cs)
        return resultado

    def contenido(self, cripta_id: str, salas: list[int]) -> list[ContenidoSala]:
        por_sala: TablaOrdenada[int, ContenidoSala] = TablaOrdenada()
        for c in self._cargar_contenido_todo(cripta_id):
            por_sala.insertar(c.sala, c)
        salida = []
        for sala in salas:
            encontrado = por_sala.obtener(sala)
            if encontrado is not None:
                salida.append(encontrado)
        return salida

    def _cargar_catalogo_todo(self) -> list[Ficha]:
        archivos = []
        archivos.extend(glob.glob(os.path.join(self.directorio, "catalogo*.json")))
        archivos.extend(glob.glob(os.path.join(self.directorio, "**", "catalogo*.json"), recursive=True))
        # dedup preserving order
        vistos_rutas: ConjuntoOrdenado[str] = ConjuntoOrdenado()
        unicos = []
        for r in archivos:
            if vistos_rutas.agregar(os.path.normpath(r)):
                unicos.append(r)
        entidades: list[dict[str, Any]] = []
        for ruta in unicos:
            if "version" in os.path.basename(ruta):
                continue
            datos = self._leer_json(ruta, "catalogo")
            items = datos.get("entidades", datos) if isinstance(datos, dict) else datos
            for item in items or []:
                if isinstance(item, dict) and "id" in item and "clase" in item:
                    entidades.append(item)
        # dedup por id
        ids_vistos: ConjuntoOrdenado[str] = ConjuntoOrdenado()
        salida: list[Ficha] = []
        for ent in entidades:
            if ids_vistos.agregar(ent["id"]):
                salida.append(Ficha.desde_json(ent))
        return salida

    def catalogo(self, ids: list[str]) -> list[Ficha]:
        por_id: TablaOrdenada[str, Ficha] = TablaOrdenada()
        for ficha in self._cargar_catalogo_todo():
            por_id.insertar(ficha.id, ficha)
        salida = []
        for ident in ids:
            encontrada = por_id.obtener(ident)
            if encontrada is not None:
                salida.append(encontrada)
        return salida

    def version_cripta(self, cripta_id: str) -> str:
        return self.datos_cripta(cripta_id).version

    def version_catalogo(self) -> str:
        ruta = self._encontrar_archivo("catalogo_version.json")
        if ruta is None:
            raise ErrorFuenteDatos("version_catalogo", "no se encontró catalogo_version.json")
        datos = self._leer_json(ruta, "version_catalogo")
        if isinstance(datos, dict):
            return str(datos.get("version", datos.get("catalogo_version", "")))
        return str(datos)

    def establecer_presupuesto(self, presupuesto: int) -> None:
        self._presupuesto = presupuesto

    def solicitudes_restantes(self) -> int | None:
        if self._presupuesto is None:
            return None
        return self._presupuesto

    def estadisticas(self) -> EstadisticasRed:
        return EstadisticasRed(solicitudes_realizadas=0, presupuesto=self._presupuesto)
