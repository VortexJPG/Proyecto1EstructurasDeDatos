"""Persistencia local: catálogo, esqueleto y contenido.                [Persona B]

§4.4: la caché sobrevive al cierre del programa.
- Catálogo: un archivo JSON por ficha + ``version.txt`` con la versión global
  del catálogo. Si la versión cambió, se borra todo y se vuelve a pedir.
- Cripta: una carpeta por cripta con datos generales, esqueleto y contenido de
  cada sala + ``version.txt`` con la versión de la cripta.
Todo cuelga de un directorio base (por defecto ``datos_locales/``).
"""

from __future__ import annotations

import json
import os
from typing import Any

from cripta.modelo.datos import ContenidoSala, DatosCripta, DatosSala, Ficha


def _escribir_json(ruta: str, datos: Any) -> None:
    os.makedirs(os.path.dirname(ruta), exist_ok=True) if os.path.dirname(ruta) else None
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, ensure_ascii=False)


def _leer_json(ruta: str) -> Any:
    with open(ruta, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


class AlmacenCatalogo:
    def __init__(self, directorio: str) -> None:
        self.directorio = directorio
        os.makedirs(self.directorio, exist_ok=True)

    def _ruta_version(self) -> str:
        return os.path.join(self.directorio, "version.txt")

    def _ruta_ficha(self, tipo_id: str) -> str:
        seguro = tipo_id.replace("/", "_")
        return os.path.join(self.directorio, f"{seguro}.json")

    def version_guardada(self) -> str | None:
        ruta = self._ruta_version()
        if not os.path.exists(ruta):
            return None
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                return f.read().strip() or None
        except OSError:
            return None

    def validar_version(self, version_actual: str) -> bool:
        guardada = self.version_guardada()
        if guardada == version_actual:
            return True
        # invalidar
        self.invalidar_todo()
        try:
            with open(self._ruta_version(), "w", encoding="utf-8") as f:
                f.write(version_actual)
        except OSError:
            pass
        return False

    def contiene(self, tipo_id: str) -> bool:
        return os.path.exists(self._ruta_ficha(tipo_id))

    def leer(self, tipo_id: str) -> Ficha | None:
        ruta = self._ruta_ficha(tipo_id)
        if not os.path.exists(ruta):
            return None
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)
            return Ficha.desde_json(datos)
        except (OSError, ValueError, KeyError):
            return None

    def escribir(self, ficha: Ficha) -> None:
        ruta = self._ruta_ficha(ficha.id)
        try:
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(ficha.a_dict(), f, ensure_ascii=False)
        except OSError:
            pass

    def invalidar_todo(self) -> None:
        try:
            for nombre in os.listdir(self.directorio):
                if nombre != "version.txt" and nombre.endswith(".json"):
                    os.remove(os.path.join(self.directorio, nombre))
        except OSError:
            pass
        # reset version
        ruta = self._ruta_version()
        if os.path.exists(ruta):
            try:
                os.remove(ruta)
            except OSError:
                pass


class AlmacenCripta:
    def __init__(self, directorio: str, cripta_id: str) -> None:
        self.directorio = os.path.join(directorio, cripta_id)
        os.makedirs(self.directorio, exist_ok=True)

    def _ruta_version(self) -> str:
        return os.path.join(self.directorio, "version.txt")

    def version_guardada(self) -> str | None:
        ruta = self._ruta_version()
        if not os.path.exists(ruta):
            return None
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                return f.read().strip() or None
        except OSError:
            return None

    def validar_version(self, version_actual: str) -> bool:
        guardada = self.version_guardada()
        if guardada == version_actual:
            return True
        self._invalidar_contenido()
        try:
            with open(self._ruta_version(), "w", encoding="utf-8") as f:
                f.write(version_actual)
        except OSError:
            pass
        return False

    def _invalidar_contenido(self) -> None:
        for nombre in os.listdir(self.directorio):
            if nombre in ("version.txt",):
                continue
            ruta = os.path.join(self.directorio, nombre)
            try:
                if os.path.isfile(ruta):
                    os.remove(ruta)
            except OSError:
                pass

    def _escribir(self, nombre: str, datos: Any) -> None:
        _escribir_json(os.path.join(self.directorio, nombre), datos)

    def _leer(self, nombre: str) -> Any:
        ruta = os.path.join(self.directorio, nombre)
        if not os.path.exists(ruta):
            return None
        return _leer_json(ruta)

    def guardar_datos_generales(self, datos: DatosCripta) -> None:
        payload = {
            "id": datos.id,
            "version": datos.version,
            "salas_total": datos.salas_total,
            "paginas": datos.paginas,
            "salas_por_pagina": datos.salas_por_pagina,
            "sala_inicial": datos.sala_inicial,
            "sala_salida": datos.sala_salida,
            "llave_salida": datos.llave_salida,
            "presupuesto_solicitudes": datos.presupuesto_solicitudes,
            "inventario_max": datos.inventario_max,
            "jugador": {
                "vida_max": datos.jugador.vida_max,
                "ataque": datos.jugador.ataque,
                "defensa": datos.jugador.defensa,
                "velocidad": datos.jugador.velocidad,
            },
        }
        self._escribir("datos_generales.json", payload)

    def _sala_a_dict(self, sala: DatosSala) -> dict[str, Any]:
        salidas: dict[str, Any] = {}
        for s in sala.salidas:
            item = {"sala": s.sala_destino}
            if s.cerrada:
                item["cerrada"] = True
            if s.llave is not None:
                item["llave"] = s.llave
            if s.cierre_automatico is not None:
                item["cierre_automatico"] = s.cierre_automatico
            salidas[s.direccion] = item
        return {"id": sala.id, "nombre": sala.nombre, "salidas": salidas}

    def guardar_esqueleto(self, salas: list[DatosSala]) -> None:
        self._escribir("esqueleto.json", {"salas": [self._sala_a_dict(s) for s in salas]})

    def cargar_esqueleto(self) -> list[DatosSala] | None:
        datos = self._leer("esqueleto.json")
        if not isinstance(datos, dict):
            return None
        salas = datos.get("salas")
        if not isinstance(salas, list):
            return None
        try:
            return [DatosSala.desde_json(x) for x in salas]
        except (KeyError, ValueError, TypeError):
            return None

    def _contenido_a_dict(self, contenido: ContenidoSala) -> dict[str, Any]:
        return {
            "sala": contenido.sala,
            "enemigos": [
                {"instancia": e.instancia, "tipo": e.tipo, "vida": e.vida} for e in contenido.enemigos
            ],
            "objetos": list(contenido.objetos),
            "trampas": [{"instancia": t.instancia, "tipo": t.tipo} for t in contenido.trampas],
        }

    def guardar_contenido(self, contenido: list[ContenidoSala]) -> None:
        for c in contenido:
            self._escribir(f"contenido_{c.sala}.json", self._contenido_a_dict(c))

    def cargar_contenido(self, sala_id: int) -> ContenidoSala | None:
        datos = self._leer(f"contenido_{sala_id}.json")
        if not isinstance(datos, dict):
            return None
        try:
            return ContenidoSala.desde_json(datos)
        except (KeyError, ValueError, TypeError):
            return None

    def tiene_contenido(self, sala_id: int) -> bool:
        return os.path.exists(os.path.join(self.directorio, f"contenido_{sala_id}.json"))
