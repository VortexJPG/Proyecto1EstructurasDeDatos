"""Representación neutra del estado para guardar / cargar.  [CONTRATO A↔B]

- Persona A: ``Juego.exportar_estado()`` llena estos registros y
  ``Juego.desde_estado()`` reconstruye la partida a partir de ellos.
- Persona B: los codifica en el formato binario propio y en JSON (para la
  comparación de tamaño y tiempo que pide §4.10).

El estado está partido por sala a propósito: así el archivo binario puede
llevar un índice sala → desplazamiento y cargar UNA sala sin leer todo el
archivo (§4.10).

Decisiones a documentar:
- El historial de retroceso NO se guarda: al cargar arranca vacío (Persona A).
- Las salas cuyo contenido nunca se cargó se guardan con
  ``contenido_cargado = False`` y se piden de nuevo al servicio / disco.
  Si una sala tiene ``contenido_cargado = True``, el controlador NO debe
  volver a incorporar su contenido (``Mapa.incorporar_contenido`` lo ignora).
- Los enemigos muertos no se guardan (ya no están en ninguna sala).
- ``RegistroEvento.objetivo``: "jugador", id de enemigo, id de trampa, id de
  puerta o, para efectos, "<tipo>:<portador>" (p. ej. "veneno:jugador").
- ``estado_azar`` es lo que devuelve ``random.Random.getstate()``:
  (versión, tupla de 625 enteros, gauss_next). Al decodificarlo, la parte
  interna debe volver a ser ``tuple`` (``desde_estado`` también acepta listas).
- Antes de ``Juego.desde_estado`` deben estar resueltas las fichas de todos
  los tipos que aparecen en el estado (objetos, trampas, enemigos).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class RegistroObjeto:
    instancia: str
    tipo: str


@dataclass(slots=True)
class RegistroEnemigo:
    instancia: str
    tipo: str
    numero: int  # el "#2" de "Rata gigante #2"
    vida: int
    activo: bool
    tiempo_siguiente: int | None


@dataclass(slots=True)
class RegistroTrampa:
    instancia: str
    tipo: str
    armada: bool


@dataclass(slots=True)
class RegistroPuerta:
    direccion: str  # salida de la sala dueña del registro
    cerrada: bool


@dataclass(slots=True)
class RegistroSala:
    id: int
    rastro: int | None
    contenido_cargado: bool
    visitada: bool
    objetos_suelo: list[RegistroObjeto] = field(default_factory=list)
    trampas: list[RegistroTrampa] = field(default_factory=list)
    enemigos: list[RegistroEnemigo] = field(default_factory=list)  # dormidos y activos
    puertas: list[RegistroPuerta] = field(default_factory=list)


@dataclass(slots=True)
class RegistroEfecto:
    tipo: str  # "veneno" | "velocidad" | "antorcha" | "regeneracion"
    portador: str  # "jugador" o id de instancia del enemigo
    inicio: int
    fin: int | None
    magnitud: int


@dataclass(slots=True)
class RegistroEvento:
    tiempo: int
    secuencia: int
    tipo: str  # nombre de TipoEvento
    objetivo: str  # id del actor / trampa / puerta / efecto al que aplica


@dataclass(slots=True)
class RegistroJugador:
    nombre: str
    sala: int
    vida: int
    vida_max: int
    ataque: int
    defensa: int
    velocidad: int
    tiempo_siguiente: int | None
    inventario: list[RegistroObjeto] = field(default_factory=list)  # en el ORDEN REAL
    arma_equipada: str | None = None  # id de instancia
    armadura_equipada: str | None = None
    acciones_ejecutadas: int = 0
    enemigos_derrotados: int = 0
    abrio_puerta_salida: bool = False


@dataclass(slots=True)
class EstadoGuardable:
    """Todo lo necesario para continuar una partida exactamente igual."""

    cripta_id: str
    version_cripta: str
    version_catalogo: str
    semilla: int
    estado_azar: tuple  # random.Random.getstate()
    reloj: int
    siguiente_secuencia: int
    jugador: RegistroJugador
    salas: list[RegistroSala] = field(default_factory=list)
    efectos: list[RegistroEfecto] = field(default_factory=list)
    eventos: list[RegistroEvento] = field(default_factory=list)
    # Contador de ids de objetos soltados por enemigos (``Juego.objetos_generados``).
    # No se revierte con el retroceso; guardarlo hace que una partida cargada
    # genere los mismos ids que la partida original (lo necesita el replay).
    objetos_generados: int = 0
