"""Mapa de la cripta: salas, salidas, puertas y rastro.              [Persona A]

Se construye con el esqueleto completo (§3.2) y se completa sala por sala a
medida que llega el contenido (``incorporar_contenido``).

Decisión: PUERTA COMPARTIDA. El API declara salidas DIRIGIDAS y a veces solo
un lado trae ``cerrada`` / ``llave`` (cripta-01: 2 →E→ 5 cerrada, 5 →O→ 2 sin
datos). Una salida "conecta exactamente dos salas" (§2.1), así que las dos
salidas dirigidas de un mismo pasaje comparten UN objeto ``Puerta``: abrirla o
cerrarla afecta a ambos lados (Apéndice B: "solo se impide atravesar de nuevo
hasta abrir"). Si un lado declara la puerta y el otro no, manda el que la
declara. La salida de regreso se busca primero en la dirección opuesta y, si
no apunta de vuelta, en cualquier otra dirección que sí lo haga.

Decisión del rastro (§4.7): la caducidad se DETECTA AL CONSULTAR. Cada sala
guarda solo el último instante en que el jugador estuvo allí, y
``rastro_vigente`` compara contra el reloj en O(1). Eliminar activamente los
rastros viejos exigiría un evento de caducidad por cada sala visitada (más
trabajo para la agenda y más cambios que revertir) sin cambiar ninguna
decisión del juego.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

from cripta.constantes import ANTIGUEDAD_MAXIMA_RASTRO, DIRECCIONES, indice_direccion
from cripta.estructuras.lista_doble import ListaDoble
from cripta.estructuras.tabla_ordenada import TablaOrdenada
from cripta.modelo.actores import Enemigo
from cripta.modelo.objetos import ClaseObjeto, InstanciaObjeto, InstanciaTrampa, id_objeto_de_sala

if TYPE_CHECKING:
    from cripta.estructuras.lista_doble import NodoDoble
    from cripta.modelo.datos import ContenidoSala, DatosCripta, DatosSala, DatosSalida
    from cripta.modelo.eventos import Evento
    from cripta.modelo.puertos import ProveedorFichas

# Dirección opuesta, indexada con indice_direccion (N↔S, E↔O).
_OPUESTA: tuple[str, ...] = ("S", "N", "O", "E")


class Puerta:
    """Estado VIVO de una puerta (el esqueleto solo trae el estado inicial)."""

    id: str
    cerrada: bool
    llave: str | None  # id de tipo de la llave que la abre
    cierre_automatico: int | None  # unidades hasta cerrarse tras abrirla
    evento_cierre: Evento | None
    cerrada_inicial: bool  # para reiniciar el mapa al cargar una partida

    def __init__(self, id: str, cerrada: bool, llave: str | None, cierre_automatico: int | None) -> None:
        self.id = id
        self.cerrada = cerrada
        self.llave = llave
        self.cierre_automatico = cierre_automatico
        self.evento_cierre = None
        self.cerrada_inicial = cerrada

    def __repr__(self) -> str:
        return f"Puerta({self.id!r}, cerrada={self.cerrada})"


class Salida:
    """Salida de una sala en una dirección."""

    direccion: str
    destino: Sala
    puerta: Puerta | None  # None = paso libre, nunca se cierra

    def __init__(self, direccion: str, destino: Sala, puerta: Puerta | None) -> None:
        self.direccion = direccion
        self.destino = destino
        self.puerta = puerta

    def es_transitable(self) -> bool:
        """True si no hay puerta o está abierta."""
        return self.puerta is None or not self.puerta.cerrada


class Sala:
    """Una sala. Los actores ocupan la sala completa (no hay cuadrícula)."""

    id: int
    nombre: str
    salidas: list[Salida | None]  # 4 posiciones, índice = indice_direccion()
    rastro: int | None  # último instante en que el jugador estuvo aquí
    contenido_cargado: bool
    visitada: bool  # el jugador ya entró (sus enemigos dormidos se activaron)
    enemigos: ListaDoble[Enemigo]  # dormidos y activos que están aquí
    objetos_suelo: ListaDoble[InstanciaObjeto]
    trampas: list[InstanciaTrampa]

    def __init__(self, id: int, nombre: str) -> None:
        self.id = id
        self.nombre = nombre
        self.salidas = [None] * len(DIRECCIONES)
        self.rastro = None
        self.contenido_cargado = False
        self.visitada = False
        self.enemigos = ListaDoble()
        self.objetos_suelo = ListaDoble()
        self.trampas = []

    def salida(self, direccion: str) -> Salida | None:
        """Salida en ``direccion`` o None (también si la dirección no es válida). O(1)."""
        try:
            return self.salidas[indice_direccion(direccion)]
        except ValueError:
            return None

    def salidas_transitables(self) -> Iterator[Salida]:
        """Salidas abiertas, SIEMPRE en el orden N, S, E, O (determinismo)."""
        for salida in self.salidas:
            if salida is not None and salida.es_transitable():
                yield salida

    def rastro_vigente(self, reloj: int) -> bool:
        """True si hay rastro con antigüedad < 400 (§2.9)."""
        return self.rastro is not None and reloj - self.rastro < ANTIGUEDAD_MAXIMA_RASTRO

    def enemigos_dormidos(self) -> list[Enemigo]:
        """Enemigos sin activar de esta sala (para activarlos al entrar el jugador)."""
        return [enemigo for enemigo in self.enemigos if not enemigo.activo]

    def buscar_objeto_suelo(self, objeto_id: str | None) -> NodoDoble[InstanciaObjeto] | None:
        """Nodo del objeto con ese id en el suelo, o None. O(objetos en el suelo).

        El suelo de una sala tiene pocos objetos; el requisito de costo
        independiente de la posición (§4.5) aplica al inventario.
        """
        if objeto_id is None:
            return None
        for nodo in self.objetos_suelo.nodos():
            if nodo.valor.id == objeto_id:
                return nodo
        return None

    def __repr__(self) -> str:
        return f"Sala({self.id}, {self.nombre!r})"


class Mapa:
    """Todas las salas, indexadas por id con una TablaOrdenada (arreglo ordenado; no dict, §7)."""

    salas: TablaOrdenada[int, Sala]
    enemigos: TablaOrdenada[str, Enemigo]  # TODAS las instancias conocidas, por id
    puertas: TablaOrdenada[str, Puerta]
    sala_inicial: Sala
    sala_salida: Sala
    llave_salida: str

    def __init__(self) -> None:
        self.salas = TablaOrdenada()
        self.enemigos = TablaOrdenada()
        self.puertas = TablaOrdenada()
        # Las salas en el orden del esqueleto. Se recorre esta lista cuando el
        # orden importa (exportar, reiniciar): es el orden en que la cripta
        # declara sus salas. La TablaOrdenada queda ordenada por id, que no
        # tiene por qué ser el mismo orden.
        self._orden: list[Sala] = []
        self.llave_salida = ""

    @staticmethod
    def construir(datos: DatosCripta, salas: list[DatosSala]) -> Mapa:
        """Crea todas las salas y salidas a partir del esqueleto completo.

        Tres pasadas: crear salas, crear salidas (el destino puede venir en otra
        página) y decidir las puertas compartidas.
        """
        mapa = Mapa()
        # Salidas declaradas por sala (4 posiciones) para la tercera pasada.
        declaradas: TablaOrdenada[int, list[DatosSalida | None]] = TablaOrdenada()

        # 1) Salas.
        for datos_sala in salas:
            if mapa.salas.contiene(datos_sala.id):
                raise ValueError(f"El esqueleto trae dos veces la sala {datos_sala.id}")
            sala = Sala(datos_sala.id, datos_sala.nombre)
            mapa.salas.insertar(sala.id, sala)
            mapa._orden.append(sala)
            por_direccion: list[DatosSalida | None] = [None] * len(DIRECCIONES)
            for datos_salida in datos_sala.salidas:
                por_direccion[indice_direccion(datos_salida.direccion)] = datos_salida
            declaradas.insertar(sala.id, por_direccion)

        # 2) Salidas (sin puertas todavía).
        for sala in mapa._orden:
            por_direccion = declaradas.obtener(sala.id)
            for i in range(len(DIRECCIONES)):
                datos_salida = por_direccion[i]
                if datos_salida is None:
                    continue
                destino = mapa.salas.obtener(datos_salida.sala_destino)
                if destino is None:
                    raise ValueError(
                        f"La salida {datos_salida.direccion} de la sala {sala.id} lleva a la sala "
                        f"{datos_salida.sala_destino}, que no existe en el esqueleto"
                    )
                sala.salidas[i] = Salida(datos_salida.direccion, destino, None)

        # 3) Puertas compartidas entre los dos sentidos de cada pasaje.
        for sala in mapa._orden:
            for i in range(len(DIRECCIONES)):
                salida = sala.salidas[i]
                if salida is None or salida.puerta is not None:
                    continue
                ida = declaradas.obtener(sala.id)[i]
                j = Mapa._indice_regreso(salida.destino, sala, i)
                vuelta = declaradas.obtener(salida.destino.id)[j] if j >= 0 else None
                if not (_declara_puerta(ida) or _declara_puerta(vuelta)):
                    continue  # paso libre en ambos sentidos
                puerta = Puerta(
                    f"p-{sala.id}{salida.direccion}-{salida.destino.id}",
                    cerrada=_campo(ida, "cerrada") or _campo(vuelta, "cerrada") or False,
                    llave=_primero_no_nulo(_campo(ida, "llave"), _campo(vuelta, "llave")),
                    cierre_automatico=_primero_no_nulo(
                        _campo(ida, "cierre_automatico"), _campo(vuelta, "cierre_automatico")
                    ),
                )
                salida.puerta = puerta
                if j >= 0:
                    salida.destino.salidas[j].puerta = puerta
                mapa.puertas.insertar(puerta.id, puerta)

        mapa.sala_inicial = mapa._sala_declarada(datos.sala_inicial, "sala_inicial")
        mapa.sala_salida = mapa._sala_declarada(datos.sala_salida, "sala_salida")
        mapa.llave_salida = datos.llave_salida
        return mapa

    def sala(self, sala_id: int) -> Sala:
        """Sala por id en O(1) promedio. KeyError con contexto si no existe."""
        sala = self.salas.obtener(sala_id)
        if sala is None:
            raise KeyError(f"La sala {sala_id} no existe en esta cripta")
        return sala

    def vecinos(self, sala_id: int) -> list[int]:
        """Ids de salas vecinas por cualquier salida (abierta o cerrada).

        La usa la precarga de Persona B para el BFS. Solo depende del
        esqueleto, nunca del estado de juego. Orden N, S, E, O.
        """
        return [salida.destino.id for salida in self.sala(sala_id).salidas if salida is not None]

    def incorporar_contenido(self, contenido: ContenidoSala, fichas: ProveedorFichas) -> None:
        """Agrega enemigos (dormidos), objetos y trampas de una sala.

        Reglas:
        - No activa enemigos (§2.4) ni consume el azar ni números de secuencia:
          así el momento en que llega la respuesta HTTP no altera la partida.
        - Si la sala ya tiene enemigos activos que llegaron antes que su
          contenido, se conservan (los nuevos se agregan al final).
        - Es idempotente: si la sala ya tenía contenido, no hace nada (evita
          duplicar instancias si la misma sala llega dos veces o después de
          cargar una partida).
        - Ids de instancia de objetos: ``objetos.id_objeto_de_sala``.
        - Las fichas de todos los tipos ya deben estar resueltas en ``fichas``.
        """
        sala = self.sala(contenido.sala)
        if sala.contenido_cargado:
            return
        for colocacion in contenido.enemigos:
            if self.enemigos.contiene(colocacion.instancia):
                continue  # instancia ya conocida (defensivo)
            enemigo = Enemigo(colocacion.instancia, fichas.obtener(colocacion.tipo), colocacion.vida, 0, sala)
            enemigo.nodo_en_sala = sala.enemigos.agregar_al_final(enemigo)
            self.enemigos.insertar(enemigo.id, enemigo)
        for posicion in range(len(contenido.objetos)):
            tipo_id = contenido.objetos[posicion]
            clase = ClaseObjeto.desde_texto(fichas.obtener(tipo_id).clase)
            sala.objetos_suelo.agregar_al_final(InstanciaObjeto(id_objeto_de_sala(sala.id, posicion), tipo_id, clase))
        for colocacion in contenido.trampas:
            sala.trampas.append(InstanciaTrampa(colocacion.instancia, fichas.obtener(colocacion.tipo)))
        sala.contenido_cargado = True

    def reiniciar_contenido(self) -> None:
        """Deja el mapa como recién construido (sin contenido ni estado de juego).

        Lo usa ``Juego.desde_estado`` antes de volcar una partida guardada.
        """
        self.enemigos = TablaOrdenada()
        for sala in self._orden:
            sala.rastro = None
            sala.contenido_cargado = False
            sala.visitada = False
            sala.enemigos = ListaDoble()
            sala.objetos_suelo = ListaDoble()
            sala.trampas = []
            for salida in sala.salidas:
                if salida is not None and salida.puerta is not None:
                    salida.puerta.cerrada = salida.puerta.cerrada_inicial
                    salida.puerta.evento_cierre = None

    def __iter__(self) -> Iterator[Sala]:
        """Salas en el orden del esqueleto (determinista)."""
        return iter(self._orden)

    def __len__(self) -> int:
        return len(self._orden)

    # --- internos -----------------------------------------------------------------

    def _sala_declarada(self, sala_id: int, campo: str) -> Sala:
        sala = self.salas.obtener(sala_id)
        if sala is None:
            raise ValueError(f"Los datos de la cripta declaran {campo}={sala_id}, pero esa sala no está en el esqueleto")
        return sala

    @staticmethod
    def _indice_regreso(destino: Sala, origen: Sala, indice_ida: int) -> int:
        """Posición de la salida de ``destino`` que regresa a ``origen`` (o -1).

        Prefiere la dirección opuesta; si no apunta de vuelta, busca cualquier
        otra salida hacia ``origen`` que aún no tenga puerta.
        """
        opuesta = indice_direccion(_OPUESTA[indice_ida])
        candidata = destino.salidas[opuesta]
        if candidata is not None and candidata.destino is origen and candidata.puerta is None:
            if not (destino is origen and opuesta == indice_ida):
                return opuesta
        for j in range(len(DIRECCIONES)):
            if destino is origen and j == indice_ida:
                continue  # es la misma salida (sala que se conecta consigo misma)
            candidata = destino.salidas[j]
            if candidata is not None and candidata.destino is origen and candidata.puerta is None:
                return j
        return -1


def _declara_puerta(datos_salida: DatosSalida | None) -> bool:
    """True si la salida declarada trae algún dato de puerta."""
    if datos_salida is None:
        return False
    return bool(datos_salida.cerrada) or datos_salida.llave is not None or datos_salida.cierre_automatico is not None


def _campo(datos_salida: DatosSalida | None, nombre: str) -> object:
    return getattr(datos_salida, nombre) if datos_salida is not None else None


def _primero_no_nulo(a: object, b: object) -> object:
    return a if a is not None else b
