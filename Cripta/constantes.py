"""Constantes de las REGLAS del juego (§2 del enunciado).        [Compartido]

Aquí solo van valores que el enunciado fija para TODAS las criptas.
Nada específico de una cripta (números de sala, ids, páginas, presupuesto,
estadísticas) puede escribirse en el código (§9): eso viene del servicio.
"""

# Direcciones válidas. El orden fijo N, S, E, O sirve para recorrer las
# salidas siempre igual (importa para el errante y para el replay).
DIRECCIONES: tuple[str, ...] = ("N", "S", "E", "O")

# --- Reloj y costos de acción (§2.3) ---------------------------------------
VELOCIDAD_REFERENCIA = 100
COSTO_MOVER = 100
COSTO_ATACAR = 100
COSTO_ESPERAR = 100
COSTO_USAR = 50
COSTO_EQUIPAR = 50
COSTO_RECOGER = 25
COSTO_SOLTAR = 25
COSTO_ABRIR = 50
COSTO_ACTIVACION_ENEMIGO = 100  # primera acción de un enemigo recién activado (§2.4)

# --- Combate (§2.6) --------------------------------------------------------
AZAR_DANO_MIN = 0
AZAR_DANO_MAX = 4  # randint(0, 4) incluye ambos extremos
DANO_MINIMO = 1

# --- Rastro (§2.9) ---------------------------------------------------------
ANTIGUEDAD_MAXIMA_RASTRO = 400  # un rastro con antigüedad >= 400 ya no sirve

# --- Efectos (§2.10) -------------------------------------------------------
VENENO_INTERVALO = 80
VENENO_DURACION = 400
REGENERACION_INTERVALO = 200
TRAMPA_REARME_POR_DEFECTO = 300

# --- Retroceso (§2.11, §4.6) -----------------------------------------------
MAX_ACCIONES_REVERSIBLES = 5

# --- Bitácora en pantalla (§4.8) -------------------------------------------
MENSAJES_VISIBLES = 20

# --- Red y caché (§3.4, §4.4) ----------------------------------------------
CACHE_SIZE_POR_DEFECTO = 25
MAX_SALAS_POR_CONSULTA = 10
MAX_IDS_POR_CONSULTA = 10
TIMEOUT_HTTP_SEGUNDOS = 10


def indice_direccion(direccion: str) -> int:
    """Convierte 'N' / 'S' / 'E' / 'O' en su posición dentro de DIRECCIONES.

    Las salidas de una sala se guardan en una lista de 4 posiciones indexada
    con este valor (evita usar dict). Lanza ValueError si la dirección no es
    válida.
    """
    for indice in range(len(DIRECCIONES)):
        if DIRECCIONES[indice] == direccion:
            return indice
    raise ValueError(f"Dirección inválida: {direccion!r} (se esperaba N, S, E u O)")
