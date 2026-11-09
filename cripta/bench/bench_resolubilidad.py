"""Benchmarks de resolubilidad: incremental vs. ingenuo.         [Persona B]

Evidencia para §5.4: el verificador incremental debe crecer de forma
aproximadamente lineal, mientras que repetir el recorrido por cada llave
(alternativa descartada, ``bench.ingenuo``) crece con K·(R+E).

Los tamaños y el límite son configurables por entorno (NFR-003):

- ``CRIPTA_BENCH_SALAS``: lista de tamaños, por defecto ``100,500,2000,5000``.
- ``CRIPTA_BENCH_LLAVES``: lista de K, por defecto ``5,10,20,40,80``.
- ``CRIPTA_BENCH_REPS``: repeticiones por caso, por defecto 7.
- ``CRIPTA_LIMITE_VERIFICACION_MS``: límite de la cripta grande, por defecto 200.

Se usan semillas fijas y se reporta el costo de UNA verificación. El límite se
comprueba con una cripta sintética de 300 salas (la escala de la cripta
publicada más grande).
"""

from __future__ import annotations

import os
import statistics
import time

from cripta.bench.ingenuo import verificar_ingenuo
from cripta.bench.runner import ResultadoMedicion
from cripta.bench.sinteticos import generar_cripta
from cripta.modelo.mapa import Mapa
from cripta.modelo.verificacion import Verificador


def _lista_entorno(nombre: str, defecto: str) -> list[int]:
    texto = os.environ.get(nombre, defecto)
    return [int(parte) for parte in texto.split(",") if parte.strip()]


TAMANOS = _lista_entorno("CRIPTA_BENCH_SALAS", "100,500,2000,5000")
LLAVES = _lista_entorno("CRIPTA_BENCH_LLAVES", "5,10,20,40,80")
REPETICIONES = int(os.environ.get("CRIPTA_BENCH_REPS", "7"))
LIMITE_MS = float(os.environ.get("CRIPTA_LIMITE_VERIFICACION_MS", "200"))
SEMILLA = 20261109


def _medir(caso: str, n: int, repeticiones: int, funcion) -> ResultadoMedicion:
    """Mide cada repetición y reporta la MEDIANA (no el promedio)."""
    tiempos: list[float] = []
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        funcion()
        tiempos.append(time.perf_counter() - inicio)
    mediana = statistics.median(tiempos)
    return ResultadoMedicion(
        "resolubilidad", caso, n, repeticiones, mediana * repeticiones
    )


def registrar(registro) -> None:
    for salas in TAMANOS:
        for llaves in LLAVES:
            if salas < llaves + 2:
                continue
            cripta = generar_cripta(
                SEMILLA, salas=salas, llaves=llaves, puertas_cambiantes=min(3, llaves)
            )
            mapa = Mapa.construir(cripta.datos, cripta.salas)
            registro.agregar(
                "resolubilidad",
                f"incremental salas={salas} llaves={llaves}",
                lambda c=cripta, m=mapa, s=salas, k=llaves: _medir(
                    f"incremental salas={s} llaves={k}",
                    s,
                    REPETICIONES,
                    lambda: Verificador(c.datos, m, c.llaves).verificar(),
                ),
            )
            registro.agregar(
                "resolubilidad",
                f"ingenuo salas={salas} llaves={llaves}",
                lambda c=cripta, s=salas, k=llaves: _medir(
                    f"ingenuo salas={s} llaves={k}",
                    s,
                    REPETICIONES,
                    lambda: verificar_ingenuo(c.datos, c.salas, c.llaves),
                ),
            )
    # Límite de §6.1 en la escala de la cripta publicada más grande (300 salas).
    cripta = generar_cripta(7, salas=300, llaves=4, puertas_cambiantes=2)
    mapa = Mapa.construir(cripta.datos, cripta.salas)
    registro.agregar(
        "resolubilidad",
        f"limite {LIMITE_MS:.0f} ms (300 salas)",
        lambda: _medir(
            f"limite {LIMITE_MS:.0f} ms (300 salas)",
            300,
            max(REPETICIONES, 20),
            lambda: Verificador(cripta.datos, mapa, cripta.llaves).verificar(),
        ),
    )


def revisar_limite(resultados: list[ResultadoMedicion]) -> None:
    """Imprime si la verificación de 300 salas cumple el límite configurado."""
    for resultado in resultados:
        if not resultado.caso.startswith("limite"):
            continue
        microsegundos = resultado.microsegundos_por_operacion()
        limite = LIMITE_MS * 1000.0
        estado = "OK" if microsegundos <= limite else "EXCEDE"
        print(
            f"[resolubilidad] {resultado.caso}: {microsegundos:.1f} us "
            f"(limite {LIMITE_MS:.0f} ms) -> {estado}"
        )
