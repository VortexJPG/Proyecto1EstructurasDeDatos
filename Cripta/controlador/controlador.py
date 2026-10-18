"""Controlador principal.                                            [Persona B]

Traduce comandos en operaciones del modelo y coordina red, caché, precarga,
replay y guardado. Funciona SIN vista (``vista=None``) para --replay.

Preparación de una cripta, cuidando el presupuesto (§5.1):
    1. ``datos_cripta`` (trae la versión: no hace falta pedir /version aparte)
       → ``fuente.establecer_presupuesto(...)``.
    2. Esqueleto: de disco si la versión coincide; si no, todas las páginas.
    3. ``version_catalogo`` → ``CacheCatalogo.validar_version``.
    4. ``Mapa.construir`` y ``PlanificadorPrecarga``.
    5. Asegurar el contenido (y las fichas) de la sala inicial; ``juego.iniciar()``.

Antes de confirmar un MOVER: ``juego.sala_destino`` → ``precarga.asegurar``.
Después de cada acción: escribir en el replay, ``precarga.planificar`` e
``incorporar_disponibles``.

Decisión sobre el replay al cargar una partida: la bitácora de la partida en
curso se CIERRA (un log siempre empieza en t=0 con su semilla, así que no
puede continuar desde un archivo de guardado).
"""

from __future__ import annotations

import gc
import os
import random
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from cripta.adaptadores.almacen_disco import AlmacenCatalogo, AlmacenCripta
from cripta.adaptadores.bitacora_replay import EncabezadoReplay, EscritorReplay
from cripta.adaptadores.cache_catalogo import CacheCatalogo
from cripta.adaptadores.fuente_datos import ErrorFuenteDatos, FuenteDatos
from cripta.adaptadores.guardado import GuardadoBinario, GuardadoJSON
from cripta.adaptadores.puntajes import RegistroPuntaje, TablaPuntajes
from cripta.controlador.comandos import ComandoUsuario, TipoComando
from cripta.controlador.precarga import PlanificadorPrecarga
from cripta.modelo.acciones import TipoAccion
from cripta.modelo.juego import Juego
from cripta.modelo.mapa import Mapa

if TYPE_CHECKING:
    from cripta.modelo.acciones import Accion, ResultadoAccion
    from cripta.modelo.datos import ContenidoSala, DatosCripta
    from cripta.modelo.guardable import EstadoGuardable
    from cripta.vista.vista_consola import VistaConsola
    from cripta.vista.vista_grafica import VistaGrafica


@dataclass(slots=True)
class OpcionesEjecucion:
    directorio_datos: str
    cache_size: int
    offline: str | None = None  # directorio del paquete offline
    cripta_id: str | None = None  # si se pasa, se evita GET /criptas
    semilla: int | None = None  # None → se genera una y se escribe en el log
    nombre_jugador: str | None = None


class Controlador:
    def __init__(
        self, fuente: FuenteDatos, opciones: OpcionesEjecucion, vista: VistaConsola | VistaGrafica | None = None
    ) -> None:
        self.fuente = fuente
        self.opciones = opciones
        self.vista = vista
        self.directorio_datos = opciones.directorio_datos
        self.cache_size = opciones.cache_size
        os.makedirs(self.directorio_datos, exist_ok=True)
        self._juego: Juego | None = None
        self._mapa: Mapa | None = None
        self._datos: DatosCripta | None = None
        self._catalogo: CacheCatalogo | None = None
        self._almacen_cripta: AlmacenCripta | None = None
        self.almacen_catalogo = AlmacenCatalogo(os.path.join(self.directorio_datos, "catalogo"))
        self._precarga: PlanificadorPrecarga | None = None
        self._escritor: EscritorReplay | None = None
        self._ruta_log: str | None = None
        self._cripta_id = opciones.cripta_id
        self._version_catalogo: str | None = None
        self._semilla: int | None = None

    @property
    def juego(self) -> Juego | None:
        return self._juego

    # --- flujo interactivo --------------------------------------------------------

    def ejecutar_interactivo(self) -> None:
        """Elegir cripta, iniciar partida y atender comandos hasta salir o terminar."""
        if self._cripta_id is None:
            criptas = self.fuente.listar_criptas()
            if not criptas:
                raise ErrorFuenteDatos("listar_criptas", "no hay criptas disponibles")
            if self.vista is not None:
                self._cripta_id = self.vista.elegir_cripta(criptas)
            else:
                self._cripta_id = criptas[0].id
        self.preparar_cripta(self._cripta_id)
        nombre = self.opciones.nombre_jugador
        if nombre is None:
            nombre = self.vista.pedir_nombre() if self.vista is not None else "Jugador"
        self.iniciar_partida(nombre, self.opciones.semilla, True)
        if self.vista is None:
            self.finalizar()
            return
        self.vista.mostrar_info(f"Partida iniciada (semilla {self._semilla}).")
        if self._ruta_log is not None:
            self.vista.mostrar_info(f"Bitácora de replay: {self._ruta_log}")
        self.vista.mostrar_estado(self._juego)
        while self._juego is not None and not self._juego.esta_terminada():
            comando = self.vista.pedir_comando(self._juego)
            if not self.procesar_comando(comando):
                break
        self.finalizar()

    def procesar_comando(self, comando: ComandoUsuario) -> bool:
        """Ejecuta un comando. Devuelve False si la sesión debe terminar."""
        juego = self._juego
        vista = self.vista
        if juego is None:
            return True
        tipo = comando.tipo
        if tipo is TipoComando.ACCION:
            if comando.accion is None:
                return True
            try:
                resultado = self.ejecutar_accion(comando.accion)
            except ErrorFuenteDatos as exc:
                if vista is not None:
                    vista.mostrar_error(f"No se pudo completar la acción: {exc}")
                return True
            if vista is not None:
                if resultado.aceptada:
                    vista.mostrar_estado(self._juego)
                else:
                    vista.mostrar_resultado(resultado)
            return True
        if vista is None:
            return tipo is not TipoComando.SALIR
        if tipo is TipoComando.INVENTARIO_SIGUIENTE:
            juego.jugador.inventario.avanzar()
            vista.mostrar_inventario(juego)
        elif tipo is TipoComando.INVENTARIO_ANTERIOR:
            juego.jugador.inventario.retroceder()
            vista.mostrar_inventario(juego)
        elif tipo is TipoComando.VER_INVENTARIO:
            vista.mostrar_inventario(juego)
        elif tipo is TipoComando.VISTA_ORDENADA:
            criterio = comando.argumento or "nombre"
            try:
                vista.mostrar_inventario(juego, juego.vista_inventario(criterio), criterio)
            except ValueError as exc:
                vista.mostrar_error(str(exc))
        elif tipo is TipoComando.GUARDAR:
            ruta = comando.argumento or os.path.join(self.directorio_datos, "partida_guardada.sav")
            try:
                self.guardar_partida(ruta)
                vista.mostrar_info(f"Partida guardada en {ruta} (y una copia JSON en {ruta}.json para comparar).")
            except (OSError, ValueError) as exc:
                vista.mostrar_error(f"No se pudo guardar: {exc}")
        elif tipo is TipoComando.CARGAR:
            ruta = comando.argumento or os.path.join(self.directorio_datos, "partida_guardada.sav")
            try:
                self.cargar_partida(ruta)
                vista.mostrar_info(f"Partida cargada desde {ruta}. La bitácora de replay se cerró.")
                vista.mostrar_estado(self._juego)
            except Exception as exc:  # formato, versiones o archivo: se informa y se sigue jugando
                vista.mostrar_error(f"No se pudo cargar: {exc}")
        elif tipo is TipoComando.PUNTAJES:
            tabla = TablaPuntajes(os.path.join(self.directorio_datos, "puntajes.json"))
            vista.mostrar_puntajes(tabla.ordenados("tiempo"))
        elif tipo is TipoComando.AYUDA:
            vista.mostrar_ayuda()
        elif tipo is TipoComando.SALIR:
            return False
        return True

    # --- partida ------------------------------------------------------------------

    def preparar_cripta(self, cripta_id: str) -> None:
        """Pasos 1-4 de la preparación (ver docstring del módulo)."""
        self._cripta_id = cripta_id
        self._datos = self.fuente.datos_cripta(cripta_id)
        self.fuente.establecer_presupuesto(self._datos.presupuesto_solicitudes)
        self._almacen_cripta = AlmacenCripta(self.directorio_datos, cripta_id)
        self._almacen_cripta.validar_version(self._datos.version)
        # esqueleto
        esqueleto = self._almacen_cripta.cargar_esqueleto()
        if esqueleto is None:
            esqueleto = []
            for pagina in range(1, self._datos.paginas + 1):
                esqueleto.extend(self.fuente.pagina_esqueleto(cripta_id, pagina).salas)
            self._almacen_cripta.guardar_esqueleto(esqueleto)
            self._almacen_cripta.guardar_datos_generales(self._datos)
        self._mapa = Mapa.construir(self._datos, esqueleto)
        # catálogo
        self._catalogo = CacheCatalogo(self.fuente, self.almacen_catalogo, self.cache_size)
        self._version_catalogo = self.fuente.version_catalogo()
        self._catalogo.validar_version(self._version_catalogo)
        # precarga
        mapa = self._mapa
        catalogo = self._catalogo

        def incorporar(contenido: ContenidoSala) -> None:
            mapa.incorporar_contenido(contenido, catalogo)

        self._precarga = PlanificadorPrecarga(
            self.fuente, cripta_id, self._almacen_cripta, self._catalogo, self._mapa.vecinos, incorporar
        )
        # asegurar sala inicial
        self._precarga.asegurar(self._datos.sala_inicial)
        self._precarga.planificar(self._datos.sala_inicial)

    def iniciar_partida(self, nombre_jugador: str, semilla: int | None, registrar_replay: bool = True) -> None:
        """Paso 5 + abrir el ``EscritorReplay``."""
        if semilla is None:
            semilla = random.randrange(2**31)  # solo ELIGE la semilla; el juego usa su propio Random
        self._semilla = semilla
        datos, mapa, catalogo = self._datos, self._mapa, self._catalogo
        if datos is None or mapa is None or catalogo is None:
            raise RuntimeError("Hay que preparar la cripta antes de iniciar la partida")
        self._juego = Juego(datos, mapa, catalogo, semilla, nombre_jugador)
        self._juego.iniciar()
        _congelar_objetos_cargados()
        if registrar_replay:
            encabezado = EncabezadoReplay(
                cripta_id=datos.id,
                version_cripta=datos.version,
                version_catalogo=self._version_catalogo or "",
                semilla=semilla,
                nombre_jugador=nombre_jugador,
            )
            carpeta = os.path.join(self.directorio_datos, "replays")
            os.makedirs(carpeta, exist_ok=True)
            # El nombre del archivo usa la hora real solo para no pisar logs anteriores;
            # no influye en la simulación.
            self._ruta_log = os.path.join(carpeta, f"partida_{datos.id}_{time.strftime('%Y%m%d-%H%M%S')}.log")
            self._escritor = EscritorReplay(self._ruta_log, encabezado)

    def ejecutar_accion(self, accion: Accion) -> ResultadoAccion:
        """Núcleo compartido por el modo interactivo y el replay.

        Si el modelo responde ``requiere_sala``, asegurar ese contenido y
        reintentar la misma acción.
        """
        juego = self._juego
        if juego is None:
            raise RuntimeError("No hay una partida en curso")
        # Antes de mover, traer el contenido de la sala destino (§4.2).
        if accion.tipo is TipoAccion.MOVER and self._precarga is not None:
            destino = juego.sala_destino(accion.direccion or "")
            if destino is not None:
                self._precarga.asegurar(destino.id)
        resultado = juego.ejecutar_accion(accion)
        if resultado.requiere_sala is not None and self._precarga is not None:
            self._precarga.asegurar(resultado.requiere_sala)
            resultado = juego.ejecutar_accion(accion)  # un reintento
        if resultado.aceptada and self._escritor is not None:
            self._escritor.registrar(accion)
        self._despues_de_accion()
        return resultado

    def guardar_partida(self, ruta: str) -> None:
        juego = self._juego
        if juego is None:
            raise ValueError("No hay una partida en curso")
        estado = juego.exportar_estado(self._version_catalogo or "")
        GuardadoBinario().guardar(ruta, estado)
        GuardadoJSON().guardar(ruta + ".json", estado)

    def cargar_partida(self, ruta: str) -> None:
        """Valida versiones de cripta y catálogo antes de reconstruir."""
        estado = GuardadoBinario().cargar(ruta)
        if self._datos is None or self._mapa is None or self._catalogo is None or self._precarga is None:
            raise RuntimeError("Hay que preparar la cripta antes de cargar una partida")
        if estado.cripta_id != self._datos.id or estado.version_cripta != self._datos.version:
            raise ErrorFuenteDatos("cargar_partida", "la partida es de otra cripta o de otra versión")
        if self._version_catalogo is not None and estado.version_catalogo != self._version_catalogo:
            raise ErrorFuenteDatos("cargar_partida", "versión de catálogo incompatible")
        # Las fichas de todo lo que aparece en el estado deben estar resueltas.
        self._catalogo.registrar_necesarios(_tipos_del_estado(estado))
        self._catalogo.resolver_pendientes()
        # La partida anterior suelta sus fichas fijadas antes de ser reemplazada.
        if self._juego is not None:
            self._juego.liberar_fijaciones()
        self._juego = Juego.desde_estado(estado, self._datos, self._mapa, self._catalogo)
        _congelar_objetos_cargados()
        self._precarga.reiniciar([sala.id for sala in estado.salas if sala.contenido_cargado])
        if self._escritor is not None:
            self._escritor.cerrar()
            self._escritor = None

    def finalizar(self) -> None:
        """Cierra precarga y replay, registra el puntaje y muestra el reporte de §5.1:
        solicitudes realizadas, presupuesto, aciertos y fallos de caché."""
        self.cerrar_recursos()
        if self._juego is not None:
            try:
                registro = RegistroPuntaje.desde_resumen(self._juego.resumen())
                TablaPuntajes(os.path.join(self.directorio_datos, "puntajes.json")).agregar(registro)
            except OSError as exc:
                if self.vista is not None:
                    self.vista.mostrar_error(f"No se pudo guardar el puntaje: {exc}")
            if self.vista is not None:
                self.vista.mostrar_fin(self._juego, self.reporte_red())

    def cerrar_recursos(self) -> None:
        """Cierra el hilo de precarga y la bitácora de replay (sin registrar puntaje)."""
        if self._precarga is not None:
            try:
                self._precarga.cerrar()
            except ErrorFuenteDatos:
                pass  # una precarga anticipada que falló ya no importa al terminar
        if self._escritor is not None:
            self._escritor.cerrar()
            self._escritor = None

    def reporte_red(self) -> str:
        stats = self.fuente.estadisticas()
        texto = (
            f"Solicitudes: {stats.solicitudes_realizadas}/"
            f"{stats.presupuesto if stats.presupuesto is not None else '?'}"
            f" | 429: {stats.respuestas_429} | errores: {stats.errores}"
        )
        if self._catalogo is not None:
            st = self._catalogo.estadisticas()
            texto += (
                f"\nCaché de catálogo: aciertos memoria={st.aciertos_memoria}, disco={st.aciertos_disco}, "
                f"fallos (red)={st.fallos_red}, desalojos={self._catalogo.cache.desalojos}"
            )
        if self._ruta_log is not None:
            texto += f"\nBitácora de replay: {self._ruta_log}"
        return texto

    # --- internos -----------------------------------------------------------------

    def _despues_de_accion(self) -> None:
        """Precarga anticipada; un fallo de red aquí no detiene el juego."""
        if self._precarga is None or self._juego is None:
            return
        try:
            self._precarga.planificar(self._juego.jugador.sala.id)
            self._precarga.incorporar_disponibles()
        except ErrorFuenteDatos as exc:
            if self.vista is not None:
                self.vista.mostrar_error(f"Precarga: {exc}")


def _congelar_objetos_cargados() -> None:
    """Deja lo ya cargado fuera de las revisiones del recolector de basura de Python.

    Cada tanto, Python revisa TODOS los objetos para ver cuáles ya no se usan.
    El mapa, las salas y los enemigos de la cripta no se descartan durante la
    partida, pero igual se revisaban, y esa pausa era lo que más pesaba en el
    peor ciclo de §5.2 (unos 8 ms con 900 salas). ``gc.freeze`` los saca de
    esas revisiones; lo que se crea después (eventos, cambios del historial)
    se sigue revisando normal. Antes se hace ``unfreeze``, para que lo de una
    partida anterior (por ejemplo, al cargar otra) sí se pueda liberar.
    """
    gc.unfreeze()
    gc.collect()
    gc.freeze()


def _tipos_del_estado(estado: EstadoGuardable) -> list[str]:
    """Ids de catálogo que aparecen en una partida guardada."""
    tipos = [objeto.tipo for objeto in estado.jugador.inventario]
    for sala in estado.salas:
        tipos.extend(objeto.tipo for objeto in sala.objetos_suelo)
        tipos.extend(trampa.tipo for trampa in sala.trampas)
        tipos.extend(enemigo.tipo for enemigo in sala.enemigos)
    return tipos
