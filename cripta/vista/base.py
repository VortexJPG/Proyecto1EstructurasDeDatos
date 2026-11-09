"""Lógica común de las dos vistas: consola y ventana.                  [Persona A]

Las dos vistas hacen lo mismo con lo que elige el usuario: lo traducen a un
``ComandoUsuario`` con ids de instancia reales ("e-202", "o-2-1") ANTES de
entregarlo al controlador, así el replay no depende de la pantalla. Lo único
que cambia entre una y otra es CÓMO se pregunta (menú numerado en el texto o
menú en la ventana) y cómo se muestran los avisos. Por eso aquí va todo lo que
no depende de eso, y cada vista implementa ``_preguntar``, ``mostrar_error`` y
``mostrar_info``.

La vista NUNCA modifica el modelo: solo lee el estado y devuelve comandos.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, TypeVar

from cripta.controlador.comandos import ComandoUsuario, TipoComando
from cripta.modelo.acciones import Accion, TipoAccion
from cripta.modelo.objetos import ClaseObjeto
from cripta.modelo.puertos import FichaNoDisponible

if TYPE_CHECKING:
    from cripta.modelo.datos import Ficha
    from cripta.modelo.juego import Juego
    from cripta.modelo.mapa import Salida
    from cripta.modelo.objetos import InstanciaObjeto

T = TypeVar("T")

# Teclas de movimiento (W A S D) y palabras que también se aceptan.
DIRECCIONES_TEXTO: tuple[tuple[str, str], ...] = (
    ("w", "N"), ("norte", "N"),
    ("a", "O"), ("oeste", "O"),
    ("s", "S"), ("sur", "S"),
    ("d", "E"), ("este", "E"),
)
_NOMBRE_DIRECCION: tuple[tuple[str, str], ...] = (("N", "Norte"), ("S", "Sur"), ("E", "Este"), ("O", "Oeste"))
_TECLA_DIRECCION: tuple[tuple[str, str], ...] = (("N", "W"), ("S", "S"), ("E", "D"), ("O", "A"))

# Clases de línea que devuelve ``lineas_bitacora``.
LINEA_TU_TURNO = "turno"
LINEA_ENEMIGOS = "enemigos"
LINEA_MENSAJE = "mensaje"
LINEA_SIN_NOVEDADES = "nada"


def direccion_desde_texto(texto: str) -> str | None:
    """'w' o 'norte' → 'N'. None si no es una dirección."""
    for palabra, direccion in DIRECCIONES_TEXTO:
        if palabra == texto:
            return direccion
    return None


def nombre_direccion(direccion: str) -> str:
    """'N' → 'Norte'."""
    for letra, nombre in _NOMBRE_DIRECCION:
        if letra == direccion:
            return nombre
    return direccion


def tecla_de(direccion: str) -> str:
    """'N' → 'W' (la tecla que hay que apretar para ir en esa dirección)."""
    for letra, tecla in _TECLA_DIRECCION:
        if letra == direccion:
            return tecla
    return direccion


def puertas_cerradas(juego: Juego) -> list[Salida]:
    """Salidas de la sala actual con la puerta cerrada, en orden N, S, E, O."""
    return [
        salida for salida in juego.jugador.sala.salidas
        if salida is not None and salida.puerta is not None and salida.puerta.cerrada
    ]


def lineas_bitacora(juego: Juego) -> list[tuple[str, int | None, str]]:
    """Últimos mensajes con los encabezados "Tu turno" / "Turno de los enemigos".

    Devuelve tríos (clase, tiempo, texto); ``clase`` es una de las constantes
    LINEA_*; ``tiempo`` solo viene en los mensajes.

    El juego sigue el reloj virtual del enunciado (§2.3); estos encabezados
    solo agrupan lo que pasó en la última decisión para leerlo como turnos:
    primero lo que hiciste tú y después todo lo que pasó hasta que vuelve a
    ser tu turno (los enemigos rápidos pueden actuar más de una vez).
    """
    lineas: list[tuple[str, int | None, str]] = []
    marca_turno = juego.marca_turno
    marca_enemigos = juego.marca_enemigos
    numero_turno = juego.jugador.acciones_ejecutadas
    primero = True
    for numero, tiempo, texto in juego.mensajes.ultimos_numerados():
        if primero:
            primero = False
            # El inicio del bloque pudo salir de los últimos 20 mensajes.
            if marca_enemigos is not None and marca_enemigos < numero:
                lineas.append((LINEA_ENEMIGOS, None, "Turno de los enemigos (continuación)"))
            elif marca_turno is not None and marca_turno < numero:
                lineas.append((LINEA_TU_TURNO, None, f"Tu turno #{numero_turno} (continuación)"))
        if numero == marca_turno:
            lineas.append((LINEA_TU_TURNO, None, f"Tu turno #{numero_turno}"))
        if numero == marca_enemigos:
            lineas.append((LINEA_ENEMIGOS, None, "Turno de los enemigos"))
        lineas.append((LINEA_MENSAJE, tiempo, texto))
    if marca_enemigos is not None and marca_enemigos >= juego.mensajes.total:
        lineas.append((LINEA_ENEMIGOS, None, "Turno de los enemigos"))
        lineas.append((LINEA_SIN_NOVEDADES, None, "(sin novedades)"))
    return lineas


class VistaBase:
    """Traducción común de "lo que elige el usuario" → ``ComandoUsuario``."""

    # --- lo que implementa cada vista ----------------------------------------------

    def _preguntar(self, titulo: str, opciones: list[str], marcas: list[str] | None = None) -> int | None:
        """Menú de opciones. Devuelve la posición elegida (desde 0) o None si se cancela.

        ``marcas`` (opcional, paralela a ``opciones``) dice a qué cosa de la
        sala se refiere cada opción (id de enemigo, id de objeto o dirección
        de una puerta), para que la ventana pueda señalarla. La consola la ignora.
        """
        raise NotImplementedError

    def mostrar_error(self, texto: str) -> None:
        raise NotImplementedError

    def mostrar_info(self, texto: str) -> None:
        raise NotImplementedError

    # --- común ----------------------------------------------------------------------

    @staticmethod
    def _accion(tipo: TipoAccion, direccion: str | None = None, objetivo: str | None = None) -> ComandoUsuario:
        return ComandoUsuario(TipoComando.ACCION, accion=Accion(tipo, direccion, objetivo))

    def _elegir_de_lista(
        self,
        elementos: list[T],
        argumento: str | None,
        pregunta: str,
        si_vacia: str,
        describir: Callable[[T], str],
        marca: Callable[[T], str] | None = None,
    ) -> T | None:
        """Elemento k (desde 1) de ``elementos``; sin k: el único que haya o se pregunta."""
        if not elementos:
            self.mostrar_error(si_vacia)
            return None
        if argumento is None:
            if len(elementos) == 1:
                return elementos[0]
            marcas = [marca(elemento) for elemento in elementos] if marca is not None else None
            indice = self._preguntar(pregunta, [describir(elemento) for elemento in elementos], marcas)
            return elementos[indice] if indice is not None else None
        if not argumento.isdigit() or not 1 <= int(argumento) <= len(elementos):
            self.mostrar_error(f"Número inválido: {argumento} (hay {len(elementos)}).")
            return None
        return elementos[int(argumento) - 1]

    def _atacar(self, juego: Juego, argumento: str | None) -> ComandoUsuario | None:
        """Q [k]: sin k, el único enemigo de la sala o se pregunta a cuál."""
        enemigo = self._elegir_de_lista(
            juego.enemigos_en_sala(), argumento, "¿A quién atacas?", "No hay enemigos en la sala.",
            lambda e: f"{e.etiqueta()} (vida {e.vida}/{e.vida_max})",
            lambda e: e.id,
        )
        return self._accion(TipoAccion.ATACAR, objetivo=enemigo.id) if enemigo is not None else None

    def _recoger(self, juego: Juego, argumento: str | None) -> ComandoUsuario | None:
        """E [k]: sin k, el único objeto del suelo o se pregunta cuál."""
        objeto = self._elegir_de_lista(
            juego.jugador.sala.objetos_suelo.a_lista(), argumento, "¿Qué recoges?",
            "No hay objetos en el suelo.", lambda o: juego.nombre_de_tipo(o.tipo_id),
            lambda o: o.id,
        )
        return self._accion(TipoAccion.RECOGER, objetivo=objeto.id) if objeto is not None else None

    def _abrir(self, juego: Juego, argumento: str | None) -> ComandoUsuario | None:
        """R [W/A/S/D]: sin dirección, abre la única puerta cerrada o pregunta cuál."""
        if argumento is not None:
            direccion = direccion_desde_texto(argumento.lower())
            if direccion is None:
                self.mostrar_error("Indica la puerta con W/A/S/D (por ejemplo, R D abre la del este).")
                return None
            return self._accion(TipoAccion.ABRIR, direccion=direccion)
        cerradas = puertas_cerradas(juego)
        if not cerradas:
            self.mostrar_error("No hay puertas cerradas en esta sala.")
            return None
        if len(cerradas) == 1:
            return self._accion(TipoAccion.ABRIR, direccion=cerradas[0].direccion)
        indice = self._preguntar(
            "¿Qué puerta abres?",
            [f"[{tecla_de(s.direccion)}] {nombre_direccion(s.direccion)} -> {s.destino.nombre}" for s in cerradas],
            [s.direccion for s in cerradas],
        )
        return self._accion(TipoAccion.ABRIR, direccion=cerradas[indice].direccion) if indice is not None else None

    def _menu_objeto(self, juego: Juego, objeto: InstanciaObjeto) -> ComandoUsuario | None:
        """F: pregunta qué hacer con el objeto (solo muestra lo que tiene sentido)."""
        jugador = juego.jugador
        nombre = juego.nombre_de_tipo(objeto.tipo_id)
        equipado = objeto is jugador.arma or objeto is jugador.armadura
        opciones: list[tuple[str, ComandoUsuario]] = []
        if objeto.clase in (ClaseObjeto.ARMA, ClaseObjeto.ARMADURA) and not equipado:
            opciones.append(("Equipar", self._accion(TipoAccion.EQUIPAR, objetivo=objeto.id)))
        elif objeto.clase in (ClaseObjeto.POCION, ClaseObjeto.ANTIDOTO, ClaseObjeto.ANTORCHA):
            opciones.append(("Usar", self._accion(TipoAccion.USAR, objetivo=objeto.id)))
        elif objeto.clase is ClaseObjeto.PERGAMINO:
            opciones.append(("Usar (deshacer tu última acción)", self._accion(TipoAccion.RETROCEDER)))
        opciones.append(("Soltar", self._accion(TipoAccion.SOLTAR, objetivo=objeto.id)))
        titulo = f"¿Qué haces con {nombre}{' [equipado]' if equipado else ''}?"
        if objeto.clase is ClaseObjeto.LLAVE:
            titulo += " (las llaves se usan solas al abrir con R)"
        indice = self._preguntar(titulo, [texto for texto, _ in opciones])
        return opciones[indice][1] if indice is not None else None

    def _objeto_de_inventario(self, juego: Juego, argumento: str | None) -> InstanciaObjeto | None:
        """Objeto k del orden real; sin k, el que está bajo el cursor."""
        inventario = juego.jugador.inventario
        if len(inventario) == 0:
            self.mostrar_error("Tu inventario está vacío.")
            return None
        if argumento is None:
            return inventario.actual()
        if not argumento.isdigit():
            self.mostrar_error(f"Número de objeto inválido: {argumento}")
            return None
        objeto = inventario.objeto_en_posicion(int(argumento) - 1)
        if objeto is None:
            self.mostrar_error(f"No hay objeto {argumento} en el inventario (1-{len(inventario)}).")
        return objeto

    @staticmethod
    def _describir_objeto(juego: Juego, objeto: InstanciaObjeto) -> str:
        """"Daga oxidada (peso 2, valor 15, atq +3)"."""
        try:
            ficha = juego.fichas.obtener(objeto.tipo_id)
        except FichaNoDisponible:
            return objeto.tipo_id
        return f"{ficha.nombre} ({detalles_ficha(ficha)})"


def detalles_ficha(ficha: Ficha) -> str:
    """"peso 2, valor 15, atq +3": lo que sirve para decidir qué hacer con un objeto."""
    detalles: list[str] = [f"peso {ficha.peso if ficha.peso is not None else 0}",
                           f"valor {ficha.valor if ficha.valor is not None else 0}"]
    if ficha.ataque_bonus:
        detalles.append(f"atq +{ficha.ataque_bonus}")
    if ficha.defensa_bonus:
        detalles.append(f"def +{ficha.defensa_bonus}")
    if ficha.cura:
        detalles.append(f"cura {ficha.cura}")
    if ficha.modificador_velocidad:
        detalles.append(f"vel {ficha.modificador_velocidad:+d} por {ficha.duracion}")
    if ficha.clase == "antorcha" and ficha.duracion:
        detalles.append(f"dura {ficha.duracion}")
    return ", ".join(detalles)
