"""Interfaz de consola.                                              [Persona A]

§10.2: debe permitir seleccionar cripta, moverse en 4 direcciones, abrir
puertas, atacar a un enemigo elegido, esperar, recoger / usar / equipar /
soltar, recorrer el inventario (también ordenado), usar pergamino, guardar,
cargar y salir. Debe mostrar: sala actual, salidas, enemigos (identificables:
"Rata gigante #1"), objetos del suelo, vida y estadísticas, efectos activos y
los últimos 20 mensajes.

Controles: W/A/S/D moverse, Q atacar, E recoger, R abrir, F usar / equipar /
soltar (con un menú), T esperar, I inventario. Cuando hay que elegir (varios
enemigos, varios objetos, varias puertas), la vista pregunta con un menú
numerado en vez de dar error. Se escribe la letra y se presiona Enter.

La traducción de lo que elige el usuario a comandos (con ids de instancia
reales) es la misma que usa la ventana: está en ``vista/base.py``. Aquí solo
queda lo propio del texto: leer líneas, imprimir y el menú numerado.

La vista NUNCA modifica el modelo: solo lee el estado y devuelve un
``ComandoUsuario``. Incluso mover el cursor del inventario es un comando
(INVENTARIO_SIGUIENTE / INVENTARIO_ANTERIOR) que ejecuta el controlador.

Solo se usan caracteres que existen en la consola de Windows (sin cajas ni
flechas Unicode).
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from cripta.controlador.comandos import ComandoUsuario, TipoComando
from cripta.modelo.acciones import TipoAccion
from cripta.modelo.juego import EstadoPartida
from cripta.vista.base import (
    LINEA_ENEMIGOS,
    LINEA_MENSAJE,
    LINEA_TU_TURNO,
    VistaBase,
    direccion_desde_texto,
    lineas_bitacora,
    nombre_direccion,
    tecla_de,
)

if TYPE_CHECKING:
    from cripta.adaptadores.puntajes import RegistroPuntaje
    from cripta.modelo.acciones import ResultadoAccion
    from cripta.modelo.datos import ResumenCripta
    from cripta.modelo.juego import Juego
    from cripta.modelo.objetos import InstanciaObjeto

ANCHO = 64
LINEA_DOBLE = "=" * ANCHO
LINEA_SIMPLE = "-" * ANCHO

TECLAS = "W/A/S/D moverse | Q atacar | E recoger | R abrir | F objeto | T esperar | I inventario"

AYUDA = """\
Controles (escribe la letra y presiona Enter; no importan mayúsculas):
  W / A / S / D        moverse al norte / oeste / sur / este
  Q [k]                atacar al enemigo k (si hay varios y no pones k, te pregunta)
  E [k]                recoger el objeto k del suelo (igual: si hay varios, te pregunta)
  R [W/A/S/D]          abrir una puerta con llave (p. ej. "R D" abre la del este;
                       si hay una sola puerta cerrada, basta con R)
  F [k]                usar, equipar o soltar el objeto k del inventario
                       (sin k: el que estás viendo con el cursor >); te pregunta qué hacer
  T                    esperar
  I                    ver el inventario (orden real, con el cursor >)
  sig | ant            mover el cursor del inventario
  ordenar peso|valor|nombre   ver el inventario ordenado (no cambia el orden real)
  retroceder           usar un pergamino de retroceso
  guardar [ruta] | cargar [ruta]   (sin ruta: datos_locales/partida_guardada.sav)
  puntajes             tabla de puntajes
  ayuda | ?            esta ayuda
  salir                terminar la sesión
También se aceptan las palabras completas: norte, atacar 2, recoger, abrir este, usar 3..."""


def _imprimir(texto: str = "") -> None:
    """``print`` que no se cae si la consola no soporta algún carácter."""
    try:
        print(texto)
    except UnicodeEncodeError:
        codificacion = sys.stdout.encoding or "ascii"
        print(texto.encode(codificacion, errors="replace").decode(codificacion))


def _separar(texto: str) -> list[str]:
    """Parte la línea en palabras; "q2" se entiende como "q 2"."""
    partes = texto.strip().split()
    primera = partes[0]
    if len(primera) > 1 and primera[0].isalpha() and primera[1:].isdigit():
        partes = [primera[0], primera[1:]] + partes[1:]
    return partes


class VistaConsola(VistaBase):
    def __init__(self) -> None:
        self._entrada = input  # se puede reemplazar en pruebas

    # --- entrada ------------------------------------------------------------------

    def elegir_cripta(self, criptas: list[ResumenCripta]) -> str:
        """Devuelve el id de la cripta elegida."""
        if not criptas:
            raise ValueError("El servicio no tiene criptas publicadas")
        _imprimir(LINEA_DOBLE)
        if len(criptas) == 1:
            _imprimir(f"Cripta: {criptas[0].nombre} [{criptas[0].id}]  salas: {criptas[0].salas}"
                      f"  dificultad: {criptas[0].dificultad}")
            return criptas[0].id
        _imprimir("Criptas disponibles:")
        for i in range(len(criptas)):
            cripta = criptas[i]
            _imprimir(f"  {i + 1}) {cripta.nombre} [{cripta.id}]  salas: {cripta.salas}  dificultad: {cripta.dificultad}")
        while True:
            texto = self._leer("Elige una cripta (número o id): ")
            if texto.isdigit() and 1 <= int(texto) <= len(criptas):
                return criptas[int(texto) - 1].id
            for cripta in criptas:
                if cripta.id == texto:
                    return cripta.id
            self.mostrar_error("Opción no válida.")

    def pedir_nombre(self) -> str:
        try:
            nombre = self._leer("Nombre del jugador: ")
        except EOFError:
            return "Jugador"
        return nombre if nombre else "Jugador"

    def pedir_comando(self, juego: Juego) -> ComandoUsuario:
        """Lee una línea y la convierte en comando; repite si no se entiende."""
        while True:
            try:
                texto = self._leer("> ")
            except EOFError:
                return ComandoUsuario(TipoComando.SALIR)
            except KeyboardInterrupt:
                _imprimir()
                return ComandoUsuario(TipoComando.SALIR)
            if not texto:
                continue
            comando = self._interpretar(texto, juego)
            if comando is not None:
                return comando

    def _interpretar(self, texto: str, juego: Juego) -> ComandoUsuario | None:
        """Texto → ComandoUsuario (None si no es válido o se canceló; el motivo ya se mostró)."""
        partes = _separar(texto)
        verbo = partes[0].lower()
        argumento = partes[1] if len(partes) > 1 else None
        resto = texto.strip()[len(texto.strip().split()[0]):].strip()  # para rutas con espacios

        # --- W A S D: moverse -------------------------------------------------------
        direccion = direccion_desde_texto(verbo)
        if direccion is not None and argumento is None:
            return self._accion(TipoAccion.MOVER, direccion=direccion)
        if verbo in ("mover", "ir"):
            direccion = direccion_desde_texto(argumento.lower()) if argumento else None
            if direccion is None:
                self.mostrar_error("Indica la dirección con W/A/S/D (o norte, sur, este, oeste).")
                return None
            return self._accion(TipoAccion.MOVER, direccion=direccion)

        # --- R: abrir / Q: atacar / T: esperar ------------------------------------------
        if verbo in ("r", "abrir"):
            return self._abrir(juego, argumento)
        if verbo in ("q", "atacar"):
            return self._atacar(juego, argumento)
        if verbo in ("t", "esperar"):
            return self._accion(TipoAccion.ESPERAR)

        # --- E: recoger / F: usar, equipar o soltar -------------------------------------
        if verbo in ("e", "recoger", "tomar"):
            return self._recoger(juego, argumento)
        if verbo == "f":
            objeto = self._objeto_de_inventario(juego, argumento)
            return self._menu_objeto(juego, objeto) if objeto is not None else None
        if verbo in ("soltar", "usar", "equipar"):
            objeto = self._objeto_de_inventario(juego, argumento)
            if objeto is None:
                return None
            tipo = TipoAccion.SOLTAR if verbo == "soltar" else TipoAccion.USAR if verbo == "usar" else TipoAccion.EQUIPAR
            return self._accion(tipo, objetivo=objeto.id)
        if verbo in ("retroceder", "pergamino", "deshacer"):
            return self._accion(TipoAccion.RETROCEDER)

        # --- I: inventario ------------------------------------------------------------
        if verbo in ("i", "inv", "inventario"):
            return ComandoUsuario(TipoComando.VER_INVENTARIO)
        if verbo in ("sig", "siguiente", ">"):
            return ComandoUsuario(TipoComando.INVENTARIO_SIGUIENTE)
        if verbo in ("ant", "anterior", "<"):
            return ComandoUsuario(TipoComando.INVENTARIO_ANTERIOR)
        if verbo in ("ordenar", "orden"):
            criterio = argumento.lower() if argumento else ""
            if criterio not in ("peso", "valor", "nombre"):
                self.mostrar_error("Uso: ordenar peso|valor|nombre")
                return None
            return ComandoUsuario(TipoComando.VISTA_ORDENADA, argumento=criterio)

        # --- sesión -----------------------------------------------------------------
        if verbo in ("guardar", "cargar"):
            # Sin ruta, el controlador usa su archivo por defecto.
            tipo = TipoComando.GUARDAR if verbo == "guardar" else TipoComando.CARGAR
            return ComandoUsuario(tipo, argumento=resto or None)
        if verbo == "puntajes":
            return ComandoUsuario(TipoComando.PUNTAJES)
        if verbo in ("ayuda", "?", "h"):
            return ComandoUsuario(TipoComando.AYUDA)
        if verbo in ("salir", "exit"):  # "q" ya no: ahora es atacar
            return ComandoUsuario(TipoComando.SALIR)

        self.mostrar_error(f"No entiendo '{texto.strip()}'. Escribe 'ayuda' para ver los comandos.")
        return None

    # --- salida -------------------------------------------------------------------

    def mostrar_estado(self, juego: Juego) -> None:
        """Sala, salidas, enemigos, suelo, jugador, efectos y mensajes."""
        jugador = juego.jugador
        sala = jugador.sala
        _imprimir()
        _imprimir(LINEA_DOBLE)
        _imprimir(f" t={juego.reloj:<7} Sala {sala.id}: {sala.nombre}")
        _imprimir(LINEA_DOBLE)

        # Salidas.
        salidas: list[str] = []
        for salida in sala.salidas:
            if salida is None:
                continue
            texto = (f"[{tecla_de(salida.direccion)}] {nombre_direccion(salida.direccion)} -> "
                     f"{salida.destino.nombre} ({salida.destino.id})")
            if salida.puerta is not None:
                if salida.puerta.cerrada:
                    llave = salida.puerta.llave
                    texto += f" [cerrada{', llave: ' + juego.nombre_de_tipo(llave) if llave else ''}]"
                else:
                    texto += " [abierta]"
            salidas.append(texto)
        _imprimir("Salidas:")
        for texto in salidas:
            _imprimir(f"  {texto}")
        if not salidas:
            _imprimir("  (ninguna)")

        # Enemigos, suelo y trampas.
        enemigos = juego.enemigos_en_sala()
        _imprimir("Enemigos:" if enemigos else "Enemigos: ninguno")
        for i in range(len(enemigos)):
            enemigo = enemigos[i]
            proxima = enemigo.tiempo_siguiente
            _imprimir(
                f"  {i + 1}) {enemigo.etiqueta():<24} vida {enemigo.vida}/{enemigo.vida_max}"
                f"  atq {enemigo.ataque} def {enemigo.defensa} vel {enemigo.velocidad}"
                f"  {'actúa en t=' + str(proxima) if proxima is not None else ''}"
            )
        suelo = sala.objetos_suelo.a_lista()
        _imprimir("Suelo:" if suelo else "Suelo: vacío")
        for i in range(len(suelo)):
            _imprimir(f"  {i + 1}) {juego.nombre_de_tipo(suelo[i].tipo_id)}")
        if sala.trampas:
            textos = [f"{t.nombre} ({'armada' if t.armada else 'desarmada'})" for t in sala.trampas]
            _imprimir("Trampas: " + ", ".join(textos))

        # Jugador.
        _imprimir(LINEA_SIMPLE)
        proxima = jugador.tiempo_siguiente
        _imprimir(
            f"{jugador.nombre}: vida {jugador.vida}/{jugador.vida_max}  atq {jugador.ataque}  "
            f"def {jugador.defensa}  vel {jugador.velocidad}"
            + (f"  | próxima acción en t={proxima}" if proxima is not None else "")
        )
        arma = juego.nombre_de_tipo(jugador.arma.tipo_id) if jugador.arma is not None else "-"
        armadura = juego.nombre_de_tipo(jugador.armadura.tipo_id) if jugador.armadura is not None else "-"
        _imprimir(f"Equipo: arma {arma} | armadura {armadura}")
        _imprimir(
            f"Inventario: {len(jugador.inventario)}/{jugador.inventario.capacidad} objetos"
            f"  | pergaminos: {juego.pergaminos_disponibles()}"
            f"  | acciones: {jugador.acciones_ejecutadas}  derrotados: {jugador.enemigos_derrotados}"
        )
        efectos: list[str] = []
        if jugador.veneno is not None:
            efectos.append(f"veneno {jugador.veneno.magnitud}/pulso hasta t={jugador.veneno.fin}")
        if jugador.efecto_velocidad is not None:
            efecto = jugador.efecto_velocidad
            efectos.append(f"velocidad {efecto.magnitud:+d} hasta t={efecto.fin}")
        if jugador.antorcha is not None:
            efectos.append(f"antorcha hasta t={jugador.antorcha.fin}")
        _imprimir("Efectos: " + (" | ".join(efectos) if efectos else "ninguno"))

        # Últimos 20 mensajes, separados por turnos.
        _imprimir(LINEA_SIMPLE)
        _imprimir("Bitácora (últimos mensajes):")
        for clase, tiempo, texto in lineas_bitacora(juego):
            if clase == LINEA_MENSAJE:
                _imprimir(f"  [t={tiempo}] {texto}")
            elif clase in (LINEA_TU_TURNO, LINEA_ENEMIGOS):
                _imprimir(f"  -- {texto} --")
            else:
                _imprimir(f"  {texto}")
        _imprimir(LINEA_SIMPLE)
        if not juego.esta_terminada():
            _imprimir(f"Es tu turno (t={juego.reloj}). ¿Qué haces?")
            _imprimir(f"{TECLAS} | ayuda")

    def mostrar_inventario(
        self, juego: Juego, vista: list[InstanciaObjeto] | None = None, criterio: str | None = None
    ) -> None:
        """Orden real con el cursor marcado, o una vista ordenada si se pasa."""
        jugador = juego.jugador
        inventario = jugador.inventario
        objetos = vista if vista is not None else [objeto for objeto in inventario]
        titulo = f"Inventario ordenado por {criterio}" if vista is not None else "Inventario (orden real)"
        _imprimir(LINEA_SIMPLE)
        _imprimir(f"{titulo}: {len(inventario)}/{inventario.capacidad}")
        if not objetos:
            _imprimir("  (vacío)")
        actual = inventario.actual()
        for i in range(len(objetos)):
            objeto = objetos[i]
            marca = ">" if objeto is actual and vista is None else " "
            equipado = " [equipado]" if objeto is jugador.arma or objeto is jugador.armadura else ""
            _imprimir(f" {marca}{i + 1}) {self._describir_objeto(juego, objeto)}{equipado}")
        if vista is not None:
            _imprimir("  (los números de F siguen el orden REAL: míralo con I)")
        elif objetos:
            _imprimir("  F k = usar, equipar o soltar el objeto k  |  sig / ant = mover el cursor >")

    def mostrar_resultado(self, resultado: ResultadoAccion) -> None:
        if not resultado.aceptada and resultado.motivo:
            self.mostrar_error(resultado.motivo)

    def mostrar_info(self, texto: str) -> None:
        _imprimir(texto)

    def mostrar_error(self, texto: str) -> None:
        _imprimir(f"(!) {texto}")

    def mostrar_ayuda(self) -> None:
        _imprimir(AYUDA)

    def mostrar_fin(self, juego: Juego, reporte_red: str) -> None:
        resumen = juego.resumen()
        _imprimir(LINEA_DOBLE)
        if resumen.estado is EstadoPartida.VICTORIA:
            _imprimir(" ¡VICTORIA! Escapaste de la cripta.")
        elif resumen.estado is EstadoPartida.DERROTA:
            _imprimir(" DERROTA. La cripta se queda con otro aventurero.")
        else:
            _imprimir(" Partida terminada sin resolver.")
        _imprimir(LINEA_DOBLE)
        _imprimir(f"Jugador: {resumen.nombre_jugador}")
        _imprimir(f"Cripta: {resumen.cripta_id} (versión {resumen.version_cripta})")
        _imprimir(f"Acciones ejecutadas: {resumen.acciones_ejecutadas}")
        _imprimir(f"Enemigos derrotados: {resumen.enemigos_derrotados}")
        _imprimir(f"Tiempo final del reloj: {resumen.tiempo_final}")
        if reporte_red:
            _imprimir(LINEA_SIMPLE)
            _imprimir(reporte_red)

    def mostrar_puntajes(self, registros: list[RegistroPuntaje]) -> None:
        _imprimir(LINEA_SIMPLE)
        if not registros:
            _imprimir("Todavía no hay puntajes.")
            return
        _imprimir(f"{'#':>3} {'Jugador':<16} {'Cripta':<12} {'Resultado':<10} {'Acciones':>8} {'Derrot.':>7} {'Reloj':>8}")
        for i in range(len(registros)):
            r = registros[i]
            _imprimir(
                f"{i + 1:>3} {r.nombre[:16]:<16} {r.cripta_id[:12]:<12} {r.resultado:<10} "
                f"{r.acciones:>8} {r.enemigos_derrotados:>7} {r.tiempo_final:>8}"
            )

    def cerrar(self) -> None:
        """La consola no tiene nada que cerrar (la ventana sí)."""

    # --- internos -----------------------------------------------------------------

    def _leer(self, mensaje: str) -> str:
        return self._entrada(mensaje).strip()

    def _preguntar(self, titulo: str, opciones: list[str], marcas: list[str] | None = None) -> int | None:
        """Menú numerado. Devuelve la posición elegida (desde 0) o None si se cancela."""
        _imprimir(titulo)
        for i in range(len(opciones)):
            _imprimir(f"  {i + 1}) {opciones[i]}")
        _imprimir("  0) Cancelar")
        while True:
            try:
                respuesta = self._leer("Elige un número: ")
            except EOFError:
                return None
            if respuesta in ("", "0"):
                self.mostrar_info("Cancelado.")
                return None
            if respuesta.isdigit() and 1 <= int(respuesta) <= len(opciones):
                return int(respuesta) - 1
            self.mostrar_error(f"Escribe un número del 1 al {len(opciones)} (0 para cancelar).")
