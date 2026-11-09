"""DTOs con los datos que entrega el servicio.         [CONTRATO A↔B]"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from cripta.constantes import DIRECCIONES


@dataclass(slots=True)
class ResumenCripta:
    id: str
    nombre: str
    salas: int
    dificultad: int

    @staticmethod
    def desde_json(datos: Any) -> "ResumenCripta":
        return ResumenCripta(
            id=str(datos["id"]),
            nombre=str(datos["nombre"]),
            salas=int(datos["salas"]),
            dificultad=int(datos["dificultad"]),
        )


@dataclass(slots=True)
class EstadisticasIniciales:
    vida_max: int
    ataque: int
    defensa: int
    velocidad: int


@dataclass(slots=True)
class DatosCripta:
    id: str
    version: str
    salas_total: int
    paginas: int
    salas_por_pagina: int
    sala_inicial: int
    sala_salida: int
    llave_salida: str
    presupuesto_solicitudes: int
    inventario_max: int
    jugador: EstadisticasIniciales

    @staticmethod
    def desde_json(datos: Any) -> "DatosCripta":
        jugador = datos["jugador"]
        return DatosCripta(
            id=str(datos["id"]),
            version=str(datos["version"]),
            salas_total=int(datos["salas_total"]),
            paginas=int(datos["paginas"]),
            salas_por_pagina=int(datos["salas_por_pagina"]),
            sala_inicial=int(datos["sala_inicial"]),
            sala_salida=int(datos["sala_salida"]),
            llave_salida=str(datos["llave_salida"]),
            presupuesto_solicitudes=int(datos["presupuesto_solicitudes"]),
            inventario_max=int(datos["inventario_max"]),
            jugador=EstadisticasIniciales(
                vida_max=int(jugador["vida_max"]),
                ataque=int(jugador["ataque"]),
                defensa=int(jugador["defensa"]),
                velocidad=int(jugador["velocidad"]),
            ),
        )


@dataclass(slots=True)
class DatosSalida:
    direccion: str
    sala_destino: int
    cerrada: bool = False
    llave: str | None = None
    cierre_automatico: int | None = None


@dataclass(slots=True)
class DatosSala:
    id: int
    nombre: str
    salidas: list[DatosSalida] = field(default_factory=list)

    @staticmethod
    def desde_json(datos: Any) -> "DatosSala":
        salidas_raw = datos.get("salidas", {}) or {}
        salidas: list[DatosSalida] = []
        for direccion in salidas_raw:
            if str(direccion) not in DIRECCIONES:
                raise ValueError(f"sala {datos.get('id')}: dirección de salida desconocida {direccion!r}")
        # orden determinista N, S, E, O; solo las declaradas existen.
        for direccion in DIRECCIONES:
            valor = salidas_raw.get(direccion)
            if valor is None:
                continue
            salidas.append(
                DatosSalida(
                    direccion=str(direccion),
                    sala_destino=int(valor["sala"]),
                    cerrada=bool(valor.get("cerrada", False)),
                    llave=None if valor.get("llave") is None else str(valor.get("llave")),
                    cierre_automatico=None
                    if valor.get("cierre_automatico") is None
                    else int(valor.get("cierre_automatico")),
                )
            )
        return DatosSala(id=int(datos["id"]), nombre=str(datos["nombre"]), salidas=salidas)


@dataclass(slots=True)
class PaginaEsqueleto:
    pagina: int
    total_paginas: int
    salas: list[DatosSala]

    @staticmethod
    def desde_json(datos: Any) -> "PaginaEsqueleto":
        return PaginaEsqueleto(
            pagina=int(datos["pagina"]),
            total_paginas=int(datos["total_paginas"]),
            salas=[DatosSala.desde_json(x) for x in datos.get("salas", [])],
        )


@dataclass(slots=True)
class ColocacionEnemigo:
    instancia: str
    tipo: str
    vida: int | None = None


@dataclass(slots=True)
class ColocacionTrampa:
    instancia: str
    tipo: str


@dataclass(slots=True)
class ContenidoSala:
    sala: int
    enemigos: list[ColocacionEnemigo] = field(default_factory=list)
    objetos: list[str] = field(default_factory=list)
    trampas: list[ColocacionTrampa] = field(default_factory=list)

    @staticmethod
    def desde_json(datos: Any) -> "ContenidoSala":
        enemigos = [
            ColocacionEnemigo(
                instancia=str(e["instancia"]),
                tipo=str(e["tipo"]),
                vida=None if e.get("vida") is None else int(e["vida"]),
            )
            for e in datos.get("enemigos", [])
        ]
        objetos = [str(x) for x in datos.get("objetos", [])]
        trampas = [
            ColocacionTrampa(instancia=str(t["instancia"]), tipo=str(t["tipo"]))
            for t in datos.get("trampas", [])
        ]
        return ContenidoSala(
            sala=int(datos["sala"]), enemigos=enemigos, objetos=objetos, trampas=trampas
        )

    def tipos_referenciados(self) -> list[str]:
        tipos: list[str] = []
        for e in self.enemigos:
            tipos.append(e.tipo)
        for o in self.objetos:
            tipos.append(o)
        for t in self.trampas:
            tipos.append(t.tipo)
        return tipos


@dataclass(slots=True)
class Ficha:
    id: str
    clase: str
    nombre: str
    vida_max: int | None = None
    ataque: int | None = None
    defensa: int | None = None
    velocidad: int | None = None
    comportamiento: str | None = None
    suelta: list[str] = field(default_factory=list)
    regeneracion: int | None = None
    veneno: int | None = None
    peso: int | None = None
    valor: int | None = None
    ataque_bonus: int | None = None
    defensa_bonus: int | None = None
    cura: int | None = None
    modificador_velocidad: int | None = None
    duracion: int | None = None
    abre: str | int | None = None
    dano: int | None = None
    rearme: int | None = None

    @staticmethod
    def desde_json(datos: Any) -> "Ficha":
        dano = datos.get("dano")
        if dano is None:
            dano = datos.get("daño")
        abre = datos.get("abre")
        return Ficha(
            id=str(datos["id"]),
            clase=str(datos["clase"]),
            nombre=str(datos["nombre"]),
            vida_max=None if datos.get("vida_max") is None else int(datos.get("vida_max")),
            ataque=None if datos.get("ataque") is None else int(datos.get("ataque")),
            defensa=None if datos.get("defensa") is None else int(datos.get("defensa")),
            velocidad=None if datos.get("velocidad") is None else int(datos.get("velocidad")),
            comportamiento=None if datos.get("comportamiento") is None else str(datos.get("comportamiento")),
            suelta=[str(x) for x in datos.get("suelta", []) or []],
            regeneracion=None if datos.get("regeneracion") is None else int(datos.get("regeneracion")),
            veneno=None if datos.get("veneno") is None else int(datos.get("veneno")),
            peso=None if datos.get("peso") is None else int(datos.get("peso")),
            valor=None if datos.get("valor") is None else int(datos.get("valor")),
            ataque_bonus=None if datos.get("ataque_bonus") is None else int(datos.get("ataque_bonus")),
            defensa_bonus=None if datos.get("defensa_bonus") is None else int(datos.get("defensa_bonus")),
            cura=None if datos.get("cura") is None else int(datos.get("cura")),
            modificador_velocidad=None
            if datos.get("modificador_velocidad") is None
            else int(datos.get("modificador_velocidad")),
            duracion=None if datos.get("duracion") is None else int(datos.get("duracion")),
            abre=abre,
            dano=None if dano is None else int(dano),
            rearme=None if datos.get("rearme") is None else int(datos.get("rearme")),
        )

    def a_dict(self) -> dict[str, Any]:
        """Campos de la ficha como dict plano, para que el adaptador de disco lo
        escriba como JSON (el modelo no importa ``json``, §6)."""
        return asdict(self)
