"""Benchmarks de la línea de tiempo: tiempo y memoria.            [Persona B]

Evidencia para §5.5 / §6.3-B:

- tiempo de consulta para K ∈ {10, 25, 50, 100} y para la alternativa **sin
  puntos de control**;
- memoria estimada: checkpoints + acciones;
- partida sintética de ``CRIPTA_TIMELINE_ACCIONES`` acciones (5000 por defecto)
  con la cripta publicada de ejemplo, sin red y con vida alta para que la
  partida no termine.

Variables de entorno (NFR-004):

- ``CRIPTA_TIMELINE_ACCIONES``: acciones de la partida (5000).
- ``CRIPTA_TIMELINE_KS``: lista de K (``10,25,50,100``).
- ``CRIPTA_TIMELINE_CONSULTAS``: consultas por caso (25).
- ``CRIPTA_LIMITE_HISTORIA_MS``: límite de una consulta (50).
"""

from __future__ import annotations

import os
import pickle
import shutil
import statistics
import tempfile
import time

from cripta.adaptadores.fuente_offline import FuenteOffline
from cripta.bench.runner import ResultadoMedicion
from cripta.controlador.controlador import Controlador, OpcionesEjecucion
from cripta.modelo.acciones import Accion, TipoAccion
from cripta.modelo.timeline import K_POR_DEFECTO

DATOS_EJEMPLO = os.path.join(os.path.dirname(__file__), "..", "..", "datos_ejemplo")
ACCIONES = int(os.environ.get("CRIPTA_TIMELINE_ACCIONES", "5000"))
KS = [int(x) for x in os.environ.get("CRIPTA_TIMELINE_KS", "10,25,50,100").split(",") if x.strip()]
CONSULTAS = int(os.environ.get("CRIPTA_TIMELINE_CONSULTAS", "25"))
LIMITE_MS = float(os.environ.get("CRIPTA_LIMITE_HISTORIA_MS", "50"))
SEMILLA = 20261110
SIN_PUNTOS = 10**9

_DIRECTORIO = tempfile.mkdtemp(prefix="cripta_bench_tl_")
_PARTIDAS: list[tuple[int, Controlador]] = []


def _partida(k: int) -> Controlador:
    for valor, controlador in _PARTIDAS:
        if valor == k:
            return controlador
    controlador = Controlador(
        FuenteOffline(DATOS_EJEMPLO),
        OpcionesEjecucion(
            directorio_datos=os.path.join(_DIRECTORIO, f"k{k}"),
            cache_size=25,
            checkpoint_cada=k,
        ),
        None,
    )
    controlador.preparar_cripta("cripta-02")
    controlador._datos.jugador.vida_max = 10**9
    controlador.iniciar_partida("Bench", SEMILLA, registrar_replay=False)
    esperar = Accion(TipoAccion.ESPERAR)
    for _ in range(ACCIONES):
        if controlador.juego.esta_terminada():
            break
        if not controlador.ejecutar_accion(esperar).aceptada:
            break
    _PARTIDAS.append((k, controlador))
    return controlador


def _consultar(controlador: Controlador, indice: int) -> None:
    linea = controlador.timeline
    if linea is None:
        return
    linea.resumen(linea.estado_en_accion(indice), f"#{indice + 1}")


def _medir_tiempo(caso: str, k: int) -> ResultadoMedicion:
    controlador = _partida(k)
    linea = controlador.timeline
    total = len(linea.acciones) if linea is not None else 0
    repeticiones = 1 if k == SIN_PUNTOS else CONSULTAS
    tiempos: list[float] = []
    for i in range(repeticiones):
        indice = total if k == SIN_PUNTOS else (i * 37) % (total + 1)
        inicio = time.perf_counter()
        _consultar(controlador, indice)
        tiempos.append(time.perf_counter() - inicio)
    mediana = statistics.median(tiempos)
    return ResultadoMedicion(
        "timeline", caso, total, repeticiones, mediana * repeticiones
    )


def registrar(registro) -> None:
    for k in KS:
        registro.agregar(
            "timeline",
            f"consulta k={k}",
            lambda k=k: _medir_tiempo(f"consulta k={k}", k),
        )
    registro.agregar(
        "timeline",
        "consulta sin puntos de control",
        lambda: _medir_tiempo("consulta sin puntos de control", SIN_PUNTOS),
    )


def _memoria(k: int) -> tuple[int, int, int]:
    controlador = _partida(k)
    linea = controlador.timeline
    bytes_checkpoints = sum(len(pickle.dumps(p.estado)) for p in linea.checkpoints)
    bytes_acciones = len(pickle.dumps(linea.acciones))
    return len(linea.checkpoints), bytes_checkpoints, bytes_acciones


def imprimir_memoria() -> None:
    print("\nMemoria de la línea (estimada con pickle; sin contar el estado vivo):")
    print(f"{'K':>10}{'checkpoints':>14}{'MB puntos':>12}{'KB acciones':>14}")
    for k in KS + [SIN_PUNTOS]:
        cantidad, bytes_cp, bytes_acc = _memoria(k)
        etiqueta = "sin CP" if k == SIN_PUNTOS else str(k)
        print(
            f"{etiqueta:>10}{cantidad:>14}{bytes_cp / (1024 * 1024):>12.3f}"
            f"{bytes_acc / 1024:>14.1f}"
        )


def revisar_limite(resultados: list[ResultadoMedicion]) -> None:
    for resultado in resultados:
        if resultado.caso != f"consulta k={K_POR_DEFECTO}":
            continue
        microsegundos = resultado.microsegundos_por_operacion()
        limite = LIMITE_MS * 1000.0
        estado = "OK" if microsegundos <= limite else "EXCEDE"
        print(
            f"[timeline] consulta con K por defecto ({K_POR_DEFECTO}): "
            f"{microsegundos:.1f} us (limite {LIMITE_MS:.0f} ms) -> {estado}"
        )


def limpiar() -> None:
    for _, controlador in _PARTIDAS:
        controlador.cerrar_recursos()
    _PARTIDAS.clear()
    shutil.rmtree(_DIRECTORIO, ignore_errors=True)
