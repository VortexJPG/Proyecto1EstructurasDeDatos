"""Adaptadores: red, modo --offline y disco, detrás de interfaces (§6).  [Persona B]

    fuente_datos.py     Interfaz FuenteDatos (contrato lógico común).
    cliente_http.py     FuenteDatos por HTTP: X-Cripta-Client-Id, 429, presupuesto.
    fuente_offline.py   FuenteDatos desde el paquete de respuestas en disco.
    almacen_disco.py    Persistencia de catálogo, esqueleto y contenido.
    cache_catalogo.py   ProveedorFichas: memoria (acotada) → disco → red.
    guardado.py         Partida en binario propio (+ JSON para comparar).
    bitacora_replay.py  Log de solo anexado para --replay.
    puntajes.py         Tabla de puntajes local.
"""
