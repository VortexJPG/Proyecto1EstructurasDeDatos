"""Fichas en memoria y criptas sintéticas deterministas.            [Persona B]

``FichasEnMemoria`` sirve a ``--bench`` y a las pruebas sin red.
``generar_cripta`` construye una cripta completa a partir de una semilla, para
medir resolubilidad, línea de tiempo y comportamiento sin depender de las
criptas publicadas (Parte II, punto 3 B→A).

Diseño del generador:
- Un pasillo 1..N con salidas N (avance) y S (retroceso).
- ``m`` llaves encadenadas. Hay ``m`` puertas cerradas: la puerta j requiere la
  llave j y está al final del segmento j. La llave j está dentro del segmento
  j, antes de su puerta, así que la cripta es resoluble por construcción.
- Con ``resoluble=False`` la última llave (``llave_salida``) se coloca detrás
  de su propia puerta: la cripta queda no resoluble con un ciclo concreto.
- Salidas laterales E que saltan una sala dentro del mismo segmento (nunca
  cruzan una puerta), para que el recorrido no sea una única cadena.
- Costos de salida aleatorios en ``[costo_min, costo_max]`` y, opcionalmente,
  ``puertas_cambiantes`` con ``cierre_automatico``.
- Una llave puede quedar en el campo ``suelta`` de un enemigo errante.

Todo usa un único ``random.Random(semilla)`` y no usa ``dict`` ni ``set``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from cripta.estructuras.tabla_ordenada import TablaOrdenada
from cripta.modelo.datos import (
    ColocacionEnemigo,
    ContenidoSala,
    DatosCripta,
    DatosSala,
    DatosSalida,
    EstadisticasIniciales,
    Ficha,
    UbicacionLlave,
)
from cripta.modelo.puertos import FichaNoDisponible, ProveedorFichas


class FichasEnMemoria(ProveedorFichas):
    """``ProveedorFichas`` sin caché ni disco: todas las fichas en una ``TablaOrdenada``."""

    def __init__(self, fichas: list[Ficha]) -> None:
        self._tabla: TablaOrdenada[str, Ficha] = TablaOrdenada()
        for f in fichas:
            self._tabla.insertar(f.id, f)

    def obtener(self, tipo_id: str) -> Ficha:
        valor = self._tabla.obtener(tipo_id)
        if valor is None:
            raise FichaNoDisponible(tipo_id)
        return valor

    def fijar(self, tipo_id: str) -> None:
        return None

    def liberar(self, tipo_id: str) -> None:
        return None


@dataclass(slots=True)
class CriptaSintetica:
    """Paquete completo que puede usar el juego, las pruebas o ``--bench``."""

    datos: DatosCripta
    salas: list[DatosSala] = field(default_factory=list)
    contenido: list[ContenidoSala] = field(default_factory=list)
    llaves: list[UbicacionLlave] = field(default_factory=list)
    fichas: list[Ficha] = field(default_factory=list)

    def proveedor_fichas(self) -> FichasEnMemoria:
        return FichasEnMemoria(self.fichas)


def generar_cripta(
    semilla: int,
    salas: int = 20,
    llaves: int = 3,
    costo_min: int = 50,
    costo_max: int = 300,
    puertas_cambiantes: int = 0,
    llave_en_enemigo: int | None = None,
    resoluble: bool = True,
    lado_extra: float = 0.25,
) -> CriptaSintetica:
    """Genera una cripta determinista.

    ``llave_en_enemigo`` es el índice (0-based) de la llave que suelta un
    enemigo errante; el resto quedan en el suelo. ``lado_extra`` es la
    probabilidad de una salida E que salta una sala dentro del segmento.
    """
    if salas < 4:
        raise ValueError("salas debe ser >= 4")
    if llaves < 1 or salas < llaves + 2:
        raise ValueError("hacen falta al menos dos salas por llave y una salida")
    if costo_min < 1 or costo_max < costo_min:
        raise ValueError("costos inválidos")
    if not 0 <= puertas_cambiantes <= llaves:
        raise ValueError("puertas_cambiantes debe estar entre 0 y llaves")
    if llave_en_enemigo is not None and not 0 <= llave_en_enemigo < llaves:
        raise ValueError("llave_en_enemigo fuera de rango")
    if not 0.0 <= lado_extra <= 1.0:
        raise ValueError("lado_extra debe estar entre 0 y 1")

    rng = random.Random(semilla)
    ids = [f"itm_sint_llave_{j + 1}" for j in range(llaves)]
    m = llaves
    base = (salas - 1) // m
    cortes = [j * base for j in range(1, m)] + [salas - 1]
    segmentos: list[tuple[int, int]] = []
    inicio = 1
    for corte in cortes:
        segmentos.append((inicio, corte))
        inicio = corte + 1

    # Sala de cada llave: una por segmento, antes de la puerta de ese segmento.
    salas_llave = [rng.randint(a, b) for a, b in segmentos]
    if not resoluble:
        salas_llave[m - 1] = salas  # la llave de salida queda detrás de su puerta

    enemigo_id = None
    tipo_enemigo = None
    if llave_en_enemigo is not None:
        enemigo_id = f"e-sint-{llave_en_enemigo + 1}"
        tipo_enemigo = f"ent_sint_errante_{llave_en_enemigo + 1}"

    salidas: list[DatosSala] = []
    for sala in range(1, salas + 1):
        por_direccion: list[DatosSalida] = []
        if sala < salas:
            corte = _indice_corte(sala, cortes)
            if corte >= 0:
                por_direccion.append(
                    DatosSalida(
                        "N",
                        sala + 1,
                        cerrada=True,
                        llave=ids[corte],
                        cierre_automatico=(
                            rng.randint(200, 600) if corte < puertas_cambiantes else None
                        ),
                    )
                )
            else:
                por_direccion.append(DatosSalida("N", sala + 1, costo=_costo(rng, costo_min, costo_max)))
        if sala > 1:
            por_direccion.append(DatosSalida("S", sala - 1, costo=_costo(rng, costo_min, costo_max)))
        if sala + 2 <= salas and _salto_libre(sala, cortes) and rng.random() < lado_extra:
            por_direccion.append(DatosSalida("E", sala + 2, costo=_costo(rng, costo_min, costo_max)))
        salidas.append(DatosSala(id=sala, nombre=f"Sala {sala}", salidas=por_direccion))

    contenido: list[ContenidoSala] = []
    for sala in range(1, salas + 1):
        objetos = [
            ids[j]
            for j in range(m)
            if salas_llave[j] == sala and j != llave_en_enemigo
        ]
        enemigos = []
        if llave_en_enemigo is not None and salas_llave[llave_en_enemigo] == sala:
            enemigos.append(ColocacionEnemigo(instancia=enemigo_id, tipo=tipo_enemigo))
        contenido.append(ContenidoSala(sala=sala, enemigos=enemigos, objetos=objetos))

    ubicaciones = [
        UbicacionLlave(
            id=ids[j],
            sala=salas_llave[j],
            enemigo=enemigo_id if j == llave_en_enemigo else None,
        )
        for j in range(m)
    ]

    fichas: list[Ficha] = [
        Ficha(
            id=ids[j],
            clase="llave",
            nombre=f"Llave sintética {j + 1}",
            peso=1,
            valor=0,
        )
        for j in range(m)
    ]
    if llave_en_enemigo is not None:
        fichas.append(
            Ficha(
                id=tipo_enemigo,
                clase="enemigo",
                nombre="Errante sintético",
                vida_max=10,
                ataque=1,
                defensa=0,
                velocidad=100,
                comportamiento="errante",
                suelta=[ids[llave_en_enemigo]],
            )
        )

    paginas = max(1, (salas + 49) // 50)
    datos = DatosCripta(
        id=f"sintetica-{semilla}-{salas}-{llaves}",
        version=f"sint-{semilla}-{salas}-{llaves}",
        salas_total=salas,
        paginas=paginas,
        salas_por_pagina=50,
        sala_inicial=1,
        sala_salida=salas,
        llave_salida=ids[-1],
        presupuesto_solicitudes=max(10, salas // 5 + 10),
        inventario_max=max(5, llaves + 2),
        jugador=EstadisticasIniciales(vida_max=100, ataque=10, defensa=2, velocidad=100),
    )
    return CriptaSintetica(
        datos=datos,
        salas=salidas,
        contenido=contenido,
        llaves=ubicaciones,
        fichas=fichas,
    )


def _costo(rng: random.Random, minimo: int, maximo: int) -> int:
    return rng.randint(minimo, maximo)


def _indice_corte(sala: int, cortes: list[int]) -> int:
    """Posición de ``sala`` en ``cortes`` o -1 (la puerta sale de esa sala)."""
    for indice in range(len(cortes)):
        if cortes[indice] == sala:
            return indice
    return -1


def _salto_libre(sala: int, cortes: list[int]) -> bool:
    """True si saltar de ``sala`` a ``sala + 2`` no cruza ninguna puerta."""
    return _indice_corte(sala, cortes) < 0 and _indice_corte(sala + 1, cortes) < 0
