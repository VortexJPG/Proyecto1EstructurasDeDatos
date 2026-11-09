"""Interfaz gráfica con sprites pixel art (pygame-ce).                  [Persona A]

Es OTRA vista para el mismo modelo y el mismo controlador (MVC): el modelo no
cambia en nada y el controlador la usa igual que a la consola, con los mismos
métodos (``pedir_comando``, ``mostrar_estado``...). Se abre con ``--gui``.

Cómo funciona:
- ``pedir_comando`` tiene su propio ciclo: lee el teclado, dibuja la pantalla
  unas 30 veces por segundo (para las animaciones) y devuelve un comando en
  cuanto se presiona una tecla que tenga sentido. Mientras tanto el reloj
  virtual del juego NO avanza: el juego sigue esperando la decisión del
  jugador, igual que en la consola (§2.3).
- Lo que se pregunta (a quién atacar, qué recoger...) usa la misma lógica que
  la consola (``vista/base.py``), pero con un menú en la ventana que además
  señala en la sala a qué cosa se refiere cada opción.
- Las salas no tienen cuadrícula (§2.1): dónde se dibuja cada cosa dentro de
  la sala es solo decorativo (sale de su lugar en la lista de la sala).
- Las animaciones (números de daño, destellos, la calavera de un enemigo
  derrotado) salen de comparar la vida de cada actor antes y después de la
  acción. Son solo presentación: no tocan el modelo ni el reloj.

Las fichas del catálogo se consultan UNA vez por tipo y se guardan aquí
(``_tipos``): la pantalla se redibuja muchas veces por segundo y consultar la
caché en cada cuadro inflaría sus estadísticas y movería el orden de la LRU
(§4.4).

Los sprites están en ``vista/sprites.py`` como texto y se convierten a
imágenes una sola vez, al abrir la ventana.
"""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")  # sin el saludo de pygame en la terminal

import pygame

from cripta.controlador.comandos import ComandoUsuario, TipoComando
from cripta.estructuras.cola import ColaEnlazada
from cripta.estructuras.tabla_ordenada import TablaOrdenada
from cripta.modelo.acciones import TipoAccion
from cripta.modelo.actores import Jugador
from cripta.modelo.juego import EstadoPartida
from cripta.modelo.puertos import FichaNoDisponible
from cripta.vista import sprites
from cripta.vista.base import (
    LINEA_ENEMIGOS,
    LINEA_MENSAJE,
    LINEA_SIN_NOVEDADES,
    LINEA_TU_TURNO,
    VistaBase,
    detalles_ficha,
    lineas_bitacora,
    nombre_direccion,
    tecla_de,
)
from cripta.vista.vista_consola import VistaConsola

if TYPE_CHECKING:
    from cripta.adaptadores.puntajes import RegistroPuntaje
    from cripta.modelo.acciones import ResultadoAccion
    from cripta.modelo.actores import Enemigo
    from cripta.modelo.datos import ResumenCripta
    from cripta.modelo.juego import Juego, ResumenPartida
    from cripta.modelo.mapa import Salida
    from cripta.modelo.objetos import InstanciaObjeto

# --- Medidas (en pixeles de la ventana) ------------------------------------------
ANCHO, ALTO = 1024, 640
FPS = 30
ESCALA = 3  # cada pixel del sprite se dibuja de 3 x 3
LADO = sprites.TAMANO * ESCALA  # una casilla de la sala: 48 px
COLUMNAS, FILAS = 11, 9  # la sala dibujada, contando las paredes
SALA_X, SALA_Y = 12, 40
SALA_ANCHO, SALA_ALTO = COLUMNAS * LADO, FILAS * LADO
PANEL_X = SALA_X + SALA_ANCHO + 12
PANEL_ANCHO = ANCHO - PANEL_X - 12
ABAJO_Y = SALA_Y + SALA_ALTO + 8
ABAJO_ALTO = ALTO - ABAJO_Y - 8
FILAS_INVENTARIO = 10

# --- Colores ------------------------------------------------------------------------
FONDO = (16, 13, 22)
CAJA = (30, 25, 38)
BORDE = (74, 62, 90)
TEXTO = (232, 228, 220)
TENUE = (146, 138, 158)
DORADO = (236, 196, 90)
ROJO = (232, 86, 74)
ROJO_CLARO = (240, 186, 176)
VERDE = (112, 204, 112)
AZUL = (122, 170, 240)
MORADO = (176, 116, 220)
NEGRO = (0, 0, 0)

# --- Dónde se dibuja cada cosa dentro de la sala: (columna, fila) -------------------
POS_JUGADOR = (5, 4)
POS_ENEMIGOS = ((5, 2), (3, 2), (7, 2), (2, 3), (8, 3), (4, 1), (6, 1), (2, 1), (8, 1))
POS_OBJETOS = ((4, 6), (6, 6), (3, 6), (7, 6), (4, 7), (6, 7), (2, 7), (8, 7), (3, 7), (7, 7))
POS_TRAMPAS = ((2, 5), (8, 5), (1, 6), (9, 6))
POS_PUERTAS = (("N", (5, 0)), ("S", (5, 8)), ("E", (10, 4)), ("O", (0, 4)))
POS_ANTORCHAS = ((2, 0), (8, 0))

TECLAS_MOVER = ((pygame.K_w, "N"), (pygame.K_a, "O"), (pygame.K_s, "S"), (pygame.K_d, "E"))
TECLAS_NUMERO = (
    (pygame.K_1, pygame.K_KP1), (pygame.K_2, pygame.K_KP2), (pygame.K_3, pygame.K_KP3),
    (pygame.K_4, pygame.K_KP4), (pygame.K_5, pygame.K_KP5), (pygame.K_6, pygame.K_KP6),
    (pygame.K_7, pygame.K_KP7), (pygame.K_8, pygame.K_KP8), (pygame.K_9, pygame.K_KP9),
)
TECLAS_ACEPTAR = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
TECLAS_CANCELAR = (pygame.K_ESCAPE, pygame.K_0, pygame.K_KP0, pygame.K_BACKSPACE)

# Orden del inventario que va mostrando la tecla I (None = orden real).
ORDENES: tuple[str | None, ...] = (None, "peso", "valor", "nombre")

AYUDA: tuple[tuple[str, str], ...] = (
    ("W A S D", "moverse al norte, oeste, sur y este"),
    ("Q", "atacar (si hay varios enemigos, te pregunta)"),
    ("E", "recoger un objeto del suelo"),
    ("R", "abrir una puerta con llave"),
    ("F", "usar, equipar o soltar el objeto del cursor"),
    ("T", "esperar"),
    ("Arriba / Abajo", "mover el cursor del inventario"),
    ("I", "ordenar el inventario (peso, valor, nombre)"),
    ("Z", "usar un pergamino de retroceso"),
    ("F5 / F9", "guardar / cargar la partida"),
    ("P", "tabla de puntajes"),
    ("L", "ver la bitácora completa (los últimos 20 mensajes)"),
    ("F1", "ver esta ayuda"),
    ("Esc", "salir"),
)

_FUENTES = "consolas,dejavusansmono,liberationmono,menlo,couriernew"


def _fuente(tamano: int, negrita: bool = False) -> pygame.font.Font:
    """Fuente monoespaciada si existe en el sistema (si no, la de pygame)."""
    return pygame.font.SysFont(_FUENTES, tamano, bold=negrita)


def _superficie(filas: list[str], escala: int) -> pygame.Surface:
    """Convierte un sprite de texto en imagen y lo agranda sin suavizar."""
    ancho, alto = len(filas[0]), len(filas)
    imagen = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    for y in range(alto):
        fila = filas[y]
        for x in range(ancho):
            color = sprites.color_de(fila[x])
            if color is not None:
                imagen.set_at((x, y), color)
    return pygame.transform.scale(imagen, (ancho * escala, alto * escala))


def _casilla(columna: int, fila: int) -> tuple[int, int]:
    """Esquina superior izquierda de una casilla de la sala, en pixeles."""
    return SALA_X + columna * LADO, SALA_Y + fila * LADO


def _numero_de_tecla(tecla: int) -> int | None:
    """K_1 / K_KP1 → 1 ... (None si no es un número del 1 al 9)."""
    for i in range(len(TECLAS_NUMERO)):
        if tecla in TECLAS_NUMERO[i]:
            return i + 1
    return None


@dataclass(slots=True)
class _Menu:
    titulo: str
    opciones: list[str]
    marcas: list[str] | None
    seleccion: int = 0
    zonas: list[pygame.Rect] = field(default_factory=list)  # dónde quedó cada opción (para el mouse)


@dataclass(slots=True)
class _Aviso:
    texto: str
    error: bool
    hasta: int  # milisegundos


@dataclass(slots=True)
class _Flotante:
    """Número de daño o curación que sube y se desvanece sobre un actor."""

    texto: str
    color: tuple[int, int, int]
    x: int
    y: int
    inicio: int


@dataclass(slots=True)
class _InfoTipo:
    """Lo que la ventana necesita de una ficha (se consulta una vez por tipo)."""

    nombre: str
    sprite: str
    detalles: str
    provisional: bool = False  # la ficha no estaba disponible: se reintenta después


class VentanaCerrada(EOFError):
    """El usuario cerró la ventana cuando el juego le estaba preguntando algo."""


class VistaGrafica(VistaBase):
    """Ventana con la sala dibujada, los paneles del jugador y la bitácora."""

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("CRIPTA")
        try:
            # SCALED: la ventana se puede agrandar o maximizar y todo se escala parejo.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")  # sin aceleración de video avisa, pero funciona igual
                self._pantalla = pygame.display.set_mode((ANCHO, ALTO), pygame.SCALED | pygame.RESIZABLE)
        except pygame.error:
            self._pantalla = pygame.display.set_mode((ANCHO, ALTO))
        pygame.display.set_icon(_superficie(sprites.JUGADOR, 2))
        self._sprites = self._cargar(sprites.SPRITES, ESCALA)
        self._sprites_chicos = self._cargar(sprites.SPRITES, 1)
        self._iconos = self._cargar(sprites.ICONOS, 2)
        self._iconos_grandes = self._cargar(sprites.ICONOS, ESCALA)
        self._destellados: TablaOrdenada[str, pygame.Surface] = TablaOrdenada()
        self._apagados: TablaOrdenada[str, pygame.Surface] = TablaOrdenada()
        self._sombra = pygame.Surface((36, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(self._sombra, (0, 0, 0, 90), self._sombra.get_rect())
        self._fuente = _fuente(14)
        self._fuente_chica = _fuente(12)
        self._fuente_negrita = _fuente(14, True)
        self._fuente_titulo = _fuente(20, True)
        self._fuente_grande = _fuente(52, True)
        self._reloj = pygame.time.Clock()
        self._pendientes: ColaEnlazada[pygame.event.Event] = ColaEnlazada()

        self._juego: Juego | None = None
        self._tipos: TablaOrdenada[str, _InfoTipo] = TablaOrdenada()
        self._provisionales: list[str] = []
        self._menu: _Menu | None = None
        self._capa: str | None = None  # "ayuda" | "puntajes" | "bitacora": se cierra con cualquier tecla
        self._puntajes: list[RegistroPuntaje] = []
        self._fin: tuple[ResumenPartida, str] | None = None
        self._avisos: list[_Aviso] = []
        self._flotantes: list[_Flotante] = []
        self._muertes: list[tuple[int, int, int]] = []  # (x, y, inicio) de enemigos derrotados
        self._destellos: TablaOrdenada[str, int] = TablaOrdenada()  # id de actor → hasta cuándo destella
        self._marcables: list[tuple[str, int, int]] = []  # (id o dirección, x, y) del último cuadro
        self._vidas: TablaOrdenada[str, int] = TablaOrdenada()  # vida de cada actor en el estado anterior
        self._enemigos_previos: list[tuple[str, int, int]] = []
        self._sala_previa: int | None = None
        self._criterio: str | None = None
        self._vista_ordenada: list[InstanciaObjeto] | None = None
        self._ultimo_comando: ComandoUsuario | None = None
        self._transicion_hasta = 0
        self._retroceso_hasta = 0
        self._cerrada = False
        self._ayuda_mostrada = False
        self.espera_fin_ms = 700  # en la pantalla final, ignora teclas un momento (por si venían apretadas)

    # =========================================================================
    # Lo que usa el controlador
    # =========================================================================

    def elegir_cripta(self, criptas: list[ResumenCripta]) -> str:
        """Pantalla de inicio con la lista de criptas (flechas + Enter, número o clic)."""
        if not criptas:
            raise ValueError("El servicio no tiene criptas publicadas")
        if len(criptas) == 1:
            self._pantalla_espera(f"Preparando {criptas[0].nombre}...")
            return criptas[0].id
        seleccion = 0
        zonas: list[pygame.Rect] = []
        while True:
            evento = self._siguiente_evento()
            if evento is None:
                self._dibujar_portada("Elige una cripta")
                zonas = self._dibujar_lista_criptas(criptas, seleccion)
                self._dibujar_avisos(pygame.time.get_ticks())
                self._presentar()
                continue
            elegida: int | None = None
            if evento.type == pygame.QUIT:
                self._cerrar_ventana()
            elif evento.type == pygame.KEYDOWN:
                if evento.key in (pygame.K_UP, pygame.K_w):
                    seleccion = (seleccion - 1) % len(criptas)
                elif evento.key in (pygame.K_DOWN, pygame.K_s):
                    seleccion = (seleccion + 1) % len(criptas)
                elif evento.key in TECLAS_ACEPTAR:
                    elegida = seleccion
                elif evento.key == pygame.K_ESCAPE:
                    self._cerrar_ventana()
                else:
                    numero = _numero_de_tecla(evento.key)
                    if numero is not None and numero <= len(criptas):
                        elegida = numero - 1
            elif evento.type == pygame.MOUSEMOTION:
                seleccion = self._zona_en(zonas, evento.pos, seleccion)
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if self._zona_en(zonas, evento.pos, -1) >= 0:
                    elegida = self._zona_en(zonas, evento.pos, -1)
            if elegida is not None:
                self._pantalla_espera(f"Preparando {criptas[elegida].nombre}...")
                return criptas[elegida].id

    def pedir_nombre(self) -> str:
        """Pantalla para escribir el nombre (Enter acepta; vacío o Esc = "Jugador")."""
        nombre = ""
        pygame.key.start_text_input()
        try:
            while True:
                evento = self._siguiente_evento()
                if evento is None:
                    self._dibujar_portada("¿Cómo te llamas?")
                    self._dibujar_entrada_nombre(nombre)
                    self._presentar()
                    continue
                if evento.type == pygame.QUIT:
                    self._cerrar_ventana()
                elif evento.type == pygame.TEXTINPUT:
                    nombre = (nombre + evento.text)[:16]
                elif evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_BACKSPACE:
                        nombre = nombre[:-1]
                    elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        return nombre.strip() or "Jugador"
                    elif evento.key == pygame.K_ESCAPE:
                        return "Jugador"
        finally:
            pygame.key.stop_text_input()

    def pedir_comando(self, juego: Juego) -> ComandoUsuario:
        """Espera una tecla con sentido y la devuelve como comando (el reloj no avanza)."""
        self._juego = juego
        if not self._ayuda_mostrada:  # la primera vez se muestran los controles
            self._ayuda_mostrada = True
            self._capa = "ayuda"
        while True:
            if self._cerrada:
                return ComandoUsuario(TipoComando.SALIR)
            evento = self._siguiente_evento()
            if evento is None:
                self._mostrar_cuadro()
                continue
            if evento.type == pygame.QUIT:
                self._cerrada = True
                return ComandoUsuario(TipoComando.SALIR)
            if evento.type != pygame.KEYDOWN:
                continue
            if self._capa is not None:  # cualquier tecla cierra la ayuda, los puntajes o la bitácora
                self._capa = None
                continue
            if evento.key == pygame.K_l:  # solo cambia lo que se ve: no es un comando del juego
                self._capa = "bitacora"
                continue
            comando = self._comando_de_tecla(evento.key, juego)
            if comando is not None and not self._cerrada:
                self._ultimo_comando = comando
                return comando

    def mostrar_estado(self, juego: Juego) -> None:
        """Se llama después de cada acción aceptada: prepara las animaciones."""
        self._juego = juego
        ahora = pygame.time.get_ticks()
        self._reintentar_provisionales()
        sala_id = juego.jugador.sala.id
        cambio_de_sala = self._sala_previa is not None and sala_id != self._sala_previa
        comando = self._ultimo_comando
        self._ultimo_comando = None
        accion = comando.accion if comando is not None and comando.tipo is TipoComando.ACCION else None
        if accion is not None and accion.tipo is TipoAccion.RETROCEDER:
            self._retroceso_hasta = ahora + 600  # destello morado: "el tiempo vuelve atrás"
        elif accion is not None:
            self._animar_cambios(juego, cambio_de_sala, ahora)
        if cambio_de_sala:
            self._transicion_hasta = ahora + 260
        self._recordar_vidas(juego)
        self._sala_previa = sala_id
        if self._criterio is not None:
            self._vista_ordenada = juego.vista_inventario(self._criterio)

    def mostrar_inventario(
        self, juego: Juego, vista: list[InstanciaObjeto] | None = None, criterio: str | None = None
    ) -> None:
        """El inventario siempre está a la vista: solo se cambia el orden que se muestra."""
        self._juego = juego
        self._vista_ordenada = vista
        self._criterio = criterio if vista is not None else None

    def mostrar_resultado(self, resultado: ResultadoAccion) -> None:
        if not resultado.aceptada and resultado.motivo:
            self.mostrar_error(resultado.motivo)

    def mostrar_info(self, texto: str) -> None:
        print(texto)  # copia en la terminal (por ejemplo, la ruta del replay)
        self._agregar_aviso(texto, False)

    def mostrar_error(self, texto: str) -> None:
        self._agregar_aviso(texto, True)

    def mostrar_ayuda(self) -> None:
        self._capa = "ayuda"

    def mostrar_puntajes(self, registros: list[RegistroPuntaje]) -> None:
        self._puntajes = registros
        self._capa = "puntajes"

    def mostrar_fin(self, juego: Juego, reporte_red: str) -> None:
        """Pantalla de victoria o derrota; espera una tecla antes de cerrar."""
        VistaConsola().mostrar_fin(juego, reporte_red)  # queda en la terminal al cerrar la ventana
        if self._cerrada:
            return
        self._juego = juego
        self._menu = None
        self._capa = None
        self._fin = (juego.resumen(), reporte_red)
        inicio = pygame.time.get_ticks()
        while True:
            evento = self._siguiente_evento()
            if evento is None:
                self._mostrar_cuadro()
                continue
            if evento.type == pygame.QUIT:
                self._cerrada = True
                return
            esperando = pygame.time.get_ticks() - inicio < self.espera_fin_ms
            if evento.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN) and not esperando:
                return

    def cerrar(self) -> None:
        """Cierra la ventana (se puede llamar más de una vez)."""
        if pygame.get_init():
            pygame.quit()

    # =========================================================================
    # Teclado y menús
    # =========================================================================

    def _comando_de_tecla(self, tecla: int, juego: Juego) -> ComandoUsuario | None:
        """Tecla → comando. None si no hace nada (o se canceló un menú)."""
        for tecla_mover, direccion in TECLAS_MOVER:
            if tecla == tecla_mover:
                return self._accion(TipoAccion.MOVER, direccion=direccion)
        if tecla == pygame.K_q:
            return self._atacar(juego, None)
        if tecla == pygame.K_e:
            return self._recoger(juego, None)
        if tecla == pygame.K_r:
            return self._abrir(juego, None)
        if tecla == pygame.K_f:
            objeto = self._objeto_de_inventario(juego, None)
            return self._menu_objeto(juego, objeto) if objeto is not None else None
        if tecla == pygame.K_t:
            return self._accion(TipoAccion.ESPERAR)
        if tecla == pygame.K_z:
            return self._accion(TipoAccion.RETROCEDER)
        if tecla == pygame.K_i:
            siguiente = ORDENES[(ORDENES.index(self._criterio) + 1) % len(ORDENES)]
            if siguiente is None:
                return ComandoUsuario(TipoComando.VER_INVENTARIO)
            return ComandoUsuario(TipoComando.VISTA_ORDENADA, argumento=siguiente)
        if tecla == pygame.K_UP:
            return ComandoUsuario(TipoComando.INVENTARIO_ANTERIOR)
        if tecla == pygame.K_DOWN:
            return ComandoUsuario(TipoComando.INVENTARIO_SIGUIENTE)
        if tecla == pygame.K_F5:
            return ComandoUsuario(TipoComando.GUARDAR)
        if tecla == pygame.K_F9:
            return ComandoUsuario(TipoComando.CARGAR)
        if tecla == pygame.K_p:
            return ComandoUsuario(TipoComando.PUNTAJES)
        if tecla in (pygame.K_F1, pygame.K_h):
            return ComandoUsuario(TipoComando.AYUDA)
        if tecla == pygame.K_ESCAPE:
            indice = self._preguntar("¿Salir de la partida?", ["Sí, salir", "No, seguir jugando"])
            return ComandoUsuario(TipoComando.SALIR) if indice == 0 else None
        return None

    def _preguntar(self, titulo: str, opciones: list[str], marcas: list[str] | None = None) -> int | None:
        """Menú en la ventana: flechas o W/S + Enter, el número, o clic. Esc cancela."""
        if self._cerrada:
            return None
        menu = _Menu(titulo, opciones, marcas)
        self._menu = menu
        try:
            while True:
                evento = self._siguiente_evento()
                if evento is None:
                    self._mostrar_cuadro()
                    continue
                if evento.type == pygame.QUIT:
                    self._cerrada = True
                    return None
                if evento.type == pygame.KEYDOWN:
                    if evento.key in (pygame.K_UP, pygame.K_w):
                        menu.seleccion = (menu.seleccion - 1) % len(opciones)
                    elif evento.key in (pygame.K_DOWN, pygame.K_s):
                        menu.seleccion = (menu.seleccion + 1) % len(opciones)
                    elif evento.key in TECLAS_ACEPTAR:
                        return menu.seleccion
                    elif evento.key in TECLAS_CANCELAR:
                        return None
                    else:
                        numero = _numero_de_tecla(evento.key)
                        if numero is not None and numero <= len(opciones):
                            return numero - 1
                elif evento.type == pygame.MOUSEMOTION:
                    menu.seleccion = self._zona_en(menu.zonas, evento.pos, menu.seleccion)
                elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    elegida = self._zona_en(menu.zonas, evento.pos, -1)
                    if elegida >= 0:
                        return elegida
        finally:
            self._menu = None

    def _siguiente_evento(self) -> pygame.event.Event | None:
        """Próximo evento en orden de llegada (None si no hay ninguno esperando).

        Los menús también sacan de esta misma cola: si alguien aprieta "Q" y
        "2" muy rápido, el "2" le llega al menú que abrió la "Q".
        """
        if self._pendientes.esta_vacia():
            for evento in pygame.event.get():
                self._pendientes.encolar(evento)
        if self._pendientes.esta_vacia():
            return None
        return self._pendientes.desencolar()

    @staticmethod
    def _zona_en(zonas: list[pygame.Rect], posicion: tuple[int, int], defecto: int) -> int:
        for i in range(len(zonas)):
            if zonas[i].collidepoint(posicion):
                return i
        return defecto

    def _cerrar_ventana(self) -> None:
        self._cerrada = True
        raise VentanaCerrada("Se cerró la ventana")

    # =========================================================================
    # Estado para las animaciones
    # =========================================================================

    def _animar_cambios(self, juego: Juego, cambio_de_sala: bool, ahora: int) -> None:
        """Números de daño / curación, destellos y calaveras de los derrotados."""
        self._comparar_vida(Jugador.ID, juego.jugador.vida, _casilla(*POS_JUGADOR), ahora)
        if cambio_de_sala:
            return  # los enemigos de la sala nueva no tienen "antes"
        enemigos = juego.enemigos_en_sala()
        for i in range(min(len(enemigos), len(POS_ENEMIGOS))):
            self._comparar_vida(enemigos[i].id, enemigos[i].vida, _casilla(*POS_ENEMIGOS[i]), ahora)
        for enemigo_id, x, y in self._enemigos_previos:
            enemigo = juego.enemigos.obtener(enemigo_id)
            if enemigo is not None and not enemigo.esta_vivo():
                self._muertes.append((x, y, ahora))

    def _comparar_vida(self, actor_id: str, vida: int, posicion: tuple[int, int], ahora: int) -> None:
        previa = self._vidas.obtener(actor_id)
        if previa is None or previa == vida:
            return
        diferencia = vida - previa
        color = VERDE if diferencia > 0 else ROJO
        self._flotantes.append(_Flotante(f"{diferencia:+d}", color, posicion[0] + LADO // 2, posicion[1], ahora))
        if diferencia < 0:
            self._destellos.insertar(actor_id, ahora + 220)

    def _recordar_vidas(self, juego: Juego) -> None:
        self._vidas = TablaOrdenada()
        self._vidas.insertar(Jugador.ID, juego.jugador.vida)
        self._enemigos_previos = []
        enemigos = juego.enemigos_en_sala()
        for i in range(len(enemigos)):
            self._vidas.insertar(enemigos[i].id, enemigos[i].vida)
            if i < len(POS_ENEMIGOS):
                x, y = _casilla(*POS_ENEMIGOS[i])
                self._enemigos_previos.append((enemigos[i].id, x, y))

    # =========================================================================
    # Fichas (una consulta por tipo)
    # =========================================================================

    def _info(self, juego: Juego, tipo_id: str) -> _InfoTipo:
        info = self._tipos.obtener(tipo_id)
        if info is not None:
            return info
        try:
            ficha = juego.fichas.obtener(tipo_id)
        except FichaNoDisponible:
            # Todavía no llegó (p. ej. la llave de una puerta lejana): se reintenta
            # después de la próxima acción, no en cada cuadro.
            info = _InfoTipo(tipo_id, "pocion", "", provisional=True)
            self._provisionales.append(tipo_id)
        else:
            if ficha.clase == "enemigo":
                sprite = sprites.sprite_enemigo(ficha.id, ficha.nombre)
            elif ficha.clase == "trampa":
                sprite = sprites.sprite_trampa(ficha.id, ficha.nombre)
            else:
                sprite = sprites.sprite_objeto(ficha.clase, ficha.id, ficha.nombre, bool(ficha.modificador_velocidad))
            info = _InfoTipo(ficha.nombre, sprite, detalles_ficha(ficha))
        self._tipos.insertar(tipo_id, info)
        return info

    def _reintentar_provisionales(self) -> None:
        for tipo_id in self._provisionales:
            self._tipos.eliminar(tipo_id)
        self._provisionales = []

    def _sprite_de_enemigo(self, enemigo: Enemigo) -> str:
        """El enemigo ya copió nombre y tipo de su ficha: no hace falta la caché."""
        clave = "enemigo:" + enemigo.tipo_id
        info = self._tipos.obtener(clave)
        if info is None:
            info = _InfoTipo(enemigo.nombre_tipo, sprites.sprite_enemigo(enemigo.tipo_id, enemigo.nombre_tipo), "")
            self._tipos.insertar(clave, info)
        return info.sprite

    # =========================================================================
    # Dibujo: utilidades
    # =========================================================================

    def _cargar(self, lista: tuple[tuple[str, list[str]], ...], escala: int) -> TablaOrdenada[str, pygame.Surface]:
        tabla: TablaOrdenada[str, pygame.Surface] = TablaOrdenada()
        for nombre, filas in lista:
            tabla.insertar(nombre, _superficie(filas, escala).convert_alpha())
        return tabla

    def _sprite(self, nombre: str) -> pygame.Surface:
        imagen = self._sprites.obtener(nombre)
        return imagen if imagen is not None else self._sprites.obtener("limo")

    def _icono(self, nombre: str, grande: bool = False) -> pygame.Surface:
        return (self._iconos_grandes if grande else self._iconos).obtener(nombre)

    def _destellado(self, nombre: str) -> pygame.Surface:
        """El sprite teñido de rojo (cuando recibe daño)."""
        imagen = self._destellados.obtener(nombre)
        if imagen is None:
            imagen = self._sprite(nombre).copy()
            imagen.fill((150, 30, 30), special_flags=pygame.BLEND_RGB_ADD)
            self._destellados.insertar(nombre, imagen)
        return imagen

    def _apagado(self, nombre: str) -> pygame.Surface:
        """El sprite oscurecido (trampa desarmada)."""
        imagen = self._apagados.obtener(nombre)
        if imagen is None:
            imagen = self._sprite(nombre).copy()
            imagen.fill((95, 95, 105), special_flags=pygame.BLEND_RGB_MULT)
            self._apagados.insertar(nombre, imagen)
        return imagen

    def _texto(
        self,
        texto: str,
        posicion: tuple[int, int],
        color: tuple[int, int, int] = TEXTO,
        fuente: pygame.font.Font | None = None,
        sombra: bool = True,
    ) -> int:
        """Dibuja texto con una sombra de 1 px. Devuelve el ancho dibujado."""
        fuente = fuente if fuente is not None else self._fuente
        if sombra:
            self._pantalla.blit(fuente.render(texto, True, NEGRO), (posicion[0] + 1, posicion[1] + 1))
        imagen = fuente.render(texto, True, color)
        self._pantalla.blit(imagen, posicion)
        return imagen.get_width()

    @staticmethod
    def _recortar(fuente: pygame.font.Font, texto: str, ancho: int) -> str:
        """Acorta el texto con "..." para que quepa en ``ancho`` pixeles."""
        if fuente.size(texto)[0] <= ancho:
            return texto
        while len(texto) > 1 and fuente.size(texto + "...")[0] > ancho:
            texto = texto[:-1]
        return texto.rstrip() + "..."

    @staticmethod
    def _partir(fuente: pygame.font.Font, texto: str, ancho: int) -> list[str]:
        """Parte el texto en renglones que quepan en ``ancho`` pixeles."""
        renglones: list[str] = []
        actual = ""
        for palabra in texto.split(" "):
            prueba = palabra if not actual else actual + " " + palabra
            if fuente.size(prueba)[0] <= ancho or not actual:
                actual = prueba
            else:
                renglones.append(actual)
                actual = palabra
        renglones.append(actual)
        return renglones

    def _caja(self, rect: pygame.Rect, titulo: str | None = None, nota: str | None = None) -> None:
        pygame.draw.rect(self._pantalla, CAJA, rect, border_radius=6)
        pygame.draw.rect(self._pantalla, BORDE, rect, 2, border_radius=6)
        if titulo:
            self._texto(titulo, (rect.x + 10, rect.y + 6), DORADO, self._fuente_negrita)
        if nota:
            ancho = self._fuente_chica.size(nota)[0]
            self._texto(nota, (rect.right - ancho - 10, rect.y + 8), TENUE, self._fuente_chica)

    def _barra(
        self, x: int, y: int, ancho: int, alto: int, valor: int, maximo: int, con_numeros: bool = False
    ) -> None:
        """Barra de vida: verde, amarilla o roja según cuánto queda."""
        fraccion = valor / maximo if maximo > 0 else 0
        color = VERDE if fraccion > 0.5 else DORADO if fraccion > 0.25 else ROJO
        pygame.draw.rect(self._pantalla, (20, 16, 24), (x, y, ancho, alto))
        pygame.draw.rect(self._pantalla, color, (x, y, max(0, round(ancho * fraccion)), alto))
        pygame.draw.rect(self._pantalla, NEGRO, (x - 1, y - 1, ancho + 2, alto + 2), 1)
        if con_numeros:
            texto = f"{valor}/{maximo}"
            ancho_texto, alto_texto = self._fuente_chica.size(texto)
            self._texto(texto, (x + (ancho - ancho_texto) // 2, y + (alto - alto_texto) // 2), TEXTO, self._fuente_chica)

    def _insignia(self, letra: str, centro: tuple[int, int]) -> None:
        """Cuadrito con la tecla de una salida (W, A, S o D)."""
        rect = pygame.Rect(0, 0, 20, 20)
        rect.center = centro
        pygame.draw.rect(self._pantalla, (12, 10, 16), rect, border_radius=4)
        pygame.draw.rect(self._pantalla, DORADO, rect, 2, border_radius=4)
        ancho, alto = self._fuente_negrita.size(letra)
        self._texto(letra, (rect.centerx - ancho // 2, rect.centery - alto // 2), DORADO, self._fuente_negrita, False)

    def _velo(self, rect: pygame.Rect, color: tuple[int, int, int], alfa: int) -> None:
        """Rectángulo semitransparente encima de lo ya dibujado."""
        capa = pygame.Surface(rect.size, pygame.SRCALPHA)
        capa.fill((*color, max(0, min(255, alfa))))
        self._pantalla.blit(capa, rect.topleft)

    def _agregar_aviso(self, texto: str, error: bool) -> None:
        self._avisos.append(_Aviso(texto, error, pygame.time.get_ticks() + 3500))
        if len(self._avisos) > 3:
            self._avisos.pop(0)

    def _presentar(self) -> None:
        pygame.display.flip()
        self._reloj.tick(FPS)

    # =========================================================================
    # Dibujo: pantallas de inicio
    # =========================================================================

    def _dibujar_portada(self, subtitulo: str) -> None:
        pantalla = self._pantalla
        pantalla.fill(FONDO)
        # Una franja de pared y suelo con personajes, de adorno.
        for columna in range(ANCHO // LADO + 1):
            pantalla.blit(self._sprite("pared"), (columna * LADO, 40))
            pantalla.blit(self._sprite("suelo"), (columna * LADO, 40 + LADO))
        ahora = pygame.time.get_ticks()
        llama = "antorcha_pared_1" if (ahora // 220) % 2 == 0 else "antorcha_pared_2"
        for columna in (2, 8, 14, 19):
            pantalla.blit(self._sprite(llama), (columna * LADO, 40))
        desfile = ("rata", "esqueleto", "jugador", "arana", "murcielago")
        for i in range(len(desfile)):
            salto = -ESCALA if (ahora // 400 + i) % 2 == 0 else 0
            pantalla.blit(self._sprite(desfile[i]), (ANCHO // 2 - 2 * LADO * 2 + i * LADO * 2 - LADO // 2, 40 + LADO + salto))
        titulo = "CRIPTA"
        ancho = self._fuente_grande.size(titulo)[0]
        self._texto(titulo, ((ANCHO - ancho) // 2 + 3, 150 + 3), (60, 30, 20), self._fuente_grande, False)
        self._texto(titulo, ((ANCHO - ancho) // 2, 150), DORADO, self._fuente_grande, False)
        ancho = self._fuente_titulo.size(subtitulo)[0]
        self._texto(subtitulo, ((ANCHO - ancho) // 2, 220), TEXTO, self._fuente_titulo)

    def _dibujar_lista_criptas(self, criptas: list[ResumenCripta], seleccion: int) -> list[pygame.Rect]:
        zonas: list[pygame.Rect] = []
        y = 262
        for i in range(len(criptas)):
            cripta = criptas[i]
            rect = pygame.Rect(ANCHO // 2 - 280, y, 560, 46)
            elegida = i == seleccion
            pygame.draw.rect(self._pantalla, (58, 46, 24) if elegida else CAJA, rect, border_radius=6)
            pygame.draw.rect(self._pantalla, DORADO if elegida else BORDE, rect, 2, border_radius=6)
            self._texto(f"{i + 1}", (rect.x + 14, rect.y + 13), DORADO, self._fuente_titulo)
            self._texto(cripta.nombre, (rect.x + 46, rect.y + 6), DORADO if elegida else TEXTO, self._fuente_negrita)
            self._texto(f"{cripta.id} - {cripta.salas} salas", (rect.x + 46, rect.y + 25), TENUE, self._fuente_chica)
            for j in range(min(cripta.dificultad, 8)):
                self._pantalla.blit(self._icono("calavera"), (rect.right - 26 - j * 20, rect.y + 15))
            zonas.append(rect)
            y += 54
        texto = "Flechas + Enter, el número o un clic.  Esc para salir."
        ancho = self._fuente_chica.size(texto)[0]
        self._texto(texto, ((ANCHO - ancho) // 2, ALTO - 30), TENUE, self._fuente_chica)
        return zonas

    def _dibujar_entrada_nombre(self, nombre: str) -> None:
        rect = pygame.Rect(ANCHO // 2 - 200, 280, 400, 48)
        pygame.draw.rect(self._pantalla, CAJA, rect, border_radius=6)
        pygame.draw.rect(self._pantalla, DORADO, rect, 2, border_radius=6)
        ancho = self._texto(nombre, (rect.x + 16, rect.y + 13), TEXTO, self._fuente_titulo)
        if (pygame.time.get_ticks() // 500) % 2 == 0:  # cursor que parpadea
            pygame.draw.rect(self._pantalla, DORADO, (rect.x + 18 + ancho, rect.y + 12, 3, 24))
        texto = "Escribe tu nombre y presiona Enter."
        ancho = self._fuente_chica.size(texto)[0]
        self._texto(texto, ((ANCHO - ancho) // 2, rect.bottom + 14), TENUE, self._fuente_chica)

    def _pantalla_espera(self, texto: str) -> None:
        """Un cuadro con "Preparando..." mientras el controlador descarga la cripta."""
        self._dibujar_portada(texto)
        self._presentar()

    # =========================================================================
    # Dibujo: la partida
    # =========================================================================

    def _mostrar_cuadro(self) -> None:
        """Dibuja la pantalla completa y la presenta (un cuadro de animación)."""
        ahora = pygame.time.get_ticks()
        self._pantalla.fill(FONDO)
        if self._juego is not None:
            self._dibujar_partida(self._juego, ahora)
        self._dibujar_avisos(ahora)  # debajo de los menús y de las pantallas encima
        if self._menu is not None:
            self._dibujar_menu(self._menu, ahora)
        if self._capa == "ayuda":
            self._dibujar_ayuda()
        elif self._capa == "puntajes":
            self._dibujar_puntajes()
        elif self._capa == "bitacora":
            self._dibujar_bitacora_completa()
        if self._fin is not None:
            self._dibujar_fin(*self._fin)
        self._presentar()

    def _dibujar_partida(self, juego: Juego, ahora: int) -> None:
        sala = juego.jugador.sala
        self._marcables = []
        self._texto(self._recortar(self._fuente_titulo, f"Sala {sala.id}: {sala.nombre}", SALA_ANCHO - 120),
                    (SALA_X + 2, 10), DORADO, self._fuente_titulo)
        reloj = f"t = {juego.reloj}"
        ancho = self._fuente_titulo.size(reloj)[0]
        self._texto(reloj, (SALA_X + SALA_ANCHO - ancho, 10), TEXTO, self._fuente_titulo)
        self._dibujar_sala(juego, ahora)
        self._dibujar_efectos(ahora)
        self._dibujar_salidas(juego)
        self._dibujar_en_sala(juego)
        self._dibujar_panel_jugador(juego)
        self._dibujar_inventario(juego)
        self._dibujar_bitacora(juego)

    def _dibujar_sala(self, juego: Juego, ahora: int) -> None:
        pantalla = self._pantalla
        sala = juego.jugador.sala
        # Paredes y suelo (las grietas salen siempre en el mismo lugar de cada sala).
        for fila in range(FILAS):
            for columna in range(COLUMNAS):
                if fila == 0:
                    nombre = "pared"
                elif fila == FILAS - 1 or columna in (0, COLUMNAS - 1):
                    nombre = "pared_borde"
                elif (columna * 7 + fila * 13 + sala.id * 5) % 11 == 0:
                    nombre = "suelo_grieta"
                else:
                    nombre = "suelo"
                pantalla.blit(self._sprite(nombre), _casilla(columna, fila))
        llama = "antorcha_pared_1" if (ahora // 220) % 2 == 0 else "antorcha_pared_2"
        for columna, fila in POS_ANTORCHAS:
            pantalla.blit(self._sprite(llama), _casilla(columna, fila))

        # Puertas, cada una con la tecla que lleva hacia allá.
        for direccion, (columna, fila) in POS_PUERTAS:
            salida = sala.salida(direccion)
            if salida is None:
                continue
            x, y = _casilla(columna, fila)
            pantalla.blit(self._sprite(self._sprite_puerta(juego, salida)), (x, y))
            if direccion == "N":
                centro = (x + LADO // 2, y + LADO)
            elif direccion == "S":
                centro = (x + LADO // 2, y)
            elif direccion == "O":
                centro = (x + LADO, y + LADO // 2)
            else:
                centro = (x, y + LADO // 2)
            self._insignia(tecla_de(direccion), centro)
            self._marcables.append((direccion, x, y))

        # Trampas (oscurecidas si están desarmadas).
        for i in range(min(len(sala.trampas), len(POS_TRAMPAS))):
            trampa = sala.trampas[i]
            nombre = sprites.sprite_trampa(trampa.tipo_id, trampa.nombre)
            pantalla.blit(self._sprite(nombre) if trampa.armada else self._apagado(nombre), _casilla(*POS_TRAMPAS[i]))

        # Objetos del suelo.
        objetos = sala.objetos_suelo.a_lista()
        for i in range(min(len(objetos), len(POS_OBJETOS))):
            x, y = _casilla(*POS_OBJETOS[i])
            pantalla.blit(self._sombra, (x + 6, y + LADO - 12))
            pantalla.blit(self._sprite(self._info(juego, objetos[i].tipo_id).sprite), (x, y - ESCALA))
            self._marcables.append((objetos[i].id, x, y))

        # Enemigos, con su barra de vida y su número ("#1").
        enemigos = juego.enemigos_en_sala()
        for i in range(min(len(enemigos), len(POS_ENEMIGOS))):
            enemigo = enemigos[i]
            x, y = _casilla(*POS_ENEMIGOS[i])
            nombre = self._sprite_de_enemigo(enemigo)
            imagen = self._destellado(nombre) if self._destella(enemigo.id, ahora) else self._sprite(nombre)
            pantalla.blit(self._sombra, (x + 6, y + LADO - 10))
            pantalla.blit(imagen, (x, y + self._salto(ahora, i + 1)))
            self._barra(x + 6, y - 4, LADO - 12, 5, enemigo.vida, enemigo.vida_max)
            if enemigo.numero > 0:
                etiqueta = f"#{enemigo.numero}"
                ancho = self._fuente_chica.size(etiqueta)[0]
                self._texto(etiqueta, (x + (LADO - ancho) // 2, y + LADO - 4), TEXTO, self._fuente_chica)
            self._marcables.append((enemigo.id, x, y))

        # Jugador.
        jugador = juego.jugador
        x, y = _casilla(*POS_JUGADOR)
        imagen = self._destellado("jugador") if self._destella(Jugador.ID, ahora) else self._sprite("jugador")
        pantalla.blit(self._sombra, (x + 6, y + LADO - 10))
        pantalla.blit(imagen, (x, y + self._salto(ahora, 0)))
        self._barra(x + 6, y - 4, LADO - 12, 5, jugador.vida, jugador.vida_max)
        estados: list[str] = []
        if jugador.antorcha is not None:
            estados.append("llama")
        if jugador.veneno is not None:
            estados.append("veneno")
        if jugador.efecto_velocidad is not None:
            estados.append("velocidad")
        for i in range(len(estados)):
            pantalla.blit(self._icono(estados[i]), (x + LADO - 4, y + 2 + i * 17))

    @staticmethod
    def _sprite_puerta(juego: Juego, salida: Salida) -> str:
        puerta = salida.puerta
        if puerta is None:
            return "paso"
        if not puerta.cerrada:
            return "puerta_abierta"
        if puerta.llave is not None and puerta.llave == juego.datos.llave_salida:
            return "puerta_salida"
        return "puerta_cerrada"

    def _destella(self, actor_id: str, ahora: int) -> bool:
        hasta = self._destellos.obtener(actor_id)
        return hasta is not None and ahora < hasta

    @staticmethod
    def _salto(ahora: int, indice: int) -> int:
        """Animación de "respirar": cada actor sube un pixel cada tanto, desfasados."""
        return -ESCALA if (ahora // 400 + indice) % 2 == 0 else 0

    def _dibujar_efectos(self, ahora: int) -> None:
        """Números flotantes, calaveras, cambio de sala y retroceso (encima de la sala)."""
        pantalla = self._pantalla
        vivos: list[_Flotante] = []
        for flotante in self._flotantes:
            transcurrido = ahora - flotante.inicio
            if transcurrido > 900:
                continue
            vivos.append(flotante)
            imagen = self._fuente_titulo.render(flotante.texto, True, flotante.color)
            contorno = self._fuente_titulo.render(flotante.texto, True, NEGRO)
            alfa = 255 if transcurrido < 500 else int(255 * (900 - transcurrido) / 400)
            imagen.set_alpha(alfa)
            contorno.set_alpha(alfa)
            x = flotante.x - imagen.get_width() // 2
            y = flotante.y - 8 - transcurrido * 32 // 900
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                pantalla.blit(contorno, (x + dx, y + dy))
            pantalla.blit(imagen, (x, y))
        self._flotantes = vivos

        calavera = self._icono("calavera", grande=True)
        quedan: list[tuple[int, int, int]] = []
        for x, y, inicio in self._muertes:
            transcurrido = ahora - inicio
            if transcurrido > 900:
                continue
            quedan.append((x, y, inicio))
            imagen = calavera.copy()
            imagen.set_alpha(int(255 * (900 - transcurrido) / 900))
            pantalla.blit(imagen, (x + (LADO - imagen.get_width()) // 2, y + 10 - transcurrido * 20 // 900))
        self._muertes = quedan

        sala = pygame.Rect(SALA_X, SALA_Y, SALA_ANCHO, SALA_ALTO)
        if ahora < self._transicion_hasta:
            self._velo(sala, NEGRO, 255 * (self._transicion_hasta - ahora) // 260)
        if ahora < self._retroceso_hasta:
            self._velo(sala, MORADO, 150 * (self._retroceso_hasta - ahora) // 600)

    def _dibujar_salidas(self, juego: Juego) -> None:
        caja = pygame.Rect(SALA_X, ABAJO_Y, 290, ABAJO_ALTO)
        self._caja(caja, "SALIDAS")
        self._pantalla.set_clip(caja.inflate(-4, -4))
        y = caja.y + 30
        hay = False
        for salida in juego.jugador.sala.salidas:
            if salida is None:
                continue
            hay = True
            self._insignia(tecla_de(salida.direccion), (caja.x + 22, y + 8))
            texto = f"{nombre_direccion(salida.direccion)}: {salida.destino.nombre}"
            puerta = salida.puerta
            if puerta is not None and not puerta.cerrada:
                texto += " (abierta)"
            self._texto(self._recortar(self._fuente, texto, caja.width - 52), (caja.x + 40, y), TEXTO)
            y += 19
            if puerta is not None and puerta.cerrada:
                self._pantalla.blit(self._icono("candado"), (caja.x + 40, y))
                detalle = "cerrada"  # el candado ya lo dice; si hay llave, se nombra
                if puerta.llave is not None:
                    detalle = f"necesita {self._info(juego, puerta.llave).nombre}"
                self._texto(self._recortar(self._fuente_chica, detalle, caja.width - 76), (caja.x + 60, y + 1),
                            ROJO_CLARO, self._fuente_chica)
                y += 19
        if not hay:
            self._texto("(ninguna)", (caja.x + 12, y), TENUE)
        self._pantalla.set_clip(None)

    def _dibujar_en_sala(self, juego: Juego) -> None:
        caja = pygame.Rect(SALA_X + 298, ABAJO_Y, SALA_ANCHO - 298, ABAJO_ALTO)
        self._caja(caja, "EN LA SALA")
        self._pantalla.set_clip(caja.inflate(-4, -4))
        x, y = caja.x + 10, caja.y + 30
        sala = juego.jugador.sala
        hay = False
        for enemigo in juego.enemigos_en_sala():
            hay = True
            vida = f"{enemigo.vida}/{enemigo.vida_max}"
            ancho_vida = self._fuente_chica.size(vida)[0]
            fraccion = enemigo.vida / enemigo.vida_max if enemigo.vida_max > 0 else 0
            color = VERDE if fraccion > 0.5 else DORADO if fraccion > 0.25 else ROJO
            self._texto(self._recortar(self._fuente, enemigo.etiqueta(), caja.width - 30 - ancho_vida), (x, y), ROJO_CLARO)
            self._texto(vida, (caja.right - 10 - ancho_vida, y + 1), color, self._fuente_chica)
            y += 18
        for objeto in sala.objetos_suelo:
            hay = True
            info = self._info(juego, objeto.tipo_id)
            self._pantalla.blit(self._sprites_chicos.obtener(info.sprite), (x, y))
            self._texto(self._recortar(self._fuente, info.nombre, caja.width - 40), (x + 20, y), TEXTO)
            y += 18
        for trampa in sala.trampas:
            hay = True
            texto = f"{trampa.nombre} ({'armada' if trampa.armada else 'desarmada'})"
            self._texto(self._recortar(self._fuente_chica, texto, caja.width - 20), (x, y + 1),
                        ROJO if trampa.armada else TENUE, self._fuente_chica)
            y += 18
        if not hay:
            self._texto("Nada a la vista.", (x, y), TENUE)
        self._pantalla.set_clip(None)

    def _dibujar_panel_jugador(self, juego: Juego) -> None:
        jugador = juego.jugador
        caja = pygame.Rect(PANEL_X, 8, PANEL_ANCHO, 144)
        self._caja(caja)
        x, y = caja.x + 12, caja.y + 10
        self._pantalla.blit(self._sprite("jugador"), (x, y + 6))
        tx = x + LADO + 14
        self._texto(self._recortar(self._fuente_titulo, jugador.nombre, 200), (tx, y), DORADO, self._fuente_titulo)
        self._pantalla.blit(self._icono("corazon"), (tx, y + 30))
        self._barra(tx + 22, y + 30, 180, 16, jugador.vida, jugador.vida_max, con_numeros=True)
        sx = tx
        for icono, valor in (("ataque", jugador.ataque), ("defensa", jugador.defensa), ("velocidad", jugador.velocidad)):
            self._pantalla.blit(self._icono(icono), (sx, y + 56))
            self._texto(str(valor), (sx + 20, y + 56), TEXTO, self._fuente_negrita)
            sx += 66
        rx = caja.right - 140
        self._pantalla.blit(self._icono("pergamino"), (rx, y))
        self._texto(f"Pergaminos {juego.pergaminos_disponibles()}", (rx + 20, y + 1), MORADO, self._fuente_chica)
        self._texto(f"Acciones   {jugador.acciones_ejecutadas}", (rx + 20, y + 21), TENUE, self._fuente_chica)
        self._texto(f"Derrotados {jugador.enemigos_derrotados}", (rx + 20, y + 41), TENUE, self._fuente_chica)

        arma = self._info(juego, jugador.arma.tipo_id).nombre if jugador.arma is not None else "-"
        armadura = self._info(juego, jugador.armadura.tipo_id).nombre if jugador.armadura is not None else "-"
        self._texto(self._recortar(self._fuente_chica, f"Arma: {arma}", 210), (x, y + 84), TEXTO, self._fuente_chica)
        self._texto(self._recortar(self._fuente_chica, f"Armadura: {armadura}", 210), (x + 220, y + 84),
                    TEXTO, self._fuente_chica)

        efectos: list[tuple[str, str, tuple[int, int, int]]] = []
        if jugador.veneno is not None:
            efectos.append(("veneno", f"Veneno -{jugador.veneno.magnitud} hasta t={jugador.veneno.fin}", VERDE))
        if jugador.efecto_velocidad is not None:
            efecto = jugador.efecto_velocidad
            efectos.append(("velocidad", f"Velocidad {efecto.magnitud:+d} hasta t={efecto.fin}", DORADO))
        if jugador.antorcha is not None:
            efectos.append(("llama", f"Antorcha hasta t={jugador.antorcha.fin}", (255, 160, 80)))
        ex, ey = x, y + 106
        if not efectos:
            self._texto("Sin efectos activos", (ex, ey), TENUE, self._fuente_chica)
        for icono, texto, color in efectos:
            ancho = 20 + self._fuente_chica.size(texto)[0]
            if ex + ancho > caja.right - 10:
                ex, ey = x, ey + 18
            self._pantalla.blit(self._icono(icono), (ex, ey - 1))
            self._texto(texto, (ex + 20, ey), color, self._fuente_chica)
            ex += ancho + 14

    def _dibujar_inventario(self, juego: Juego) -> None:
        jugador = juego.jugador
        inventario = jugador.inventario
        caja = pygame.Rect(PANEL_X, 160, PANEL_ANCHO, 36 + FILAS_INVENTARIO * 20)
        orden = f"por {self._criterio}" if self._criterio is not None else "orden real"
        self._caja(caja, f"INVENTARIO {len(inventario)}/{inventario.capacidad} ({orden})", "I ordena  F usa")
        if self._criterio is not None and self._vista_ordenada is not None:
            objetos = self._vista_ordenada
        else:
            objetos = [objeto for objeto in inventario]
        if not objetos:
            self._texto("(vacío)", (caja.x + 14, caja.y + 30), TENUE)
            return
        actual = inventario.actual()
        posicion_actual = 0
        for i in range(len(objetos)):
            if objetos[i] is actual:
                posicion_actual = i
        inicio = max(0, posicion_actual - FILAS_INVENTARIO + 1)
        y = caja.y + 28
        for i in range(inicio, min(len(objetos), inicio + FILAS_INVENTARIO)):
            objeto = objetos[i]
            info = self._info(juego, objeto.tipo_id)
            if objeto is actual:
                pygame.draw.rect(self._pantalla, (64, 52, 26), (caja.x + 6, y - 1, caja.width - 12, 20), border_radius=4)
                self._texto(">", (caja.x + 10, y + 1), DORADO, self._fuente_negrita)
            self._pantalla.blit(self._sprites_chicos.obtener(info.sprite), (caja.x + 24, y + 1))
            ancho = self._texto(info.nombre, (caja.x + 46, y + 1), DORADO if objeto is actual else TEXTO)
            resto = caja.x + 46 + ancho + 8
            if objeto is jugador.arma or objeto is jugador.armadura:
                resto += self._texto("[equipado]", (resto, y + 2), VERDE, self._fuente_chica) + 8
            espacio = caja.right - 10 - resto
            if info.detalles and espacio > 40:
                self._texto(self._recortar(self._fuente_chica, info.detalles, espacio), (resto, y + 2),
                            TENUE, self._fuente_chica)
            y += 20
        if len(objetos) > FILAS_INVENTARIO:
            self._texto(f"{len(objetos)} objetos (flechas para ver)", (caja.x + 14, caja.bottom - 16), TENUE,
                        self._fuente_chica)

    def _renglones_bitacora(
        self, juego: Juego, fuente: pygame.font.Font, ancho: int
    ) -> list[tuple[str, tuple[int, int, int]]]:
        """Los últimos 20 mensajes con los encabezados de turno, partidos en renglones de ``ancho``."""
        renglones: list[tuple[str, tuple[int, int, int]]] = []
        color_mensaje = TENUE  # lo de turnos anteriores, más apagado
        for clase, tiempo, texto in lineas_bitacora(juego):
            if clase == LINEA_TU_TURNO:
                renglones.append((f"-- {texto} --", AZUL))
                color_mensaje = TEXTO
            elif clase == LINEA_ENEMIGOS:
                renglones.append((f"-- {texto} --", ROJO))
                color_mensaje = ROJO_CLARO
            elif clase == LINEA_SIN_NOVEDADES:
                renglones.append((f"   {texto}", TENUE))
            elif clase == LINEA_MENSAJE:
                partes = self._partir(fuente, f"[t={tiempo}] {texto}", ancho)
                for j in range(len(partes)):
                    renglones.append(((" " * 4 if j > 0 else "") + partes[j], color_mensaje))
        return renglones

    def _dibujar_bitacora(self, juego: Juego) -> None:
        """El panel muestra lo más reciente que cabe; con L se ven los 20 mensajes (§4.8, §10.2)."""
        arriba = 160 + 36 + FILAS_INVENTARIO * 20 + 8  # justo debajo del inventario
        caja = pygame.Rect(PANEL_X, arriba, PANEL_ANCHO, ALTO - arriba - 8)
        self._caja(caja, "BITÁCORA", "L ver los 20   F1 controles")
        renglones = self._renglones_bitacora(juego, self._fuente_chica, caja.width - 24)
        alto_renglon = 15
        visibles = (caja.height - 34) // alto_renglon
        y = caja.y + 28
        for texto, color in renglones[-visibles:]:
            self._texto(texto, (caja.x + 12, y), color, self._fuente_chica)
            y += alto_renglon

    def _dibujar_bitacora_completa(self) -> None:
        """Capa con los últimos 20 mensajes completos (tecla L)."""
        self._velo(self._pantalla.get_rect(), NEGRO, 170)
        rect = pygame.Rect(40, 24, ANCHO - 80, ALTO - 48)
        pygame.draw.rect(self._pantalla, CAJA, rect, border_radius=8)
        pygame.draw.rect(self._pantalla, DORADO, rect, 2, border_radius=8)
        if self._juego is None:
            return
        cantidad = len(self._juego.mensajes)
        self._texto(f"BITÁCORA: los últimos {cantidad} mensajes", (rect.x + 20, rect.y + 14), DORADO, self._fuente_titulo)
        renglones = self._renglones_bitacora(self._juego, self._fuente, rect.width - 40)
        alto_renglon = 17
        visibles = (rect.height - 90) // alto_renglon
        y = rect.y + 50
        for texto, color in renglones[-visibles:]:
            self._texto(texto, (rect.x + 20, y), color, self._fuente)
            y += alto_renglon
        self._texto("Presiona cualquier tecla para volver", (rect.x + 20, rect.bottom - 30), AZUL, self._fuente_negrita)

    # =========================================================================
    # Dibujo: menús, capas y avisos
    # =========================================================================

    def _dibujar_menu(self, menu: _Menu, ahora: int) -> None:
        """El menú va sobre el panel derecho, así la sala queda a la vista."""
        # Flecha que salta encima de la cosa a la que se refiere la opción elegida.
        if menu.marcas is not None:
            marca = menu.marcas[menu.seleccion]
            for marcable, x, y in self._marcables:
                if marcable == marca:
                    flecha = self._icono("flecha", grande=True)
                    rebote = (0, 3, 6, 3)[(ahora // 120) % 4]
                    self._pantalla.blit(flecha, (x + (LADO - flecha.get_width()) // 2, y - 30 + rebote))
        self._velo(pygame.Rect(PANEL_X - 4, 0, ANCHO - PANEL_X + 4, ALTO), NEGRO, 150)
        ancho = PANEL_ANCHO - 20
        titulo = self._partir(self._fuente_negrita, menu.titulo, ancho - 28)
        alto = 20 + 20 * len(titulo) + 10 + 28 * len(menu.opciones) + 34
        rect = pygame.Rect(PANEL_X + 10, (ALTO - alto) // 2, ancho, alto)
        pygame.draw.rect(self._pantalla, CAJA, rect, border_radius=8)
        pygame.draw.rect(self._pantalla, DORADO, rect, 2, border_radius=8)
        y = rect.y + 14
        for renglon in titulo:
            self._texto(renglon, (rect.x + 14, y), DORADO, self._fuente_negrita)
            y += 20
        y += 8
        menu.zonas = []
        for i in range(len(menu.opciones)):
            zona = pygame.Rect(rect.x + 8, y, rect.width - 16, 26)
            if i == menu.seleccion:
                pygame.draw.rect(self._pantalla, (70, 56, 24), zona, border_radius=5)
            self._texto(str(i + 1), (zona.x + 8, zona.y + 4), DORADO, self._fuente_negrita)
            self._texto(self._recortar(self._fuente, menu.opciones[i], zona.width - 44), (zona.x + 30, zona.y + 4),
                        DORADO if i == menu.seleccion else TEXTO)
            menu.zonas.append(zona)
            y += 28
        self._texto("Enter o el número para elegir   Esc cancela", (rect.x + 14, rect.bottom - 24), TENUE,
                    self._fuente_chica)

    def _dibujar_ayuda(self) -> None:
        self._velo(self._pantalla.get_rect(), NEGRO, 170)
        rect = pygame.Rect(ANCHO // 2 - 300, 70, 600, 470)
        pygame.draw.rect(self._pantalla, CAJA, rect, border_radius=8)
        pygame.draw.rect(self._pantalla, DORADO, rect, 2, border_radius=8)
        self._texto("CONTROLES", (rect.x + 20, rect.y + 16), DORADO, self._fuente_titulo)
        y = rect.y + 54
        for tecla, descripcion in AYUDA:
            self._texto(tecla, (rect.x + 24, y), DORADO, self._fuente_negrita)
            self._texto(descripcion, (rect.x + 190, y), TEXTO)
            y += 24
        notas = (
            "El tiempo solo avanza cuando haces algo. Después de tu turno",
            "actúan los enemigos, según su velocidad (el más rápido, más veces).",
        )
        y += 8
        for nota in notas:
            self._texto(nota, (rect.x + 24, y), TENUE, self._fuente_chica)
            y += 17
        self._texto("Presiona cualquier tecla para jugar", (rect.x + 24, rect.bottom - 30), AZUL, self._fuente_negrita)

    def _dibujar_puntajes(self) -> None:
        self._velo(self._pantalla.get_rect(), NEGRO, 170)
        rect = pygame.Rect(ANCHO // 2 - 330, 70, 660, 470)
        pygame.draw.rect(self._pantalla, CAJA, rect, border_radius=8)
        pygame.draw.rect(self._pantalla, DORADO, rect, 2, border_radius=8)
        self._texto("PUNTAJES", (rect.x + 20, rect.y + 16), DORADO, self._fuente_titulo)
        y = rect.y + 54
        if not self._puntajes:
            self._texto("Todavía no hay puntajes.", (rect.x + 24, y), TENUE)
        else:
            encabezado = f"{'#':>3} {'Jugador':<16} {'Cripta':<11} {'Resultado':<10} {'Acc.':>5} {'Derr.':>5} {'Reloj':>7}"
            self._texto(encabezado, (rect.x + 20, y), DORADO, self._fuente_negrita)
            y += 24
            for i in range(min(len(self._puntajes), 15)):
                r = self._puntajes[i]
                fila = (f"{i + 1:>3} {r.nombre[:16]:<16} {r.cripta_id[:11]:<11} {r.resultado:<10} "
                        f"{r.acciones:>5} {r.enemigos_derrotados:>5} {r.tiempo_final:>7}")
                self._texto(fila, (rect.x + 20, y), VERDE if r.resultado == "victoria" else TEXTO)
                y += 22
        self._texto("Presiona cualquier tecla para volver", (rect.x + 24, rect.bottom - 30), AZUL, self._fuente_negrita)

    def _dibujar_fin(self, resumen: ResumenPartida, reporte_red: str) -> None:
        self._velo(self._pantalla.get_rect(), NEGRO, 185)
        if resumen.estado is EstadoPartida.VICTORIA:
            titulo, color, frase = "VICTORIA", DORADO, "Escapaste de la cripta."
        elif resumen.estado is EstadoPartida.DERROTA:
            titulo, color, frase = "DERROTA", ROJO, "La cripta se queda con otro aventurero."
        else:
            titulo, color, frase = "FIN", TEXTO, "Partida terminada sin resolver."
        rect = pygame.Rect(ANCHO // 2 - 380, 60, 760, ALTO - 120)
        pygame.draw.rect(self._pantalla, CAJA, rect, border_radius=8)
        pygame.draw.rect(self._pantalla, color, rect, 2, border_radius=8)
        ancho = self._fuente_grande.size(titulo)[0]
        self._texto(titulo, ((ANCHO - ancho) // 2, 90), color, self._fuente_grande)
        ancho = self._fuente_titulo.size(frase)[0]
        self._texto(frase, ((ANCHO - ancho) // 2, 160), TEXTO, self._fuente_titulo)
        lineas = (
            f"Jugador: {resumen.nombre_jugador}",
            f"Cripta: {resumen.cripta_id} (versión {resumen.version_cripta})",
            f"Acciones ejecutadas: {resumen.acciones_ejecutadas}",
            f"Enemigos derrotados: {resumen.enemigos_derrotados}",
            f"Tiempo final del reloj: {resumen.tiempo_final}",
        )
        y = 214
        for linea in lineas:
            self._texto(linea, (ANCHO // 2 - 220, y), TEXTO)
            y += 22
        y += 10
        for linea in reporte_red.splitlines():
            for renglon in self._partir(self._fuente_chica, linea, 700):
                self._texto(renglon, (ANCHO // 2 - 350, y), TENUE, self._fuente_chica)
                y += 16
        texto = "Presiona cualquier tecla para cerrar"
        ancho = self._fuente_negrita.size(texto)[0]
        self._texto(texto, ((ANCHO - ancho) // 2, rect.bottom - 36), AZUL, self._fuente_negrita)

    def _dibujar_avisos(self, ahora: int) -> None:
        """Avisos cortos (errores en rojo) abajo de la sala; se borran solos."""
        self._avisos = [aviso for aviso in self._avisos if aviso.hasta > ahora]
        y = SALA_Y + SALA_ALTO - 54
        for i in range(len(self._avisos) - 1, -1, -1):
            aviso = self._avisos[i]
            texto = self._recortar(self._fuente, aviso.texto, SALA_ANCHO - 60)
            ancho = self._fuente.size(texto)[0] + 28
            rect = pygame.Rect(SALA_X + (SALA_ANCHO - ancho) // 2, y, ancho, 28)
            fondo = (70, 20, 24) if aviso.error else (24, 36, 70)
            borde = ROJO if aviso.error else AZUL
            pygame.draw.rect(self._pantalla, fondo, rect, border_radius=6)
            pygame.draw.rect(self._pantalla, borde, rect, 2, border_radius=6)
            self._texto(texto, (rect.x + 14, rect.y + 6), TEXTO)
            y -= 34
