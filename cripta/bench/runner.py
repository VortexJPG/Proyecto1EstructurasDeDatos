"""Ejecutor (harness) común de ``--bench``.                    [Persona A, punto 2]

Formato común para todas las mediciones (A y B):
- Cada caso es una función sin argumentos que devuelve un ``ResultadoMedicion``
  (subsistema, caso, tamaño n, repeticiones = operaciones medidas, segundos).
  ``microsegundos_por_operacion`` da el costo de UNA operación.
- ``detalle`` (opcional) lleva datos extra del caso: mediana, p95 y máximo,
  salas examinadas, cálculos reutilizados, memoria... Se imprime en su propia
  columna.
- ``muestras`` + ``estadisticas`` sirven para reportar mediana / p95 / máximo de
  varias repeticiones (constitución VI: semillas fijas, varias repeticiones,
  mediana o mínimo).
- ``revisar_limite`` imprime PASA / FALLA contra un límite en milisegundos
  (§6.1 de la Parte II). Los límites se pasan como argumento, no se escriben
  dentro de las mediciones.

El filtro de ``--bench FILTRO`` se compara con el subsistema y con el caso.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from cripta.estructuras.ordenamiento import ordenar


@dataclass(slots=True)
class ResultadoMedicion:
    subsistema: str
    caso: str
    n: int
    repeticiones: int
    segundos_total: float
    detalle: str = ""

    def microsegundos_por_operacion(self) -> float:
        if self.repeticiones <= 0:
            return 0.0
        return (self.segundos_total / self.repeticiones) * 1_000_000.0


@dataclass(slots=True)
class Estadisticas:
    mediana: float
    p95: float
    maximo: float
    minimo: float

    def en_ms(self) -> str:
        return (f"mediana {self.mediana * 1000:.3f} ms, p95 {self.p95 * 1000:.3f} ms, "
                f"máx {self.maximo * 1000:.3f} ms")


def estadisticas(muestras: list[float]) -> Estadisticas:
    """Mediana, percentil 95, máximo y mínimo (con el ordenamiento propio del proyecto)."""
    if not muestras:
        return Estadisticas(0.0, 0.0, 0.0, 0.0)
    orden = ordenar(list(muestras))
    n = len(orden)
    mediana = orden[n // 2] if n % 2 == 1 else (orden[n // 2 - 1] + orden[n // 2]) / 2
    p95 = orden[min(n - 1, (95 * n + 99) // 100 - 1)]
    return Estadisticas(mediana, p95, orden[-1], orden[0])


def muestras(funcion: Callable[[], object], repeticiones: int) -> list[float]:
    """Tiempo en segundos de ``repeticiones`` llamadas a ``funcion``, una por una."""
    resultado: list[float] = []
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        funcion()
        resultado.append(time.perf_counter() - inicio)
    return resultado


class RegistroBenchmarks:
    def __init__(self) -> None:
        self._casos: list[tuple[str, str, Callable[[], ResultadoMedicion]]] = []

    def agregar(self, subsistema: str, caso: str, funcion: Callable[[], ResultadoMedicion]) -> None:
        self._casos.append((subsistema, caso, funcion))

    def ejecutar(self, filtro: str | None = None) -> list[ResultadoMedicion]:
        resultados: list[ResultadoMedicion] = []
        for subsistema, caso, funcion in self._casos:
            if filtro is not None and filtro not in subsistema and filtro not in caso:
                continue
            try:
                resultados.append(funcion())
            except Exception as exc:
                print(f"[bench] error en {subsistema}/{caso}: {exc}")
        return resultados


def imprimir_tabla(resultados: list[ResultadoMedicion]) -> None:
    print(f"{'Subsistema':<22}{'Caso':<40}{'n':>8}{'reps':>8}{'us/op':>12}  Detalle")
    for r in resultados:
        print(
            f"{r.subsistema:<22}{r.caso:<40}{r.n:>8}{r.repeticiones:>8}"
            f"{r.microsegundos_por_operacion():>12.3f}  {r.detalle}"
        )


def revisar_limite(nombre: str, segundos: float, limite_ms: float) -> bool:
    """Imprime "PASA"/"FALLA" para una medición contra un límite de §6.1."""
    pasa = segundos * 1000 <= limite_ms
    print(f"[límite] {nombre}: {segundos * 1000:.3f} ms (límite {limite_ms:g} ms) -> {'PASA' if pasa else 'FALLA'}")
    return pasa


def ejecutar_bench(filtro: str | None = None) -> int:
    from cripta.bench.bench_datos import registrar as registrar_bench_datos
    from cripta.bench.bench_modelo import registrar as registrar_bench_modelo
    from cripta.bench.bench_resolubilidad import registrar as registrar_bench_resolubilidad, revisar_limite as revisar_limite_resolubilidad
    from cripta.bench.bench_rutas import registrar as registrar_bench_rutas, revisar_limites as revisar_limites_rutas
    from cripta.bench.bench_timeline import (
        imprimir_memoria,
        limpiar as limpiar_timeline,
        registrar as registrar_bench_timeline,
        revisar_limite as revisar_limite_timeline,
    )

    registro = RegistroBenchmarks()
    registrar_bench_datos(registro)
    registrar_bench_modelo(registro)
    registrar_bench_resolubilidad(registro)
    registrar_bench_timeline(registro)
    registrar_bench_rutas(registro)
    resultados = registro.ejecutar(filtro)
    imprimir_tabla(resultados)
    revisar_limites_rutas(resultados)
    if filtro is None or "resolubilidad" in filtro:
        revisar_limite_resolubilidad(resultados)
    if filtro is None or "timeline" in filtro:
        revisar_limite_timeline(resultados)
        imprimir_memoria()
        limpiar_timeline()
    if filtro is None or filtro in "frecuencias":
        from cripta.bench.frecuencias import imprimir_frecuencias

        imprimir_frecuencias()
    return 0
