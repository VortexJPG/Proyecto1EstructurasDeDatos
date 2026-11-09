"""Sprites pixel art de la ventana, dibujados como texto.             [Persona A]

Cada sprite es una cuadrícula de 16 x 16 (los íconos, de 8 x 8): una lista
de filas donde cada carácter es un pixel y su color sale de la PALETA ("."
es transparente). La ventana los convierte en imágenes una sola vez al abrir
y los agranda x3 sin suavizar, por eso se ven "pixelados".

Ventajas de dibujarlos así: no dependen de archivos de imagen ni de licencias
de terceros, y se pueden revisar y cambiar con cualquier editor.

Este módulo NO importa pygame (son solo datos y funciones de texto), así que
se puede probar aunque pygame no esté instalado.

Qué sprite le toca a cada cosa se decide por palabras clave del id o del
nombre de la ficha ("rata", "daga", "negra"...). Si no coincide ninguna, se
usa uno genérico según la clase: así una cripta nueva con enemigos u objetos
desconocidos igual se dibuja.
"""

from __future__ import annotations

# --- Paleta: (carácter, color RGB) -------------------------------------------------
# Se busca recorriendo la tupla (son pocos colores y se hace una sola vez al abrir).
PALETA: tuple[tuple[str, tuple[int, int, int]], ...] = (
    ("K", (24, 20, 30)),      # contorno
    ("k", (58, 50, 66)),      # gris oscuro
    ("g", (112, 106, 122)),   # gris
    ("G", (168, 164, 178)),   # gris claro
    ("W", (242, 240, 230)),   # blanco
    ("w", (200, 192, 172)),   # hueso (sombra)
    ("r", (140, 30, 38)),     # rojo oscuro
    ("R", (218, 58, 52)),     # rojo
    ("p", (240, 150, 150)),   # rosado
    ("o", (176, 100, 44)),    # bronce
    ("O", (236, 168, 56)),    # dorado
    ("y", (255, 230, 120)),   # amarillo
    ("b", (92, 60, 38)),      # café oscuro
    ("B", (142, 94, 54)),     # café
    ("n", (192, 144, 94)),    # beige
    ("s", (238, 194, 150)),   # piel
    ("S", (196, 146, 108)),   # piel (sombra)
    ("u", (38, 62, 128)),     # azul oscuro
    ("U", (66, 118, 206)),    # azul
    ("c", (150, 210, 240)),   # celeste (vidrio)
    ("v", (38, 104, 58)),     # verde oscuro
    ("V", (78, 176, 88)),     # verde
    ("l", (176, 232, 126)),   # verde claro
    ("m", (78, 40, 100)),     # morado oscuro
    ("M", (150, 84, 186)),    # morado
    ("f", (255, 122, 40)),    # llama naranja
    # Piedra del suelo y de las paredes.
    ("1", (40, 36, 46)),      # junta del suelo
    ("2", (66, 60, 74)),      # losa
    ("3", (84, 78, 94)),      # losa (brillo)
    ("4", (56, 46, 58)),      # junta de la pared
    ("5", (100, 84, 92)),     # ladrillo
    ("6", (128, 110, 118)),   # ladrillo (brillo)
    ("7", (28, 24, 32)),      # sombra
)

TRANSPARENTE = "."
TAMANO = 16  # lado de un sprite normal
TAMANO_ICONO = 8  # lado de un ícono


def color_de(caracter: str) -> tuple[int, int, int] | None:
    """Color de un carácter de la paleta (None = transparente). ValueError si no existe."""
    if caracter == TRANSPARENTE:
        return None
    for clave, color in PALETA:
        if clave == caracter:
            return color
    raise ValueError(f"El carácter {caracter!r} no está en la paleta")


def recolorear(filas: list[str], cambios: str) -> list[str]:
    """Copia de ``filas`` cambiando colores. ``cambios`` = pares "de a": "RU ru" → R por U y r por u.

    Cada pixel se cambia una sola vez (en "Oo yO" la y pasa a O, pero esa O
    nueva no pasa después a o).
    """
    pares = cambios.split()

    def cambiar(caracter: str) -> str:
        for par in pares:
            if par[0] == caracter:
                return par[1]
        return caracter

    return ["".join(cambiar(caracter) for caracter in fila) for fila in filas]


# =============================================================================
# Terreno
# =============================================================================

SUELO = [
    "2222222122222221",
    "2333322123333221",
    "2322222122222221",
    "2222222122222221",
    "2222222122222221",
    "2222222122222221",
    "2222222122222221",
    "1111111111111111",
    "2221222222212222",
    "2221233332212333",
    "2221232222212322",
    "2221222222212222",
    "2221222222212222",
    "2221222222212222",
    "2221222222212222",
    "1111111111111111",
]

SUELO_GRIETA = [
    "2222222122222221",
    "2333322123333221",
    "2322222122222221",
    "2222222122212221",
    "2222222122221221",
    "2222222122222121",
    "2222222122222221",
    "1111111111111111",
    "2221222222212222",
    "2221233332212333",
    "2221232122212322",
    "2221222212212222",
    "2221222221212222",
    "2221222222212222",
    "2221222222212222",
    "1111111111111111",
]

PARED = [
    "4444444444444444",
    "6555555465555554",
    "5555555455555554",
    "5555555455555554",
    "4444444444444444",
    "5554655555554655",
    "5554555555554555",
    "5554555555554555",
    "4444444444444444",
    "6555555465555554",
    "5555555455555554",
    "5555555455555554",
    "4444444444444444",
    "5554655555554655",
    "5554555555554555",
    "7777777777777777",
]

PARED_BORDE = [
    "7777777777777777",
    "7444444474444447",
    "7444444474444447",
    "7444444474444447",
    "7777777777777777",
    "7444474444444447",
    "7444474444444447",
    "7444474444444447",
    "7777777777777777",
    "7444444474444447",
    "7444444474444447",
    "7444444474444447",
    "7777777777777777",
    "7444474444444447",
    "7444474444444447",
    "7777777777777777",
]

PUERTA_CERRADA = [
    "4444444444444444",
    "4555KKKKKKKK5554",
    "455KbBBbBBbBK554",
    "45KbBBbBBbBBbK54",
    "45KBBbBBbBBbBK54",
    "45KkkkkkkkkkkK54",
    "45KBBbBBbBBbBK54",
    "45KBBbBKKBBbBK54",
    "45KBBbKOOKBbBK54",
    "45KBBbKOOKBbBK54",
    "45KBBbBKKBBbBK54",
    "45KkkkkkkkkkkK54",
    "45KBBbBBbBBbBK54",
    "45KBBbBBbBBbBK54",
    "45KBBbBBbBBbBK54",
    "77KKKKKKKKKKKK77",
]

# Puerta de la salida de la cripta: hierro oscuro con remaches dorados.
PUERTA_SALIDA = [
    "4444444444444444",
    "4555KKKKKKKK5554",
    "455KkmmkmmkmK554",
    "45KkmmkmmkmmkK54",
    "45KmmkOmkmOkmK54",
    "45KOOOOOOOOOOK54",
    "45KmmkmmkmmkmK54",
    "45KmmkmKKmmkmK54",
    "45KmmkKyyKmkmK54",
    "45KmmkKOOKmkmK54",
    "45KmmkmKKmmkmK54",
    "45KOOOOOOOOOOK54",
    "45KmmkOmkmOkmK54",
    "45KmmkmmkmmkmK54",
    "45KmmkmmkmmkmK54",
    "77KKKKKKKKKKKK77",
]

PUERTA_ABIERTA = [
    "4444444444444444",
    "4555KKKKKKKK5554",
    "455KB7777777K554",
    "45KBb77777777K54",
    "45KBb77777777K54",
    "45KBb77777777K54",
    "45KBb77777777K54",
    "45KBb77777777K54",
    "45KBb77777777K54",
    "45KBb77777777K54",
    "45KBb77777777K54",
    "45KBb11111111K54",
    "45KBb11111111K54",
    "45KBb12121212K54",
    "45KBb22222222K54",
    "77KK2222222222K7",
]

# Pasaje sin puerta (nunca se cierra).
PASO = [
    "4444444444444444",
    "4555KKKKKKKK5554",
    "455K77777777K554",
    "45K7777777777K54",
    "45K7777777777K54",
    "45K7777777777K54",
    "45K7777777777K54",
    "45K7777777777K54",
    "45K7777777777K54",
    "45K7777777777K54",
    "45K7777777777K54",
    "45K1111111111K54",
    "45K1111111111K54",
    "45K1212121212K54",
    "45K2222222222K54",
    "77K2222222222K77",
]

# Antorcha en la pared (dos cuadros para que la llama parpadee).
ANTORCHA_PARED_1 = [
    "................",
    "................",
    ".......f........",
    "......fyf.......",
    "......fyf.......",
    ".....fyWyf......",
    ".....fyyyf......",
    "......fyf.......",
    ".....KKKKK......",
    ".....KoooK......",
    "......KoK.......",
    "......KbK.......",
    "......KbK.......",
    ".......K........",
    "................",
    "................",
]

ANTORCHA_PARED_2 = [
    "................",
    "........f.......",
    ".......ff.......",
    "......fyf.......",
    ".....fyyf.......",
    ".....fyWyf......",
    "......fyyf......",
    "......fyf.......",
    ".....KKKKK......",
    ".....KoooK......",
    "......KoK.......",
    "......KbK.......",
    "......KbK.......",
    ".......K........",
    "................",
    "................",
]

# =============================================================================
# Personajes
# =============================================================================

JUGADOR = [
    "................",
    ".....KKKKKK.....",
    "....KGWGGGGK..K.",
    "...KGWGGGGGGKKWK",
    "...KGGGGGGGGKKWK",
    "...KkkkkkkkkKKWK",
    "...KsKssssKsKKWK",
    "...KssssssssKKWK",
    "....KSssssSK.KWK",
    "...KKUUUUUUKKKWK",
    "..KsKUUUUUUKsOOO",
    "..KsKUuUUuUKsKbK",
    "..KKKOOOOOOKKKKK",
    "....KUUKKUUK....",
    "....KbbKKbbK....",
    "....KKKKKKKK....",
]

RATA = [
    "................",
    "................",
    "................",
    "................",
    "...KK...........",
    "..KpBK.KKKKK....",
    ".KBBBBKBBBBBKK..",
    "KBRBBBBBBBBBBBK.",
    "KBBBBBBBBBBBBBBK",
    "pKBBBBBBBBBBBnnK",
    ".KnnBBBBBBBBBnnK",
    "..KnnnBBBBBBnKpp",
    "...KpKKKKKKpKK.p",
    "...KpK....KpK.p.",
    "..............p.",
    "................",
]

ESQUELETO = [
    ".....KKKKKK.....",
    "....KWWWWWWK....",
    "...KWWWWWWWwK...",
    "...KWKKWWKKwK...",
    "...KWKRWWKRwK...",
    "...KWWWKKWWwK...",
    "....KWKWKWKK....",
    ".....KKKKKK.....",
    "..KK..KWWK..KK..",
    ".KwWKKWKKWKKWwK.",
    ".KwK.KWWWWK.KwK.",
    ".KK..KWKKWK..KK.",
    "......KWWK......",
    ".....KWKKWK.....",
    ".....KWK.KWK....",
    "....KKK...KKK...",
]

ARANA = [
    "................",
    "......KKKK......",
    ".....KmMmmK.....",
    "..KKKmMMmmmKKK..",
    ".K..KmMmmmmK..K.",
    "K...KmmRRmmK...K",
    "..KKKmmrrmmKKK..",
    ".K..KKmmmmKK..K.",
    ".K...KKKKKK...K.",
    "...KKKkkkkKKK...",
    "..K..KRkkRK..K..",
    ".K..KKkkkkKK..K.",
    ".K.K..KKKK..K.K.",
    "..K...W..W...K..",
    "..K..........K..",
    "................",
]

MURCIELAGO = [
    "................",
    "................",
    "................",
    "................",
    "K.....K..K.....K",
    "KK....KKKK....KK",
    "KMK..KmmmmK..KMK",
    "KMMKKmRmmRmKKMMK",
    "KMMMmmmmmmmmmMMK",
    ".KMMKmmmmmmKMMK.",
    "..KK.KmmmmK.KK..",
    "......KmmK......",
    ".......KK.......",
    "................",
    "................",
    "................",
]

LOBO = [
    "................",
    "................",
    "................",
    "..K.K...........",
    ".KgKgK.......KK.",
    ".KggggK.....KgK.",
    "KgRgggGKKKKKgK..",
    "KggggggggggggK..",
    "KKKgggggggggggK.",
    "..KGGggggggggggK",
    "..KGGGggggggggK.",
    "...KGGKKKKKKgK..",
    "...KgK....KgK...",
    "...KgK....KgK...",
    "...KKK....KKK...",
    "................",
]

GOLEM = [
    "................",
    ".....KKKKKK.....",
    "....KnnnnnnK....",
    "....KnVnnVnK....",
    "....KnnnnnnK....",
    "..KKKKKKKKKKKK..",
    ".KnnKnnnnnnKnnK.",
    ".KnnKnnBnnnKnnK.",
    ".KnnKnnnnBnKnnK.",
    ".KBBKnnnnnnKBBK.",
    ".KKKKKKKKKKKKKK.",
    "....KnnK.KnnK...",
    "...KnnnK.KnnnK..",
    "...KKKKK.KKKKK..",
    "................",
    "................",
]

# Enemigo genérico (cuando el nombre no coincide con ninguno conocido).
LIMO = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "......KKKK......",
    "....KKVVVVKK....",
    "...KVVlVVVVVK...",
    "..KVVllVVVVVVK..",
    "..KVVKVVVVKVVK..",
    ".KVVVKVVVVKVVVK.",
    ".KVVVVVVVVVVVVK.",
    ".KvVVVVVVVVVVvK.",
    "..KKKKKKKKKKKK..",
    "................",
]

# =============================================================================
# Objetos
# =============================================================================

ESPADA = [
    ".............KK.",
    "............KWGK",
    "...........KWGK.",
    "..........KWGK..",
    ".........KWGK...",
    "........KWGK....",
    ".......KWGK.....",
    "..KK..KWGK......",
    "..KOKKWGK.......",
    "...KOWGK........",
    "....KOK.........",
    "...KbKOK........",
    "..KbK.KOK.......",
    ".KbK...KK.......",
    ".KK.............",
    "................",
]

DAGA = [
    "................",
    "................",
    "................",
    "..........KK....",
    ".........KGoK...",
    "........KGoK....",
    ".......KGGK.....",
    "...KK.KGoK......",
    "...KOKGGK.......",
    "....KOGK........",
    ".....KOK........",
    "....KbKOK.......",
    "...KbK.KK.......",
    "...KK...........",
    "................",
    "................",
]

CORAZA = [
    "................",
    "................",
    "..KKKK....KKKK..",
    ".KBnnBK..KBnnBK.",
    ".KBnnnBKKBnnnBK.",
    ".KBnnnnnnnnnnBK.",
    "..KKnnnnnnnnKK..",
    "...KnnnbbnnnK...",
    "...KnnnbbnnnK...",
    "...KnnbnnbnnK...",
    "...KnnnnnnnnK...",
    "...KbOObbOObK...",
    "...KnnnnnnnnK...",
    "....KKKKKKKK....",
    "................",
    "................",
]

ESCUDO = [
    "................",
    "..KKKKKKKKKKKK..",
    "..KOOOOOOOOOOK..",
    "..KOUUUUOUUUOK..",
    "..KOUUUUOUUUOK..",
    "..KOUUUUOUUUOK..",
    "..KOOOOOOOOOOK..",
    "..KOUUUUOUUUOK..",
    "...KOUUUOUUOK...",
    "...KOUUUOUUOK...",
    "....KOUUOUOK....",
    ".....KOUOOK.....",
    "......KOOK......",
    ".......KK.......",
    "................",
    "................",
]

POCION = [
    "................",
    "......KKKK......",
    "......KbbK......",
    ".....KKKKKK.....",
    "......KccK......",
    "......KccK......",
    ".....KcccWK.....",
    "....KccccccK....",
    "...KRRRRRRRRK...",
    "..KRRWRRRRRRRK..",
    "..KRWRRRRRRRRK..",
    "..KRRRRRRRRRRK..",
    "..KrRRRRRRRRrK..",
    "...KrrRRRRrrK...",
    "....KKKKKKKK....",
    "................",
]

# Poción que cambia la velocidad: la misma botella, líquido azul.
POCION_VELOZ = recolorear(POCION, "RU ru")

ANTIDOTO = [
    "................",
    "......KKKK......",
    "......KbbK......",
    "......KKKK......",
    ".......KK.......",
    "......KccK......",
    ".....KcWccK.....",
    ".....KVVVVK.....",
    ".....KVWWVK.....",
    ".....KWWWWK.....",
    ".....KVWWVK.....",
    ".....KVVVVK.....",
    ".....KvVVvK.....",
    "......KKKK......",
    "................",
    "................",
]

LLAVE = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "..KKKK..........",
    ".KOOOOK.........",
    "KOK..KOKKKKKKKK.",
    "KOK..KOyOOOOOOOK",
    "KOK..KOKKKKKOKOK",
    ".KOOOOK....KOKOK",
    "..KKKK.....KKKKK",
    "................",
    "................",
    "................",
    "................",
]

LLAVE_BRONCE = recolorear(LLAVE, "Oo yO")
LLAVE_NEGRA = recolorear(LLAVE, "Og yG")
LLAVE_AZUL = recolorear(LLAVE, "OU yc")

ANTORCHA = [
    "..........f.....",
    ".........fyf....",
    "........fyWyf...",
    "........fyyyf...",
    ".........fyf....",
    "........KKKKK...",
    "........KoooK...",
    ".......KbBK.....",
    "......KbBK......",
    ".....KbBK.......",
    "....KbBK........",
    "...KbBK.........",
    "..KbBK..........",
    "..KKK...........",
    "................",
    "................",
]

PERGAMINO = [
    "................",
    "..KKKKKKKKKKKK..",
    ".KnnnnnnnnnnnnK.",
    ".KBBBBBBBBBBBBK.",
    "..KWWWWWWWWWWK..",
    "..KWggggggWWWK..",
    "..KWWWWWWWWWWK..",
    "..KWgggggWggWK..",
    "..KWWWWWWMMWWK..",
    "..KWggggWMMMWK..",
    "..KWWWWWWMMWWK..",
    "..KWgggWWWWWWK..",
    ".KnnnnnnnnnnnnK.",
    ".KBBBBBBBBBBBBK.",
    "..KKKKKKKKKKKK..",
    "................",
]

# =============================================================================
# Trampas
# =============================================================================

PINCHOS = [
    "................",
    "................",
    "...K....K....K..",
    "..KWK..KWK..KWK.",
    "..KGK..KGK..KGK.",
    "..KgK..KgK..KgK.",
    ".kkkkkkkkkkkkkk.",
    "................",
    ".....K....K.....",
    "....KWK..KWK....",
    "....KGK..KGK....",
    "....KgK..KgK....",
    "...kkkkkkkkkk...",
    "................",
    "................",
    "................",
]

DARDOS = [
    "................",
    "................",
    "................",
    "..KGGGGGGKRR....",
    "................",
    "......KGGGGGGKRR",
    "................",
    "...KGGGGGGKRR...",
    "................",
    "..KKKKKKKKKKKK..",
    "..KgggggggggGK..",
    "..KgkkkkkkkgGK..",
    "..KgggggggggGK..",
    "..KKKKKKKKKKKK..",
    "................",
    "................",
]

# =============================================================================
# Íconos (8 x 8)
# =============================================================================

ICONO_CORAZON = [
    ".KK.KK..",
    "KRRKRRK.",
    "KRWRRRK.",
    "KRRRRRK.",
    ".KRRRK..",
    "..KRK...",
    "...K....",
    "........",
]

ICONO_ATAQUE = [
    "......KK",
    ".....KWK",
    "....KWK.",
    "KK.KWK..",
    "KOKWK...",
    ".KOK....",
    "KbKOK...",
    "KK..K...",
]

ICONO_DEFENSA = [
    "KKKKKKK.",
    "KUUOUUK.",
    "KUUOUUK.",
    "KOOOOOK.",
    "KUUOUUK.",
    ".KUOUK..",
    "..KUK...",
    "...K....",
]

ICONO_VELOCIDAD = [
    "....KKK.",
    "...KyyK.",
    "..KyyK..",
    ".KyyyyK.",
    "..KKyK..",
    "...KyK..",
    "...KK...",
    "..K.....",
]

ICONO_VENENO = [
    "...K....",
    "..KVK...",
    "..KVK...",
    ".KVlVK..",
    "KVlVVVK.",
    "KVVVVVK.",
    ".KVVVK..",
    "..KKK...",
]

ICONO_LLAMA = [
    "...f....",
    "..ff....",
    "..fyf...",
    ".fyyf...",
    ".fyWyf..",
    ".fyyyf..",
    "..fff...",
    "........",
]

ICONO_CALAVERA = [
    ".KKKKK..",
    "KWWWWWK.",
    "KWKWKWK.",
    "KWWKWWK.",
    ".KWWWK..",
    ".KWKWK..",
    "..KKK...",
    "........",
]

ICONO_CANDADO = [
    "..KKK...",
    ".K...K..",
    ".K...K..",
    "KOOOOOK.",
    "KOOKOOK.",
    "KOOKOOK.",
    "KOOOOOK.",
    ".KKKKK..",
]

ICONO_FLECHA = [
    "KKKKKKK.",
    "KyyyyyK.",
    ".KyyyK..",
    "..KyK...",
    "...K....",
    "........",
    "........",
    "........",
]

ICONO_PERGAMINO = [
    ".KKKKKK.",
    "KnnnnnnK",
    ".KWWWWK.",
    ".KWggWK.",
    ".KWWMWK.",
    ".KWgWWK.",
    "KnnnnnnK",
    ".KKKKKK.",
]

# Todos los sprites por nombre (la ventana los convierte a imágenes al abrir).
SPRITES: tuple[tuple[str, list[str]], ...] = (
    ("suelo", SUELO),
    ("suelo_grieta", SUELO_GRIETA),
    ("pared", PARED),
    ("pared_borde", PARED_BORDE),
    ("puerta_cerrada", PUERTA_CERRADA),
    ("puerta_salida", PUERTA_SALIDA),
    ("puerta_abierta", PUERTA_ABIERTA),
    ("paso", PASO),
    ("antorcha_pared_1", ANTORCHA_PARED_1),
    ("antorcha_pared_2", ANTORCHA_PARED_2),
    ("jugador", JUGADOR),
    ("rata", RATA),
    ("esqueleto", ESQUELETO),
    ("arana", ARANA),
    ("murcielago", MURCIELAGO),
    ("lobo", LOBO),
    ("golem", GOLEM),
    ("limo", LIMO),
    ("espada", ESPADA),
    ("daga", DAGA),
    ("coraza", CORAZA),
    ("escudo", ESCUDO),
    ("pocion", POCION),
    ("pocion_veloz", POCION_VELOZ),
    ("antidoto", ANTIDOTO),
    ("llave", LLAVE),
    ("llave_bronce", LLAVE_BRONCE),
    ("llave_negra", LLAVE_NEGRA),
    ("llave_azul", LLAVE_AZUL),
    ("antorcha", ANTORCHA),
    ("pergamino", PERGAMINO),
    ("pinchos", PINCHOS),
    ("dardos", DARDOS),
)

ICONOS: tuple[tuple[str, list[str]], ...] = (
    ("corazon", ICONO_CORAZON),
    ("ataque", ICONO_ATAQUE),
    ("defensa", ICONO_DEFENSA),
    ("velocidad", ICONO_VELOCIDAD),
    ("veneno", ICONO_VENENO),
    ("llama", ICONO_LLAMA),
    ("calavera", ICONO_CALAVERA),
    ("candado", ICONO_CANDADO),
    ("flecha", ICONO_FLECHA),
    ("pergamino", ICONO_PERGAMINO),
)

# =============================================================================
# Qué sprite le toca a cada cosa
# =============================================================================

# (palabra clave, sprite). Se prueban en orden; gana la primera que aparece en
# el id o en el nombre de la ficha (en minúsculas y sin tildes).
_ENEMIGOS: tuple[tuple[str, str], ...] = (
    ("rata", "rata"),
    ("esquelet", "esqueleto"),
    ("oseo", "esqueleto"),
    ("guardian", "esqueleto"),
    ("arana", "arana"),
    ("murcielago", "murcielago"),
    ("lobo", "lobo"),
    ("golem", "golem"),
)
_ARMAS: tuple[tuple[str, str], ...] = (("daga", "daga"), ("cuchillo", "daga"))
_ARMADURAS: tuple[tuple[str, str], ...] = (("escudo", "escudo"),)
_LLAVES: tuple[tuple[str, str], ...] = (
    ("negra", "llave_negra"), ("bronce", "llave_bronce"), ("azul", "llave_azul"),
)
_TRAMPAS: tuple[tuple[str, str], ...] = (("dardo", "dardos"), ("flecha", "dardos"))
# Sprite genérico por clase de objeto (campo ``clase`` de la ficha).
_POR_CLASE: tuple[tuple[str, str], ...] = (
    ("arma", "espada"),
    ("armadura", "coraza"),
    ("pocion", "pocion"),
    ("antidoto", "antidoto"),
    ("llave", "llave"),
    ("antorcha", "antorcha"),
    ("pergamino_retroceso", "pergamino"),
)


def _normalizar(texto: str) -> str:
    """Minúsculas y sin tildes, para comparar palabras clave."""
    texto = texto.lower()
    for con_tilde, sin_tilde in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")):
        texto = texto.replace(con_tilde, sin_tilde)
    return texto


def _buscar(reglas: tuple[tuple[str, str], ...], texto: str) -> str | None:
    for palabra, sprite in reglas:
        if palabra in texto:
            return sprite
    return None


def sprite_enemigo(tipo_id: str, nombre: str) -> str:
    """Nombre del sprite para un tipo de enemigo ("limo" si no se reconoce)."""
    encontrado = _buscar(_ENEMIGOS, _normalizar(f"{tipo_id} {nombre}"))
    return encontrado if encontrado is not None else "limo"


def sprite_objeto(clase: str, tipo_id: str, nombre: str, cambia_velocidad: bool = False) -> str:
    """Nombre del sprite para un objeto según su clase y sus palabras clave."""
    texto = _normalizar(f"{tipo_id} {nombre}")
    especifico: str | None = None
    if clase == "arma":
        especifico = _buscar(_ARMAS, texto)
    elif clase == "armadura":
        especifico = _buscar(_ARMADURAS, texto)
    elif clase == "llave":
        especifico = _buscar(_LLAVES, texto)
    elif clase == "pocion" and cambia_velocidad:
        especifico = "pocion_veloz"
    if especifico is not None:
        return especifico
    for clase_conocida, sprite in _POR_CLASE:  # comparación exacta: "arma" no es "armadura"
        if clase_conocida == clase:
            return sprite
    return "pocion"


def sprite_trampa(tipo_id: str, nombre: str) -> str:
    """Nombre del sprite para una trampa ("pinchos" si no se reconoce)."""
    encontrado = _buscar(_TRAMPAS, _normalizar(f"{tipo_id} {nombre}"))
    return encontrado if encontrado is not None else "pinchos"
