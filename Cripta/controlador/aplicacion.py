"""Arranque del programa y argumentos de línea de comandos.          [Persona B]

Por defecto los datos vienen del servicio HTTP del curso.

Banderas:
    --gui              jugar en una ventana con sprites pixel art (necesita pygame-ce);
                       sin esta bandera se juega en la terminal
    --offline [DIR]    leer las respuestas desde disco en vez de la red (§3.4);
                       sin DIR se usa el paquete local ``datos_ejemplo/``
    --replay ARCHIVO   reproducir una partida sin interacción (§4.11)
    --bench [FILTRO]   mediciones por subsistema, sin vista (§5.3)
    --cache-size N     fichas de catálogo en memoria (por defecto 25, §4.4)
    --semilla N        semilla de la partida (opcional)
    --cripta ID        saltar la selección de cripta (ahorra GET /criptas)
    --nombre NOMBRE    saltar la pregunta del nombre del jugador
    --datos DIR        directorio de datos locales (por defecto datos_locales/)

--replay y --bench no instancian la vista interactiva (§6), así que tampoco
usan la ventana aunque se pase --gui.
Cualquier error de red o de formato termina con un mensaje claro, no con un
traceback de ``requests``. Lo mismo si falta pygame para --gui: la consola,
--replay y --bench funcionan sin él.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import TYPE_CHECKING

from cripta.adaptadores.bitacora_replay import ErrorReplayIncompatible
from cripta.adaptadores.fuente_datos import ErrorFuenteDatos, FuenteDatos
from cripta.adaptadores.fuente_offline import FuenteOffline
from cripta.constantes import CACHE_SIZE_POR_DEFECTO
from cripta.controlador.controlador import Controlador, OpcionesEjecucion

if TYPE_CHECKING:
    from cripta.vista.vista_consola import VistaConsola
    from cripta.vista.vista_grafica import VistaGrafica

# Paquete local que usa ``--offline`` cuando no se indica un directorio.
DIRECTORIO_EJEMPLO = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "datos_ejemplo")


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cripta", description="CRIPTA: juego de mazmorra en la terminal")
    parser.add_argument("--gui", action="store_true",
                        help="jugar en una ventana con sprites (necesita pygame-ce)")
    parser.add_argument("--offline", nargs="?", const=DIRECTORIO_EJEMPLO, default=None, metavar="DIR",
                        help="leer respuestas guardadas en vez de usar la red (sin DIR: datos_ejemplo/)")
    parser.add_argument("--replay", type=str, default=None, help="archivo de bitácora a reproducir")
    parser.add_argument("--bench", nargs="?", const="", default=None, metavar="FILTRO",
                        help="ejecutar benchmarks (opcional: solo los que contienen FILTRO, p. ej. agenda)")
    parser.add_argument("--cache-size", type=int, default=CACHE_SIZE_POR_DEFECTO, dest="cache_size",
                        help="fichas en memoria")
    parser.add_argument("--semilla", type=int, default=None, help="semilla de la partida")
    parser.add_argument("--cripta", type=str, default=None, dest="cripta_id", help="id de cripta")
    parser.add_argument("--datos", type=str, default="datos_locales", help="directorio de datos locales")
    parser.add_argument("--nombre", type=str, default=None, dest="nombre_jugador", help="nombre del jugador")
    return parser


def crear_fuente(argumentos: argparse.Namespace) -> FuenteDatos:
    """``FuenteOffline`` si se pasó --offline; si no, ``ClienteHTTP``.

    Es el ÚNICO lugar del programa donde se decide si se está offline.
    ``requests`` solo se importa si de verdad se va a usar la red.
    """
    if argumentos.offline:
        return FuenteOffline(argumentos.offline)
    try:
        from cripta.adaptadores.cliente_http import BASE_URL, ClienteHTTP
    except ImportError as exc:
        raise ErrorFuenteDatos(
            "iniciar cliente HTTP",
            f"falta una dependencia ({exc}); ejecuta: pip install -r requirements.txt, o juega sin red con --offline",
        ) from exc
    return ClienteHTTP(BASE_URL)


class FaltaPygame(Exception):
    """Se pidió --gui pero pygame-ce no está instalado."""


def crear_vista(grafica: bool) -> VistaConsola | VistaGrafica:
    """La ventana (``--gui``) o la consola. pygame solo se importa si se pide la ventana."""
    if not grafica:
        from cripta.vista.vista_consola import VistaConsola

        return VistaConsola()
    try:
        from cripta.vista.vista_grafica import VistaGrafica
    except ImportError as exc:
        if exc.name != "pygame":
            raise
        raise FaltaPygame() from exc
    return VistaGrafica()


def main(argv: list[str] | None = None) -> int:
    """Despacha a modo interactivo, --replay o --bench. Devuelve el código de salida."""
    args = construir_parser().parse_args(argv)
    if args.bench is not None:
        from cripta.bench.runner import ejecutar_bench

        return ejecutar_bench(args.bench or None)
    opciones = OpcionesEjecucion(
        directorio_datos=args.datos,
        cache_size=args.cache_size,
        offline=args.offline,
        cripta_id=args.cripta_id,
        semilla=args.semilla,
        nombre_jugador=args.nombre_jugador,
    )
    try:
        fuente = crear_fuente(args)
        if args.replay:
            from cripta.controlador.replay import ReproductorReplay

            reproductor = ReproductorReplay(args.replay, fuente, opciones)
            resumen = reproductor.ejecutar()
            print(reproductor.describir(resumen))
            return 0
        vista = crear_vista(args.gui)
        try:
            Controlador(fuente, opciones, vista).ejecutar_interactivo()
        finally:
            vista.cerrar()
        return 0
    except FaltaPygame:
        print(
            "La ventana necesita pygame-ce. Instálalo con: pip install -r requirements.txt\n"
            "(o juega en la terminal, sin --gui)",
            file=sys.stderr,
        )
        return 1
    except ErrorReplayIncompatible as exc:
        print(f"No se puede garantizar una reproducción fiel: {exc}", file=sys.stderr)
        return 2
    except ErrorFuenteDatos as exc:
        print(f"Error de datos: {exc}", file=sys.stderr)
        if not args.offline:
            print("Para jugar sin red usa: python main.py --offline", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Error de archivo: {exc}", file=sys.stderr)
        return 1
    except EOFError:  # se acabó la entrada de la consola o se cerró la ventana
        print("\nSesión terminada.", file=sys.stderr)
        return 0
    except KeyboardInterrupt:
        print("\nSesión interrumpida.", file=sys.stderr)
        return 130
