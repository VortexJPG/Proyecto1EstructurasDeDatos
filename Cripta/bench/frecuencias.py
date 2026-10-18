"""Frecuencia real de las operaciones (Documento de Decisiones, §8 punto 1).  [A y B]

§8 pide decir "qué operaciones ejecuta realmente su programa y con qué
frecuencia medida". Aquí el bot (``bench/bot.py``) juega las criptas reales de
``datos_ejemplo/`` (sin red) y una cripta sintética grande, mientras se cuentan
las llamadas a las operaciones importantes. Los métodos se envuelven SOLO
durante la medición y después se restauran: el programa normal no cuenta nada.

También se guarda la secuencia de fichas que pide el modelo (la "traza"), que
``bench_datos`` usa para comparar políticas de desalojo de la caché (§4.4).
"""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from typing import Any, Callable

from cripta.adaptadores.cache_catalogo import CacheCatalogo
from cripta.adaptadores.fuente_datos import EstadisticasRed, FuenteDatos
from cripta.adaptadores.fuente_offline import FuenteOffline
from cripta.bench import bot
from cripta.controlador.controlador import Controlador, OpcionesEjecucion
from cripta.controlador.precarga import PlanificadorPrecarga
from cripta.estructuras import ordenamiento
from cripta.estructuras.ordenamiento import ordenar
from cripta.estructuras.tabla_ordenada import TablaOrdenada
from cripta.modelo.acciones import Accion, TipoAccion
from cripta.modelo.comportamiento import IAEnemigos
from cripta.modelo.eventos import Agenda
from cripta.modelo.historial import Historial
from cripta.modelo.inventario import Inventario
from cripta.modelo.mensajes import BitacoraMensajes

DATOS_EJEMPLO = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "datos_ejemplo")
def criptas_reales() -> list[str]:
    """Ids de las criptas que hay en ``datos_ejemplo/`` (no se escriben en el código, §9)."""
    return [cripta.id for cripta in FuenteOffline(DATOS_EJEMPLO).listar_criptas()]


def cripta_mas_grande() -> str:
    """Id de la cripta con más salas de ``datos_ejemplo/`` (para medir el guardado con una partida real)."""
    mayor = None
    for cripta in FuenteOffline(DATOS_EJEMPLO).listar_criptas():
        if mayor is None or cripta.salas > mayor.salas:
            mayor = cripta
    if mayor is None:
        raise RuntimeError("datos_ejemplo/ no tiene criptas")
    return mayor.id
DECISIONES_BOT = 400


# Métodos originales de TablaOrdenada: el contador los usa directamente porque,
# durante la medición, ``TablaOrdenada.obtener`` está envuelto para contar llamadas
# (si el contador lo usara, se contaría a sí mismo sin fin).
_OBTENER = TablaOrdenada.obtener
_INSERTAR = TablaOrdenada.insertar


class Contador:
    """Contadores con nombre, en el orden en que aparecen (TablaOrdenada + list)."""

    def __init__(self) -> None:
        self._valores: TablaOrdenada[str, int] = TablaOrdenada()
        self._orden: list[str] = []

    def _leer(self, nombre: str) -> int | None:
        return _OBTENER(self._valores, nombre, None)

    def sumar(self, nombre: str, cantidad: int = 1) -> None:
        actual = self._leer(nombre)
        if actual is None:
            self._orden.append(nombre)
            actual = 0
        _INSERTAR(self._valores, nombre, actual + cantidad)

    def maximo(self, nombre: str, valor: int) -> None:
        actual = self._leer(nombre)
        if actual is None:
            self._orden.append(nombre)
            actual = 0
        if valor > actual:
            _INSERTAR(self._valores, nombre, valor)

    def valor(self, nombre: str) -> int:
        actual = self._leer(nombre)
        return actual if actual is not None else 0

    def nombres(self) -> list[str]:
        return list(self._orden)


@dataclass
class Medicion:
    nombre: str
    decisiones: int
    contador: Contador
    datos_red: EstadisticasRed | None = None
    salas_visitadas: int = 0
    salas_totales: int = 0
    traza_fichas: list[str] = field(default_factory=list)


class FuenteContadora(FuenteDatos):
    """Envuelve otra fuente y cuenta solicitudes como lo haría el cliente HTTP."""

    def __init__(self, fuente: FuenteDatos, contador: Contador) -> None:
        self._fuente = fuente
        self._contador = contador
        self._presupuesto: int | None = None

    def _contar(self, operacion: str) -> None:
        self._contador.sumar("red: solicitudes")
        self._contador.sumar(f"red: {operacion}")

    def listar_criptas(self):
        self._contar("listar_criptas")
        return self._fuente.listar_criptas()

    def datos_cripta(self, cripta_id):
        self._contar("datos_cripta")
        return self._fuente.datos_cripta(cripta_id)

    def pagina_esqueleto(self, cripta_id, pagina):
        self._contar("pagina_esqueleto")
        return self._fuente.pagina_esqueleto(cripta_id, pagina)

    def contenido(self, cripta_id, salas):
        self._contar("contenido")
        self._contador.sumar("red: salas pedidas", len(salas))
        return self._fuente.contenido(cripta_id, salas)

    def catalogo(self, ids):
        self._contar("catalogo")
        return self._fuente.catalogo(ids)

    def version_cripta(self, cripta_id):
        self._contar("version_cripta")
        return self._fuente.version_cripta(cripta_id)

    def version_catalogo(self):
        self._contar("version_catalogo")
        return self._fuente.version_catalogo()

    def establecer_presupuesto(self, presupuesto: int) -> None:
        self._presupuesto = presupuesto

    def solicitudes_restantes(self) -> int | None:
        if self._presupuesto is None:
            return None
        return self._presupuesto - self._contador.valor("red: solicitudes")

    def estadisticas(self) -> EstadisticasRed:
        return EstadisticasRed(self._contador.valor("red: solicitudes"), self._presupuesto)


class _Instrumentos:
    """Envuelve métodos de varias clases para contar sus llamadas."""

    def __init__(self, contador: Contador, traza: list[str]) -> None:
        self._contador = contador
        self._traza = traza
        self._originales: list[tuple[Any, str, Any]] = []

    def _envolver(self, objeto: Any, metodo: str, nombre: str,
                  despues: Callable[[Any, tuple, Any], None] | None = None) -> None:
        original = getattr(objeto, metodo)
        contador = self._contador

        def envoltura(*args, **kwargs):
            contador.sumar(nombre)
            resultado = original(*args, **kwargs)
            if despues is not None:
                despues(args[0] if args else None, args, resultado)
            return resultado

        self._originales.append((objeto, metodo, original))
        setattr(objeto, metodo, envoltura)

    def activar(self) -> None:
        c = self._contador
        traza = self._traza
        self._envolver(Agenda, "programar", "agenda: programar",
                       lambda agenda, a, r: c.maximo("agenda: máximo de eventos pendientes", len(agenda)))
        self._envolver(Agenda, "extraer_siguiente", "agenda: extraer el siguiente")
        self._envolver(Agenda, "ver_siguiente", "agenda: ver el siguiente")
        self._envolver(Agenda, "cancelar", "agenda: cancelar")
        self._envolver(TablaOrdenada, "obtener", "tabla ordenada: buscar")
        self._envolver(TablaOrdenada, "contiene", "tabla ordenada: buscar")  # también es una búsqueda
        self._envolver(TablaOrdenada, "insertar", "tabla ordenada: insertar")
        self._envolver(CacheCatalogo, "obtener", "caché: obtener ficha",
                       lambda cache, a, r: traza.append(a[1]))
        self._envolver(CacheCatalogo, "fijar", "caché: fijar", lambda cache, a, r: traza.append(a[1]))
        self._envolver(CacheCatalogo, "liberar", "caché: liberar")
        self._envolver(Inventario, "agregar", "inventario: agregar")
        self._envolver(Inventario, "quitar", "inventario: quitar")
        self._envolver(Inventario, "mover_al_frente", "inventario: mover al frente")
        self._envolver(Inventario, "vista_ordenada", "inventario: vista ordenada")
        self._envolver(Historial, "registrar", "historial: cambios registrados")
        self._envolver(Historial, "retroceder", "historial: retrocesos")
        self._envolver(IAEnemigos, "elegir_sala_por_rastro", "rastro: decisiones de rastreador")
        self._envolver(BitacoraMensajes, "agregar", "bitácora: mensajes")
        self._envolver(ordenamiento, "_elegir", "ordenamiento: llamadas",
                       lambda _, a, r: (c.sumar("ordenamiento: elementos ordenados", len(a[0])),
                                        c.sumar(f"ordenamiento: eligió {r}")))
        self._envolver(PlanificadorPrecarga, "asegurar", "precarga: asegurar (antes de moverse)")
        self._envolver(PlanificadorPrecarga, "planificar", "precarga: planificar")

    def desactivar(self) -> None:
        for objeto, metodo, original in reversed(self._originales):
            setattr(objeto, metodo, original)
        self._originales = []


def _medir_cripta_real(cripta_id: str) -> Medicion:
    contador = Contador()
    traza: list[str] = []
    directorio = tempfile.mkdtemp(prefix="cripta_frec_")
    instrumentos = _Instrumentos(contador, traza)
    try:
        fuente = FuenteContadora(FuenteOffline(DATOS_EJEMPLO), contador)
        controlador = Controlador(fuente, OpcionesEjecucion(directorio_datos=directorio, cache_size=25), None)
        instrumentos.activar()
        # "Sala ya pedida al decidir moverse": mide si la precarga se adelantó.
        original_asegurar = PlanificadorPrecarga.asegurar

        def asegurar_contando(planificador, sala_id):
            if sala_id in planificador._solicitadas or sala_id in planificador._incorporados:
                contador.sumar("precarga: sala ya pedida al moverse")
            else:
                contador.sumar("precarga: sala NO pedida al moverse")
            return original_asegurar(planificador, sala_id)

        PlanificadorPrecarga.asegurar = asegurar_contando
        try:
            fuente.listar_criptas()
            controlador.preparar_cripta(cripta_id)
            controlador._datos.jugador.vida_max = 100_000  # el bot explora; no importa ganar
            controlador.iniciar_partida("Bot", 1, registrar_replay=False)
            decisiones = bot.jugar(controlador, DECISIONES_BOT, semilla=1)
            controlador.cerrar_recursos()
        finally:
            PlanificadorPrecarga.asegurar = original_asegurar
        juego = controlador.juego
        visitadas = 0
        for sala in juego.mapa:
            if sala.visitada:
                visitadas += 1
        cache = controlador._catalogo
        contador.sumar("caché: aciertos en memoria", cache.estadisticas().aciertos_memoria)
        contador.sumar("caché: recuperadas de disco", cache.estadisticas().aciertos_disco)
        contador.sumar("caché: pedidas por red", cache.estadisticas().fallos_red)
        return Medicion(cripta_id, decisiones, contador, fuente.estadisticas(), visitadas, len(juego.mapa), traza)
    finally:
        instrumentos.desactivar()
        shutil.rmtree(directorio, ignore_errors=True)


def _medir_cripta_pesada() -> Medicion:
    from cripta.bench.bench_modelo import _juego_cuadricula

    contador = Contador()
    instrumentos = _Instrumentos(contador, [])
    juego = _juego_cuadricula(900, 500, semilla=5)
    instrumentos.activar()
    try:
        esperar = Accion(TipoAccion.ESPERAR)
        decisiones = 0
        for _ in range(200):
            if juego.esta_terminada():
                break
            juego.ejecutar_accion(esperar)
            decisiones += 1
    finally:
        instrumentos.desactivar()
    return Medicion("sintética 900/500", decisiones, contador, None, 0, len(juego.mapa))


_cache_mediciones: list[Medicion] | None = None


def medir() -> list[Medicion]:
    """Mide una sola vez por ejecución (los benchmarks reutilizan el resultado)."""
    global _cache_mediciones
    if _cache_mediciones is None:
        _cache_mediciones = [_medir_cripta_real(cripta_id) for cripta_id in criptas_reales()]
        _cache_mediciones.append(_medir_cripta_pesada())
    return _cache_mediciones


def traza_fichas_reales() -> list[str]:
    """Fichas pedidas por el modelo jugando las 4 criptas seguidas (catálogo compartido)."""
    traza: list[str] = []
    for medicion in medir():
        traza.extend(medicion.traza_fichas)
    return traza


_GRUPOS: tuple[str, ...] = ("agenda", "historial", "rastro", "bitácora", "inventario", "ordenamiento",
                            "tabla ordenada", "caché", "precarga", "red")


def _orden_de_fila(nombre: str) -> tuple[int, str]:
    for posicion in range(len(_GRUPOS)):
        if nombre.startswith(_GRUPOS[posicion]):
            return posicion, nombre
    return len(_GRUPOS), nombre


def imprimir_frecuencias() -> None:
    mediciones = medir()
    print()
    print("Frecuencia de operaciones (total / por decisión del jugador). El bot juega sin red.")
    encabezado = f"{'Operación':<44}"
    for medicion in mediciones:
        encabezado += f"{medicion.nombre[:16]:>20}"
    print(encabezado)
    resumen = f"{'decisiones del jugador':<44}"
    for medicion in mediciones:
        resumen += f"{medicion.decisiones:>20}"
    print(resumen)
    salas = f"{'salas visitadas / total':<44}"
    for medicion in mediciones:
        salas += f"{(str(medicion.salas_visitadas) + '/' + str(medicion.salas_totales)) if medicion.datos_red else '-':>20}"
    print(salas)
    nombres: list[str] = []
    for medicion in mediciones:
        for nombre in medicion.contador.nombres():
            if nombre not in nombres:
                nombres.append(nombre)
    nombres = ordenar(nombres, clave=_orden_de_fila)
    for nombre in nombres:
        fila = f"{nombre:<44}"
        for medicion in mediciones:
            total = medicion.contador.valor(nombre)
            if "máximo" in nombre or nombre.startswith("red:") or nombre.startswith("caché: ") and "obtener" not in nombre \
                    and "fijar" not in nombre and "liberar" not in nombre or nombre.startswith("precarga: sala"):
                fila += f"{total:>20}"
            else:
                por_decision = total / medicion.decisiones if medicion.decisiones else 0
                fila += f"{f'{total} ({por_decision:.1f})':>20}"
        print(fila)
