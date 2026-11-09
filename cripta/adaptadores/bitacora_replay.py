"""Bitácora de partida (solo anexado) para --replay.                   [Persona B]

§4.11: archivo de texto. Encabezado con cripta, versiones, semilla y nombre;
después una línea por acción aceptada (``Accion.a_linea()``), que se agrega
al final y se escribe a disco enseguida (si el programa se cae, el log sirve
igual). Cada partida crea su propio archivo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from cripta.estructuras.tabla_ordenada import TablaOrdenada
from cripta.modelo.acciones import Accion


class ErrorReplayIncompatible(Exception):
    pass


@dataclass(slots=True)
class EncabezadoReplay:
    cripta_id: str
    version_cripta: str
    version_catalogo: str
    semilla: int
    nombre_jugador: str
    version_formato_log: int = 1

    def a_lineas(self) -> list[str]:
        return [
            f"CRIPTA_REPLAY {self.version_formato_log}",
            f"cripta_id={self.cripta_id}",
            f"version_cripta={self.version_cripta}",
            f"version_catalogo={self.version_catalogo}",
            f"semilla={self.semilla}",
            f"nombre_jugador={self.nombre_jugador}",
            "",
        ]

    @staticmethod
    def desde_lineas(lineas: list[str]) -> "EncabezadoReplay":
        datos: TablaOrdenada[str, str] = TablaOrdenada()
        version_formato = 1
        for line in lineas:
            texto = line.strip()
            if not texto:
                break
            if texto.startswith("CRIPTA_REPLAY"):
                partes = texto.split()
                if len(partes) == 2:
                    version_formato = int(partes[1])
                continue
            if "=" in texto:
                clave, valor = texto.split("=", 1)
            elif ":" in texto:
                clave, valor = texto.split(":", 1)
            else:
                continue
            datos.insertar(clave.strip(), valor.strip())
        for obligatorio in ("cripta_id", "version_cripta", "version_catalogo", "semilla"):
            if not datos.contiene(obligatorio):
                raise ErrorReplayIncompatible(f"el encabezado del log no tiene '{obligatorio}'")
        return EncabezadoReplay(
            cripta_id=datos.obtener("cripta_id"),
            version_cripta=datos.obtener("version_cripta"),
            version_catalogo=datos.obtener("version_catalogo"),
            semilla=int(datos.obtener("semilla")),
            nombre_jugador=datos.obtener("nombre_jugador", ""),
            version_formato_log=version_formato,
        )


class EscritorReplay:
    def __init__(self, ruta: str, encabezado: EncabezadoReplay) -> None:
        self.ruta = ruta
        # Archivo nuevo por partida; después solo se le AGREGAN líneas (§4.11).
        # Abrirlo en modo "a" mezclaría dos encabezados en el mismo log.
        self._archivo = open(ruta, "w", encoding="utf-8")
        for linea in encabezado.a_lineas():
            self._archivo.write(linea + "\n")
        self._archivo.flush()

    def registrar(self, accion: Accion) -> None:
        self._archivo.write(accion.a_linea() + "\n")
        self._archivo.flush()

    def cerrar(self) -> None:
        self._archivo.close()


class LectorReplay:
    def __init__(self, ruta: str) -> None:
        self.ruta = ruta
        with open(ruta, "r", encoding="utf-8") as archivo:
            self._lineas = [line.rstrip("\n") for line in archivo.readlines()]

    def encabezado(self) -> EncabezadoReplay:
        # primer bloque hasta línea vacía
        bloque: list[str] = []
        for line in self._lineas:
            if line.strip() == "":
                break
            bloque.append(line)
        return EncabezadoReplay.desde_lineas(bloque)

    def acciones(self) -> Iterator[Accion]:
        # saltar encabezado y primer vacío
        i = 0
        while i < len(self._lineas) and self._lineas[i].strip() != "":
            i += 1
        # saltar vacíos
        while i < len(self._lineas) and self._lineas[i].strip() == "":
            i += 1
        for line in self._lineas[i:]:
            if line.strip():
                yield Accion.desde_linea(line)
