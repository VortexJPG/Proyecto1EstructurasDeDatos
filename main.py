"""Punto de entrada de CRIPTA.

Uso (ver README.md):
    python main.py                        # partida interactiva
    python main.py --offline DIRECTORIO   # sin red, desde respuestas guardadas
    python main.py --replay partida.log   # reproduce una partida sin interacción
    python main.py --bench                # mediciones por subsistema
    python main.py --cache-size 25        # tope de fichas de catálogo en memoria
"""

import sys

from cripta.controlador.aplicacion import main

if __name__ == "__main__":
    sys.exit(main())
