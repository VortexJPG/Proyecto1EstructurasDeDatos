"""Fachada del modelo: estado de la partida y bucle de eventos.     [Persona A]

Es la ÚNICA clase del modelo que usa el controlador para jugar.

Flujo de una decisión del jugador (``ejecutar_accion``):
    1. Validar SIN modificar nada. Inválida → rechazada; no consume tiempo ni
       abre intervalo (Apéndice B: inventario lleno, puerta sin llave...).
    2. MOVER hacia una sala sin contenido → rechazada con ``requiere_sala``;
       el controlador trae el contenido y reintenta. La espera real nunca
       mueve el reloj (§2.4).
    3. Abrir intervalo en el historial (§2.11) y guardar el estado del azar.
    4. Sacar el TURNO_JUGADOR de la agenda y aplicar la acción.
    5. Refrescar el rastro de la sala actual (Apéndice B) y contar la acción.
    6. Programar el próximo turno: max(1, costo * 100 // velocidad).
    7. Si se movió: activar enemigos dormidos en orden ascendente de id de
       instancia, disparar trampas armadas, revisar victoria (§2.4, §2.10,
       §2.12). El turno del jugador se programa ANTES que el de los enemigos
       recién activados: si empatan en tiempo, el jugador va primero.
    8. ``_avanzar_hasta_decision``: ejecutar eventos hasta que el próximo sea
       otra vez el TURNO_JUGADOR (o termine la partida).
    9. Cerrar el intervalo del historial.
Si algo falla a la mitad, el intervalo abierto se revierte: la acción es
atómica (o pasa completa o no pasa).

Regla para el retroceso: TODA mutación del estado de juego pasa por
``_asignar`` (u otro helper que registre un ``Cambio``). Una mutación que no
se registra es un bug de retroceso garantizado.

Determinismo: toda aleatoriedad usa ``self.azar`` = random.Random(semilla);
nunca el ``random`` global, la hora del sistema ni el orden de llegada de
respuestas HTTP (§2.3, §2.6). Las decisiones del juego recorren listas del
propio juego (salidas en orden N, S, E, O; enemigos de la sala; esqueleto).
Las tablas de búsqueda (``TablaOrdenada``) se recorren siempre en orden de
clave, igual en cada ejecución, pero se usan para encontrar cosas, no para
decidir en qué orden pasan.

Fichas en uso (§4.4): el modelo FIJA la ficha de cada enemigo activo y vivo,
de cada objeto del inventario y de cada objeto y trampa de la sala actual, y
la LIBERA cuando deja de estar en uso. ``_fijadas`` cuenta cuántas
referencias tiene el modelo de cada tipo; después de un retroceso o de cargar
una partida, ``_reconciliar_fijaciones`` las recalcula a partir del estado.

§5.2: con la cripta cargada, resolver el ciclo entre dos decisiones del
jugador debe tomar < 20 ms (medido en bench_modelo).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable

from cripta.constantes import (
    AZAR_DANO_MAX,
    AZAR_DANO_MIN,
    COSTO_ABRIR,
    COSTO_ACTIVACION_ENEMIGO,
    COSTO_ATACAR,
    COSTO_EQUIPAR,
    COSTO_ESPERAR,
    COSTO_MOVER,
    COSTO_RECOGER,
    COSTO_SOLTAR,
    COSTO_USAR,
    DANO_MINIMO,
    MAX_ACCIONES_REVERSIBLES,
    MENSAJES_VISIBLES,
    VELOCIDAD_REFERENCIA,
)
from cripta.estructuras.ordenamiento import ordenar
from cripta.estructuras.tabla_ordenada import TablaOrdenada
from cripta.modelo.acciones import Accion, ResultadoAccion, TipoAccion
from cripta.modelo.actores import Actor, Enemigo, Jugador
from cripta.modelo.comportamiento import IAEnemigos
from cripta.modelo.efectos import Efecto, GestorEfectos, TipoEfecto, ranura_de
from cripta.modelo.eventos import Agenda, Evento, TipoEvento
from cripta.modelo.guardable import (
    EstadoGuardable,
    RegistroEfecto,
    RegistroEnemigo,
    RegistroEvento,
    RegistroJugador,
    RegistroObjeto,
    RegistroPuerta,
    RegistroSala,
    RegistroTrampa,
)
from cripta.modelo.historial import (
    CambioAtributo,
    CambioEstadoAzar,
    CambioEventoCancelado,
    CambioEventoExtraido,
    CambioEventoProgramado,
    CambioInventario,
    CambioNodoAgregado,
    CambioNodoQuitado,
    Historial,
)
from cripta.modelo.inventario import Inventario
from cripta.modelo.mensajes import BitacoraMensajes
from cripta.modelo.objetos import ClaseObjeto, InstanciaObjeto, InstanciaTrampa, id_objeto_soltado
from cripta.modelo.puertos import FichaNoDisponible

if TYPE_CHECKING:
    from cripta.estructuras.lista_doble import NodoDoble
    from cripta.modelo.datos import DatosCripta
    from cripta.modelo.mapa import Mapa, Sala
    from cripta.modelo.puertos import ProveedorFichas

# Criterios aceptados por ``vista_inventario``.
CRITERIOS_INVENTARIO: tuple[str, ...] = ("peso", "valor", "nombre")

_NOMBRES_DIRECCION: tuple[tuple[str, str], ...] = (("N", "norte"), ("S", "sur"), ("E", "este"), ("O", "oeste"))


def nombre_direccion(direccion: str) -> str:
    """'N' → 'norte' (para mensajes)."""
    for letra, nombre in _NOMBRES_DIRECCION:
        if letra == direccion:
            return nombre
    return direccion


def _id_de(actor: Actor) -> str:
    """Clave de orden para activar enemigos: id de instancia (comparación de texto)."""
    return actor.id


class EstadoPartida(Enum):
    EN_CURSO = "en_curso"
    VICTORIA = "victoria"
    DERROTA = "derrota"


@dataclass(slots=True)
class ResumenPartida:
    """Datos para la tabla de puntajes (§2.12)."""

    nombre_jugador: str
    cripta_id: str
    version_cripta: str
    acciones_ejecutadas: int
    enemigos_derrotados: int
    tiempo_final: int
    estado: EstadoPartida


class Juego:
    """Estado completo de una partida y reglas de §2."""

    datos: DatosCripta
    mapa: Mapa
    fichas: ProveedorFichas
    semilla: int
    azar: random.Random
    reloj: int
    agenda: Agenda
    jugador: Jugador
    historial: Historial
    mensajes: BitacoraMensajes
    efectos: GestorEfectos
    ia: IAEnemigos
    estado: EstadoPartida
    objetos_generados: int  # contador de ids de objetos soltados (no se revierte)

    def __init__(
        self,
        datos: DatosCripta,
        mapa: Mapa,
        fichas: ProveedorFichas,
        semilla: int,
        nombre_jugador: str,
    ) -> None:
        self.datos = datos
        self.mapa = mapa
        self.fichas = fichas
        self.semilla = semilla
        self.azar = random.Random(semilla)
        self.reloj = 0
        self.agenda = Agenda()
        self.historial = Historial(MAX_ACCIONES_REVERSIBLES)
        self.mensajes = BitacoraMensajes(MENSAJES_VISIBLES)
        self.efectos = GestorEfectos(self)
        self.ia = IAEnemigos(self)
        self.jugador = Jugador(nombre_jugador, datos.jugador, mapa.sala_inicial, Inventario(datos.inventario_max))
        self.estado = EstadoPartida.EN_CURSO
        self.objetos_generados = 0
        # Siguiente "#n" por tipo de enemigo (solo para mostrar).
        self._numeros_por_tipo: TablaOrdenada[str, int] = TablaOrdenada()
        # Cuántas referencias tiene fijadas el modelo de cada tipo de ficha.
        self._fijadas: TablaOrdenada[str, int] = TablaOrdenada()
        self._iniciado = False
        # Para mostrar el juego "por turnos" en la terminal: número del primer
        # mensaje del último turno del jugador y del primero de la fase de los
        # enemigos (None = no hubo). Es información de presentación: no cambia
        # las reglas del reloj virtual (§2.3) ni se revierte.
        self.marca_turno: int | None = None
        self.marca_enemigos: int | None = None

    @property
    def enemigos(self) -> TablaOrdenada[str, Enemigo]:
        """Todas las instancias de enemigo conocidas, por id (vivas o muertas)."""
        return self.mapa.enemigos

    # =========================================================================
    # API pública (la usa el controlador)
    # =========================================================================

    def iniciar(self) -> None:
        """Reloj 0, jugador en la sala inicial, rastro 0 ahí, activar enemigos de
        la sala inicial y programar el primer turno del jugador en 0 (§2.4).

        El contenido de la sala inicial ya debe estar incorporado.
        """
        if self._iniciado:
            raise RuntimeError("La partida ya fue iniciada")
        sala = self.jugador.sala
        if not sala.contenido_cargado:
            raise RuntimeError(
                f"El contenido de la sala inicial ({sala.id}) debe incorporarse antes de iniciar la partida"
            )
        self._iniciado = True
        self.reloj = 0
        self.jugador.evento_turno = self._programar(0, TipoEvento.TURNO_JUGADOR, self.jugador)
        sala.rastro = 0
        sala.visitada = True
        self._fijar_sala(sala)
        self._mensaje(f"{self.jugador.nombre} entra a la cripta. Estás en {sala.nombre}.")
        self._activar_enemigos(sala)
        self._avanzar_hasta_decision()

    def ejecutar_accion(self, accion: Accion) -> ResultadoAccion:
        """Ejecuta una decisión del jugador y avanza hasta la siguiente (ver flujo arriba)."""
        if accion.tipo is TipoAccion.RETROCEDER:
            return self.usar_pergamino()
        resultado = self._validar(accion)
        if not resultado.aceptada:
            return resultado

        jugador = self.jugador
        self.marca_turno = self.mensajes.total
        self.marca_enemigos = None
        self.historial.abrir_intervalo(accion)
        try:
            self.historial.registrar(CambioEstadoAzar(self.azar.getstate()))
            self._iniciar_turno_jugador()
            costo = self._aplicar_accion(accion)
            self._asignar(jugador, "acciones_ejecutadas", jugador.acciones_ejecutadas + 1)
            if not self.esta_terminada():
                self._refrescar_rastro()
                self._programar_turno(jugador, costo)
                if accion.tipo is TipoAccion.MOVER:
                    self._entrar_a_sala(jugador.sala)
            # Lo que sigue (hasta la próxima decisión) es el "turno de los enemigos".
            self.marca_enemigos = self.mensajes.total
            self._avanzar_hasta_decision()
        except Exception:
            # La acción es atómica: se deshace lo que alcanzó a hacer.
            self.historial.descartar_abierto(self)
            self._reconciliar_fijaciones()
            raise
        self.historial.cerrar_intervalo()
        return ResultadoAccion(aceptada=True)

    def usar_pergamino(self) -> ResultadoAccion:
        """Retroceso (§2.11): no consume tiempo ni se registra como acción.

        1. Verificar que hay pergamino y que el historial tiene intervalos.
        2. Consumir UNA unidad de pergamino SIN registrarla en el historial.
        3. ``historial.retroceder(self)`` y recalcular las fichas fijadas.
        """
        if not self._iniciado or self.esta_terminada():
            return self._rechazo("La partida no está en curso.")
        inventario = self.jugador.inventario
        pergamino = inventario.primero_de_clase(ClaseObjeto.PERGAMINO)
        if pergamino is None:
            return self._rechazo("No tienes pergaminos de retroceso.")
        if not self.historial.puede_retroceder():
            return self._rechazo("No hay acciones para deshacer (como máximo se recuerdan 5).")
        # El consumo del pergamino queda FUERA del retroceso: no hay intervalo
        # abierto, así que nada de esto se registra.
        inventario.quitar(pergamino.id)
        self._liberar(pergamino.tipo_id)
        self.historial.retroceder(self)
        self._reconciliar_fijaciones()
        self.marca_turno = self.mensajes.total
        self.marca_enemigos = None  # retroceder no consume tiempo: no hay turno de los enemigos
        self._mensaje(
            f"Usas un pergamino de retroceso: vuelves al instante t={self.reloj} "
            f"(te quedan {inventario.contar_clase(ClaseObjeto.PERGAMINO)})."
        )
        return ResultadoAccion(aceptada=True)

    def sala_destino(self, direccion: str) -> Sala | None:
        """Sala a la que llevaría MOVER en ``direccion`` (para que el controlador
        asegure su contenido antes de confirmar el movimiento, §4.2)."""
        salida = self.jugador.sala.salida(_normalizar_direccion(direccion))
        return salida.destino if salida is not None else None

    def esta_terminada(self) -> bool:
        return self.estado is not EstadoPartida.EN_CURSO

    def resumen(self) -> ResumenPartida:
        return ResumenPartida(
            nombre_jugador=self.jugador.nombre,
            cripta_id=self.datos.id,
            version_cripta=self.datos.version,
            acciones_ejecutadas=self.jugador.acciones_ejecutadas,
            enemigos_derrotados=self.jugador.enemigos_derrotados,
            tiempo_final=self.reloj,
            estado=self.estado,
        )

    # --- consultas para la vista y el controlador ---------------------------------

    def vista_inventario(self, criterio: str, descendente: bool = False) -> list[InstanciaObjeto]:
        """Inventario ordenado por "peso", "valor" o "nombre" sin tocar el orden real (§4.5)."""
        fichas = self.fichas

        def por_peso(objeto: InstanciaObjeto) -> int:
            return _numero(fichas.obtener(objeto.tipo_id).peso)

        def por_valor(objeto: InstanciaObjeto) -> int:
            return _numero(fichas.obtener(objeto.tipo_id).valor)

        def por_nombre(objeto: InstanciaObjeto) -> str:
            return fichas.obtener(objeto.tipo_id).nombre.lower()

        clave: Callable[[InstanciaObjeto], Any]
        if criterio == "peso":
            clave = por_peso
        elif criterio == "valor":
            clave = por_valor
        elif criterio == "nombre":
            clave = por_nombre
        else:
            raise ValueError(f"Criterio de orden desconocido: {criterio!r} (usa peso, valor o nombre)")
        return self.jugador.inventario.vista_ordenada(clave, descendente)

    def nombre_de_tipo(self, tipo_id: str) -> str:
        """Nombre de catálogo de un tipo (o el id si la ficha no está disponible)."""
        try:
            return self.fichas.obtener(tipo_id).nombre
        except FichaNoDisponible:
            return tipo_id

    def enemigos_en_sala(self) -> list[Enemigo]:
        """Enemigos en la sala del jugador, en el orden de la sala (para elegir objetivo)."""
        return self.jugador.sala.enemigos.a_lista()

    def pergaminos_disponibles(self) -> int:
        return self.jugador.inventario.contar_clase(ClaseObjeto.PERGAMINO)

    def liberar_fijaciones(self) -> None:
        """Suelta todas las fichas que este juego tiene fijadas en el proveedor.

        La usa el controlador antes de reemplazar esta partida por otra (cargar),
        para que la caché no quede con fichas fijadas para siempre.
        """
        for tipo_id, cantidad in self._fijadas.pares():
            for _ in range(cantidad):
                self.fichas.liberar(tipo_id)
        self._fijadas = TablaOrdenada()

    # =========================================================================
    # Guardar / cargar (§4.10)
    # =========================================================================

    def exportar_estado(self, version_catalogo: str) -> EstadoGuardable:
        """Convierte el estado a registros neutros para el guardado (§4.10)."""
        jugador = self.jugador
        registro_jugador = RegistroJugador(
            nombre=jugador.nombre,
            sala=jugador.sala.id,
            vida=jugador.vida,
            vida_max=jugador.vida_max,
            ataque=jugador.ataque_base,
            defensa=jugador.defensa_base,
            velocidad=jugador.velocidad_base,
            tiempo_siguiente=jugador.tiempo_siguiente,
            inventario=[RegistroObjeto(objeto.id, objeto.tipo_id) for objeto in jugador.inventario],
            arma_equipada=jugador.arma.id if jugador.arma is not None else None,
            armadura_equipada=jugador.armadura.id if jugador.armadura is not None else None,
            acciones_ejecutadas=jugador.acciones_ejecutadas,
            enemigos_derrotados=jugador.enemigos_derrotados,
            abrio_puerta_salida=jugador.abrio_puerta_salida,
        )
        efectos = self._registros_efecto(jugador)
        salas: list[RegistroSala] = []
        for sala in self.mapa:
            enemigos: list[RegistroEnemigo] = []
            for enemigo in sala.enemigos:
                enemigos.append(
                    RegistroEnemigo(
                        enemigo.id, enemigo.tipo_id, enemigo.numero, enemigo.vida, enemigo.activo,
                        enemigo.tiempo_siguiente,
                    )
                )
                efectos.extend(self._registros_efecto(enemigo))
            salas.append(
                RegistroSala(
                    id=sala.id,
                    rastro=sala.rastro,
                    contenido_cargado=sala.contenido_cargado,
                    visitada=sala.visitada,
                    objetos_suelo=[RegistroObjeto(objeto.id, objeto.tipo_id) for objeto in sala.objetos_suelo],
                    trampas=[RegistroTrampa(trampa.id, trampa.tipo_id, trampa.armada) for trampa in sala.trampas],
                    enemigos=enemigos,
                    puertas=[
                        RegistroPuerta(salida.direccion, salida.puerta.cerrada)
                        for salida in sala.salidas
                        if salida is not None and salida.puerta is not None
                    ],
                )
            )
        eventos = [
            RegistroEvento(evento.tiempo, evento.secuencia, evento.tipo.name, self._id_objetivo(evento.objetivo))
            for evento in self.agenda.pendientes()
        ]
        return EstadoGuardable(
            cripta_id=self.datos.id,
            version_cripta=self.datos.version,
            version_catalogo=version_catalogo,
            semilla=self.semilla,
            estado_azar=self.azar.getstate(),
            reloj=self.reloj,
            siguiente_secuencia=self.agenda.siguiente_secuencia,
            jugador=registro_jugador,
            salas=salas,
            efectos=efectos,
            eventos=eventos,
            objetos_generados=self.objetos_generados,
        )

    @staticmethod
    def desde_estado(estado: EstadoGuardable, datos: DatosCripta, mapa: Mapa, fichas: ProveedorFichas) -> Juego:
        """Reconstruye una partida guardada.

        ``mapa`` es el construido con el esqueleto (se le borra cualquier
        contenido previo). Las fichas de todos los tipos del estado deben estar
        resueltas. El historial de retroceso arranca vacío.
        """
        if estado.cripta_id != datos.id or estado.version_cripta != datos.version:
            raise ValueError(
                f"La partida guardada es de {estado.cripta_id} versión {estado.version_cripta}, "
                f"pero los datos cargados son de {datos.id} versión {datos.version}"
            )
        mapa.reiniciar_contenido()
        juego = Juego(datos, mapa, fichas, estado.semilla, estado.jugador.nombre)
        juego.azar.setstate(_como_estado_azar(estado.estado_azar))
        juego.reloj = estado.reloj
        trampas: TablaOrdenada[str, InstanciaTrampa] = TablaOrdenada()

        # Salas: suelo, trampas, enemigos y puertas.
        for registro_sala in estado.salas:
            sala = mapa.sala(registro_sala.id)
            sala.rastro = registro_sala.rastro
            sala.contenido_cargado = registro_sala.contenido_cargado
            sala.visitada = registro_sala.visitada
            for registro in registro_sala.objetos_suelo:
                sala.objetos_suelo.agregar_al_final(
                    InstanciaObjeto(registro.instancia, registro.tipo, juego._clase_de(registro.tipo))
                )
            for registro in registro_sala.trampas:
                trampa = InstanciaTrampa(registro.instancia, fichas.obtener(registro.tipo))
                trampa.armada = registro.armada
                sala.trampas.append(trampa)
                trampas.insertar(trampa.id, trampa)
            for registro in registro_sala.enemigos:
                enemigo = Enemigo(registro.instancia, fichas.obtener(registro.tipo), registro.vida, registro.numero, sala)
                enemigo.activo = registro.activo
                enemigo.nodo_en_sala = sala.enemigos.agregar_al_final(enemigo)
                mapa.enemigos.insertar(enemigo.id, enemigo)
                if registro.numero > juego._numeros_por_tipo.obtener(enemigo.tipo_id, 0):
                    juego._numeros_por_tipo.insertar(enemigo.tipo_id, registro.numero)
            for registro in registro_sala.puertas:
                salida = sala.salida(registro.direccion)
                if salida is not None and salida.puerta is not None:
                    salida.puerta.cerrada = registro.cerrada

        # Jugador.
        registro_jugador = estado.jugador
        jugador = juego.jugador
        jugador.sala = mapa.sala(registro_jugador.sala)
        jugador.vida_max = registro_jugador.vida_max
        jugador.vida = registro_jugador.vida
        jugador.ataque_base = registro_jugador.ataque
        jugador.defensa_base = registro_jugador.defensa
        jugador.velocidad_base = registro_jugador.velocidad
        jugador.acciones_ejecutadas = registro_jugador.acciones_ejecutadas
        jugador.enemigos_derrotados = registro_jugador.enemigos_derrotados
        jugador.abrio_puerta_salida = registro_jugador.abrio_puerta_salida
        ultimo_id: str | None = None
        for registro in registro_jugador.inventario:
            objeto = InstanciaObjeto(registro.instancia, registro.tipo, juego._clase_de(registro.tipo))
            jugador.inventario.insertar_despues(ultimo_id, objeto)  # respeta el orden real guardado
            ultimo_id = objeto.id
        if registro_jugador.arma_equipada is not None:
            jugador.arma = jugador.inventario.obtener(registro_jugador.arma_equipada)
            if jugador.arma is not None:
                jugador.bono_ataque = _numero(fichas.obtener(jugador.arma.tipo_id).ataque_bonus)
        if registro_jugador.armadura_equipada is not None:
            jugador.armadura = jugador.inventario.obtener(registro_jugador.armadura_equipada)
            if jugador.armadura is not None:
                jugador.bono_defensa = _numero(fichas.obtener(jugador.armadura.tipo_id).defensa_bonus)

        # Efectos.
        efectos: TablaOrdenada[str, Efecto] = TablaOrdenada()
        for registro in estado.efectos:
            portador = jugador if registro.portador == Jugador.ID else mapa.enemigos.obtener(registro.portador)
            if portador is None:
                raise ValueError(f"Partida guardada inconsistente: efecto sobre {registro.portador!r} desconocido")
            tipo = TipoEfecto.desde_texto(registro.tipo)
            efecto = Efecto(tipo, portador, registro.inicio, registro.fin, registro.magnitud)
            setattr(portador, ranura_de(tipo), efecto)
            if tipo is TipoEfecto.VELOCIDAD:
                portador.modificador_velocidad += registro.magnitud
            efectos.insertar(efecto.clave(), efecto)

        # Eventos (con SU secuencia original) y referencias de cada dueño a su evento.
        for registro in estado.eventos:
            tipo = TipoEvento.desde_nombre(registro.tipo)
            objetivo = juego._resolver_objetivo(tipo, registro.objetivo, efectos, trampas)
            evento = juego.agenda.insertar_cargado(registro.tiempo, registro.secuencia, tipo, objetivo)
            if tipo is TipoEvento.TURNO_JUGADOR or tipo is TipoEvento.TURNO_ENEMIGO:
                objetivo.evento_turno = evento
            elif tipo is TipoEvento.PULSO_VENENO or tipo is TipoEvento.PULSO_REGENERACION:
                objetivo.evento_pulso = evento
            elif tipo is TipoEvento.FIN_VELOCIDAD or tipo is TipoEvento.APAGAR_ANTORCHA:
                objetivo.evento_fin = evento
            elif tipo is TipoEvento.REARME_TRAMPA:
                objetivo.evento_rearme = evento
            else:
                objetivo.evento_cierre = evento
        juego.agenda.establecer_secuencia(estado.siguiente_secuencia)
        if jugador.evento_turno is None:
            raise ValueError("Partida guardada inconsistente: el jugador no tiene turno programado")

        juego.objetos_generados = estado.objetos_generados
        juego._iniciado = True
        juego._reconciliar_fijaciones()
        juego._mensaje(f"Partida cargada en t={juego.reloj}.")
        return juego

    # =========================================================================
    # Bucle de eventos (§2.3)
    # =========================================================================

    def _avanzar_hasta_decision(self) -> None:
        """Mientras la partida siga: si el próximo evento es TURNO_JUGADOR, ajustar
        el reloj y volver; si no, extraerlo, avanzar el reloj y despacharlo."""
        agenda = self.agenda
        historial = self.historial
        while self.estado is EstadoPartida.EN_CURSO:
            evento = agenda.ver_siguiente()
            if evento is None:
                raise RuntimeError("La agenda quedó vacía: el jugador no tiene turno programado")
            if evento.tipo is TipoEvento.TURNO_JUGADOR:
                self._asignar(self, "reloj", evento.tiempo)
                return
            agenda.extraer_siguiente()
            if historial.grabando:
                historial.registrar(CambioEventoExtraido(evento))
            self._asignar(self, "reloj", evento.tiempo)
            self._despachar(evento)

    def _despachar(self, evento: Evento) -> None:
        """Ejecuta un evento según su ``TipoEvento``."""
        tipo = evento.tipo
        objetivo: Any = evento.objetivo
        if tipo is TipoEvento.TURNO_ENEMIGO:
            self._asignar(objetivo, "evento_turno", None)
            self.ia.actuar(objetivo)
        elif tipo is TipoEvento.PULSO_VENENO:
            self.efectos.pulso_veneno(objetivo)
        elif tipo is TipoEvento.FIN_VELOCIDAD:
            self.efectos.terminar_velocidad(objetivo)
        elif tipo is TipoEvento.APAGAR_ANTORCHA:
            self.efectos.apagar_antorcha(objetivo)
        elif tipo is TipoEvento.PULSO_REGENERACION:
            self.efectos.pulso_regeneracion(objetivo)
        elif tipo is TipoEvento.REARME_TRAMPA:
            self.efectos.rearmar_trampa(objetivo)
        elif tipo is TipoEvento.CIERRE_PUERTA:
            self.efectos.cerrar_puerta(objetivo)
        else:
            raise RuntimeError(f"Evento que no se puede despachar: {evento!r}")

    def _iniciar_turno_jugador(self) -> None:
        """Saca de la agenda el TURNO_JUGADOR que está en la cima (paso 4)."""
        evento = self.agenda.ver_siguiente()
        if evento is None or evento.tipo is not TipoEvento.TURNO_JUGADOR:
            raise RuntimeError("Estado inconsistente: el próximo evento no es el turno del jugador")
        self.agenda.extraer_siguiente()
        self.historial.registrar(CambioEventoExtraido(evento))
        self._asignar(self.jugador, "evento_turno", None)

    # =========================================================================
    # Acciones del jugador. Cada una devuelve el costo base (§2.3).
    # La validación se hace antes, en ``_validar``.
    # =========================================================================

    def _validar(self, accion: Accion) -> ResultadoAccion:
        """Revisa si la acción es posible SIN modificar el estado."""
        if not self._iniciado:
            return self._rechazo("La partida no ha iniciado.")
        if self.esta_terminada():
            return self._rechazo("La partida ya terminó.")
        jugador = self.jugador
        sala = jugador.sala
        tipo = accion.tipo

        if tipo is TipoAccion.MOVER or tipo is TipoAccion.ABRIR:
            direccion = _normalizar_direccion(accion.direccion)
            salida = sala.salida(direccion)
            if salida is None:
                if not direccion:
                    return self._rechazo("Falta la dirección (N, S, E u O).")
                return self._rechazo(f"No hay salida hacia el {nombre_direccion(direccion)}.")
            if tipo is TipoAccion.MOVER:
                if not salida.es_transitable():
                    return self._rechazo(f"La puerta hacia el {nombre_direccion(direccion)} está cerrada.")
                if not salida.destino.contenido_cargado:
                    return ResultadoAccion(
                        aceptada=False,
                        motivo="El contenido de la sala destino aún no está disponible.",
                        requiere_sala=salida.destino.id,
                    )
                return ResultadoAccion(aceptada=True)
            puerta = salida.puerta
            if puerta is None or not puerta.cerrada:
                return self._rechazo(f"No hay una puerta cerrada hacia el {nombre_direccion(direccion)}.")
            if puerta.llave is not None and not jugador.tiene_llave(puerta.llave):
                return self._rechazo("No tienes la llave que abre esa puerta.")
            return ResultadoAccion(aceptada=True)

        if tipo is TipoAccion.ATACAR:
            enemigo = self.enemigos.obtener(accion.objetivo) if accion.objetivo is not None else None
            if enemigo is None or not enemigo.esta_vivo() or enemigo.sala is not sala or enemigo.nodo_en_sala is None:
                return self._rechazo("Ese enemigo no está en tu sala.")
            return ResultadoAccion(aceptada=True)

        if tipo is TipoAccion.ESPERAR:
            return ResultadoAccion(aceptada=True)

        if tipo is TipoAccion.RECOGER:
            if sala.buscar_objeto_suelo(accion.objetivo) is None:
                return self._rechazo("Ese objeto no está en el suelo de esta sala.")
            if jugador.inventario.esta_lleno():
                return self._rechazo("Tu inventario está lleno: suelta algo primero.")
            return ResultadoAccion(aceptada=True)

        objeto = jugador.inventario.obtener(accion.objetivo)
        if tipo is TipoAccion.SOLTAR:
            if objeto is None:
                return self._rechazo("Ese objeto no está en tu inventario.")
            return ResultadoAccion(aceptada=True)

        if tipo is TipoAccion.USAR:
            if objeto is None:
                return self._rechazo("Ese objeto no está en tu inventario.")
            if objeto.clase is ClaseObjeto.PERGAMINO:
                return self._rechazo("Para usar un pergamino de retroceso usa el comando 'retroceder'.")
            if objeto.clase not in (ClaseObjeto.POCION, ClaseObjeto.ANTIDOTO, ClaseObjeto.ANTORCHA):
                return self._rechazo("Ese objeto no se puede usar (las armas y armaduras se equipan).")
            return ResultadoAccion(aceptada=True)

        if tipo is TipoAccion.EQUIPAR:
            if objeto is None:
                return self._rechazo("Ese objeto no está en tu inventario.")
            if objeto.clase is not ClaseObjeto.ARMA and objeto.clase is not ClaseObjeto.ARMADURA:
                return self._rechazo("Solo se pueden equipar armas y armaduras.")
            if objeto is jugador.arma or objeto is jugador.armadura:
                return self._rechazo("Ese objeto ya está equipado.")
            return ResultadoAccion(aceptada=True)

        return self._rechazo(f"Acción desconocida: {tipo}")

    def _aplicar_accion(self, accion: Accion) -> int:
        tipo = accion.tipo
        if tipo is TipoAccion.MOVER:
            return self._mover(_normalizar_direccion(accion.direccion))
        if tipo is TipoAccion.ABRIR:
            return self._abrir(_normalizar_direccion(accion.direccion))
        if tipo is TipoAccion.ATACAR:
            return self._atacar(accion.objetivo)
        if tipo is TipoAccion.ESPERAR:
            return self._esperar()
        if tipo is TipoAccion.RECOGER:
            return self._recoger(accion.objetivo)
        if tipo is TipoAccion.SOLTAR:
            return self._soltar(accion.objetivo)
        if tipo is TipoAccion.USAR:
            return self._usar(accion.objetivo)
        if tipo is TipoAccion.EQUIPAR:
            return self._equipar(accion.objetivo)
        raise ValueError(f"Acción no aplicable: {tipo}")

    def _mover(self, direccion: str) -> int:
        jugador = self.jugador
        origen = jugador.sala
        destino = origen.salida(direccion).destino
        # Primero se fija lo de la sala nueva y luego se libera lo de la vieja:
        # una ficha que esté en ambas nunca queda sin referencias por un instante.
        self._fijar_sala(destino)
        self._liberar_sala(origen)
        self._asignar(jugador, "sala", destino)
        self._mensaje(f"Vas al {nombre_direccion(direccion)} y entras a {destino.nombre}.")
        return COSTO_MOVER

    def _abrir(self, direccion: str) -> int:
        """La llave no se consume; si la puerta tiene cierre automático, se programa."""
        puerta = self.jugador.sala.salida(direccion).puerta
        self._asignar(puerta, "cerrada", False)
        if puerta.llave is not None and puerta.llave == self.datos.llave_salida:
            self._asignar(self.jugador, "abrio_puerta_salida", True)
        texto = f"Abres la puerta del {nombre_direccion(direccion)}."
        if puerta.cierre_automatico is not None:
            texto += f" Se cerrará sola en {puerta.cierre_automatico}."
        self._mensaje(texto)
        self.efectos.programar_cierre(puerta)
        return COSTO_ABRIR

    def _atacar(self, enemigo_id: str) -> int:
        enemigo = self.enemigos.obtener(enemigo_id)
        dano = self._calcular_dano(self.jugador, enemigo)
        self._mensaje(f"Atacas a {enemigo.etiqueta()}: -{dano}")
        self._aplicar_dano(enemigo, dano)
        return COSTO_ATACAR

    def _esperar(self) -> int:
        self._mensaje("Esperas.")
        return COSTO_ESPERAR

    def _recoger(self, objeto_id: str) -> int:
        sala = self.jugador.sala
        nodo = sala.buscar_objeto_suelo(objeto_id)
        objeto = nodo.valor
        # Los pergaminos no se registran: el retroceso no los devuelve al suelo (§2.11).
        registrar = not objeto.es_pergamino()
        self._inventario_agregar(objeto, registrar)
        self._suelo_quitar(sala, nodo, registrar)
        self._mensaje(f"Recoges {self.nombre_de_tipo(objeto.tipo_id)}.")
        return COSTO_RECOGER

    def _soltar(self, objeto_id: str) -> int:
        jugador = self.jugador
        objeto = jugador.inventario.obtener(objeto_id)
        registrar = not objeto.es_pergamino()
        self._desequipar_si_corresponde(objeto)
        self._suelo_agregar(jugador.sala, objeto, registrar)
        self._inventario_quitar(objeto, registrar)
        self._mensaje(f"Sueltas {self.nombre_de_tipo(objeto.tipo_id)}.")
        return COSTO_SOLTAR

    def _usar(self, objeto_id: str) -> int:
        """Poción (cura o velocidad), antídoto, antorcha. El pergamino va por ``usar_pergamino``."""
        jugador = self.jugador
        objeto = jugador.inventario.obtener(objeto_id)
        ficha = self.fichas.obtener(objeto.tipo_id)
        self._mensaje(f"Usas {ficha.nombre}.")
        if objeto.clase is ClaseObjeto.POCION:
            if ficha.cura is not None and ficha.cura > 0:
                antes = jugador.vida
                self._curar(jugador, ficha.cura)
                self._mensaje(f"Recuperas {jugador.vida - antes} de vida ({jugador.vida}/{jugador.vida_max}).")
            if ficha.modificador_velocidad is not None and ficha.duracion is not None:
                self.efectos.aplicar_velocidad(jugador, ficha.modificador_velocidad, ficha.duracion)
        elif objeto.clase is ClaseObjeto.ANTIDOTO:
            if jugador.veneno is not None:
                self.efectos.cancelar_veneno(jugador)
                self._mensaje("El antídoto cancela el veneno.")
            else:
                self._mensaje("No estabas envenenado.")
        elif objeto.clase is ClaseObjeto.ANTORCHA:
            self.efectos.encender_antorcha(jugador, _numero(ficha.duracion))
        self._inventario_quitar(objeto, registrar=True)  # se consume
        return COSTO_USAR

    def _equipar(self, objeto_id: str) -> int:
        """Mueve al frente del inventario; reemplaza arma / armadura anterior (§2.7)."""
        jugador = self.jugador
        objeto = jugador.inventario.obtener(objeto_id)
        ficha = self.fichas.obtener(objeto.tipo_id)
        if objeto.clase is ClaseObjeto.ARMA:
            self._asignar(jugador, "arma", objeto)
            self._asignar(jugador, "bono_ataque", _numero(ficha.ataque_bonus))
        else:
            self._asignar(jugador, "armadura", objeto)
            self._asignar(jugador, "bono_defensa", _numero(ficha.defensa_bonus))
        self._inventario_al_frente(objeto)
        self._mensaje(f"Equipas {ficha.nombre}.")
        return COSTO_EQUIPAR

    def _desequipar_si_corresponde(self, objeto: InstanciaObjeto) -> None:
        jugador = self.jugador
        if jugador.arma is objeto:
            self._asignar(jugador, "arma", None)
            self._asignar(jugador, "bono_ataque", 0)
        if jugador.armadura is objeto:
            self._asignar(jugador, "armadura", None)
            self._asignar(jugador, "bono_defensa", 0)

    # =========================================================================
    # Reglas auxiliares
    # =========================================================================

    @staticmethod
    def calcular_intervalo(costo: int, velocidad: int) -> int:
        """max(1, costo * 100 // velocidad) (§2.3)."""
        return max(1, costo * VELOCIDAD_REFERENCIA // velocidad)

    def _calcular_dano(self, atacante: Actor, defensor: Actor) -> int:
        """max(1, ataque + azar.randint(0, 4) - defensa) (§2.6)."""
        return max(DANO_MINIMO, atacante.ataque + self.azar.randint(AZAR_DANO_MIN, AZAR_DANO_MAX) - defensor.defensa)

    def _aplicar_dano(self, actor: Actor, cantidad: int) -> None:
        if cantidad <= 0 or not actor.esta_vivo():
            return
        nueva = max(0, actor.vida - cantidad)
        self._asignar(actor, "vida", nueva)
        if nueva == 0:
            self._matar(actor)

    def _curar(self, actor: Actor, cantidad: int) -> None:
        """Nunca por encima de vida_max (Apéndice B)."""
        if cantidad <= 0 or not actor.esta_vivo():
            return
        self._asignar(actor, "vida", min(actor.vida_max, actor.vida + cantidad))

    def _programar_turno(self, actor: Actor, costo: int) -> None:
        intervalo = self.calcular_intervalo(costo, actor.velocidad)
        tipo = TipoEvento.TURNO_JUGADOR if actor is self.jugador else TipoEvento.TURNO_ENEMIGO
        self._asignar(actor, "evento_turno", self._programar(self.reloj + intervalo, tipo, actor))

    def _entrar_a_sala(self, sala: Sala) -> None:
        """Visita, activación de enemigos dormidos, trampas y victoria (paso 7).

        El rastro ya lo puso ``_refrescar_rastro`` y las fichas ya se fijaron en
        ``_mover``.
        """
        if not sala.visitada:
            self._asignar(sala, "visitada", True)
        self._activar_enemigos(sala)
        for trampa in sala.trampas:
            if self.esta_terminada():
                break
            if trampa.armada:
                self.efectos.activar_trampa(trampa, self.jugador)
        self._verificar_fin()

    def _activar_enemigos(self, sala: Sala) -> None:
        """Orden ascendente de id de instancia; primera acción con costo 100 (§2.4)."""
        dormidos = sala.enemigos_dormidos()
        if not dormidos:
            return
        for enemigo in ordenar(dormidos, clave=_id_de):
            if not enemigo.esta_vivo():
                continue
            self._asignar(enemigo, "activo", True)
            if enemigo.numero == 0:
                # El número es solo para mostrar: se asigna una vez y no se revierte.
                enemigo.numero = self._siguiente_numero(enemigo.tipo_id)
            self._fijar(enemigo.tipo_id)
            self._programar_turno(enemigo, COSTO_ACTIVACION_ENEMIGO)
            if enemigo.regeneracion_por_pulso > 0:
                self.efectos.iniciar_regeneracion(enemigo, enemigo.regeneracion_por_pulso)
            self._mensaje(f"{enemigo.etiqueta()} te ha visto.")

    def _mover_enemigo(self, enemigo: Enemigo, destino: Sala, direccion: str = "") -> None:
        origen = enemigo.sala
        sala_jugador = self.jugador.sala
        self._sacar_enemigo_de_sala(enemigo)
        self._poner_enemigo_en_sala(enemigo, destino)
        if origen is sala_jugador:
            self._mensaje(f"{enemigo.etiqueta()} se va hacia el {nombre_direccion(direccion)}.")
        elif destino is sala_jugador:
            self._mensaje(f"{enemigo.etiqueta()} entra a la sala.")

    def _matar(self, actor: Actor) -> None:
        """Cancela su turno y efectos; si es enemigo, suelta objetos y cuenta la baja."""
        self._cancelar_evento(actor.evento_turno)
        self._asignar(actor, "evento_turno", None)
        self.efectos.cancelar_efectos_de(actor)
        if actor is self.jugador:
            self._mensaje("Has muerto.")
            self._asignar(self, "estado", EstadoPartida.DERROTA)
            return
        enemigo: Enemigo = actor  # type: ignore[assignment]
        sala = enemigo.sala
        self._mensaje(f"{enemigo.etiqueta()} muere.")
        self._sacar_enemigo_de_sala(enemigo)
        if enemigo.activo:
            self._liberar(enemigo.tipo_id)
        self._asignar(self.jugador, "enemigos_derrotados", self.jugador.enemigos_derrotados + 1)
        for tipo_id in enemigo.suelta:
            self.objetos_generados += 1  # no se revierte (ver objetos.py)
            objeto = InstanciaObjeto(id_objeto_soltado(enemigo.id, self.objetos_generados), tipo_id, self._clase_de(tipo_id))
            self._suelo_agregar(sala, objeto, registrar=True)
            self._mensaje(f"{enemigo.etiqueta()} deja caer {self.nombre_de_tipo(tipo_id)}.")

    def _refrescar_rastro(self) -> None:
        self._asignar(self.jugador.sala, "rastro", self.reloj)

    def _verificar_fin(self) -> None:
        """Derrota: vida 0. Victoria: entrar a la sala de salida tras abrir su puerta."""
        if self.esta_terminada():
            return
        jugador = self.jugador
        if not jugador.esta_vivo():
            self._asignar(self, "estado", EstadoPartida.DERROTA)
        elif jugador.sala is self.mapa.sala_salida and jugador.abrio_puerta_salida:
            self._asignar(self, "estado", EstadoPartida.VICTORIA)
            self._mensaje("¡Encontraste la salida de la cripta! Victoria.")

    def _asignar(self, objeto: object, atributo: str, valor: Any) -> None:
        """setattr + registro de ``CambioAtributo`` en el historial."""
        anterior = getattr(objeto, atributo)
        if anterior is valor or anterior == valor:
            return
        if self.historial.grabando:
            self.historial.registrar(CambioAtributo(objeto, atributo, anterior))
        setattr(objeto, atributo, valor)

    def _mensaje(self, texto: str) -> None:
        self.mensajes.agregar(self.reloj, texto)

    @staticmethod
    def _rechazo(motivo: str) -> ResultadoAccion:
        return ResultadoAccion(aceptada=False, motivo=motivo)

    # =========================================================================
    # Helpers que mutan Y registran (agenda, listas de sala, inventario)
    # =========================================================================

    def _programar(self, tiempo: int, tipo: TipoEvento, objetivo: object) -> Evento:
        evento = self.agenda.programar(tiempo, tipo, objetivo)
        if self.historial.grabando:
            self.historial.registrar(CambioEventoProgramado(evento))
        return evento

    def _cancelar_evento(self, evento: Evento | None) -> None:
        if evento is not None and self.agenda.cancelar(evento) and self.historial.grabando:
            self.historial.registrar(CambioEventoCancelado(evento))

    def _reprogramar(self, evento: Evento, nuevo_tiempo: int) -> Evento:
        """Cancela y programa uno equivalente con secuencia NUEVA (§2.3)."""
        self._cancelar_evento(evento)
        return self._programar(nuevo_tiempo, evento.tipo, evento.objetivo)

    def _sacar_enemigo_de_sala(self, enemigo: Enemigo) -> None:
        nodo = enemigo.nodo_en_sala
        if nodo is None:
            return
        lista = enemigo.sala.enemigos
        anterior = lista.anterior(nodo)
        lista.quitar(nodo)
        if self.historial.grabando:
            self.historial.registrar(CambioNodoQuitado(lista, nodo, anterior))
        self._asignar(enemigo, "nodo_en_sala", None)

    def _poner_enemigo_en_sala(self, enemigo: Enemigo, sala: Sala) -> None:
        nodo = sala.enemigos.agregar_al_final(enemigo)
        if self.historial.grabando:
            self.historial.registrar(CambioNodoAgregado(sala.enemigos, nodo))
        self._asignar(enemigo, "sala", sala)
        self._asignar(enemigo, "nodo_en_sala", nodo)

    def _suelo_agregar(self, sala: Sala, objeto: InstanciaObjeto, registrar: bool) -> None:
        nodo = sala.objetos_suelo.agregar_al_final(objeto)
        if registrar and self.historial.grabando:
            self.historial.registrar(CambioNodoAgregado(sala.objetos_suelo, nodo))
        if sala is self.jugador.sala:
            self._fijar(objeto.tipo_id)

    def _suelo_quitar(self, sala: Sala, nodo: NodoDoble[InstanciaObjeto], registrar: bool) -> None:
        lista = sala.objetos_suelo
        anterior = lista.anterior(nodo)
        # Respaldo: anterior más cercano que no sea pergamino (un pergamino
        # vecino puede salir del suelo sin registrarse, §2.11).
        respaldo = anterior
        while respaldo is not None and respaldo.valor.es_pergamino():
            respaldo = lista.anterior(respaldo)
        lista.quitar(nodo)
        if registrar and self.historial.grabando:
            self.historial.registrar(CambioNodoQuitado(lista, nodo, anterior, respaldo))
        if sala is self.jugador.sala:
            self._liberar(nodo.valor.tipo_id)

    def _inventario_agregar(self, objeto: InstanciaObjeto, registrar: bool) -> None:
        self.jugador.inventario.agregar(objeto)
        self._fijar(objeto.tipo_id)
        if registrar and self.historial.grabando:
            self.historial.registrar(CambioInventario(objeto, CambioInventario.AGREGADO, None))

    def _inventario_quitar(self, objeto: InstanciaObjeto, registrar: bool) -> None:
        inventario = self.jugador.inventario
        anterior = inventario.anterior_de(objeto.id)
        respaldo = inventario.anterior_no_pergamino(objeto.id)
        inventario.quitar(objeto.id)
        self._liberar(objeto.tipo_id)
        if registrar and self.historial.grabando:
            self.historial.registrar(CambioInventario(objeto, CambioInventario.QUITADO, anterior, respaldo))

    def _inventario_al_frente(self, objeto: InstanciaObjeto) -> None:
        inventario = self.jugador.inventario
        anterior = inventario.anterior_de(objeto.id)
        respaldo = inventario.anterior_no_pergamino(objeto.id)
        inventario.mover_al_frente(objeto.id)
        if self.historial.grabando:
            self.historial.registrar(CambioInventario(objeto, CambioInventario.FRENTE, anterior, respaldo))

    # =========================================================================
    # Fichas en uso (§4.4)
    # =========================================================================

    def _fijar(self, tipo_id: str) -> None:
        self._fijadas.insertar(tipo_id, self._fijadas.obtener(tipo_id, 0) + 1)
        self.fichas.fijar(tipo_id)

    def _liberar(self, tipo_id: str) -> None:
        cantidad = self._fijadas.obtener(tipo_id, 0)
        if cantidad <= 0:
            return
        if cantidad == 1:
            self._fijadas.eliminar(tipo_id)
        else:
            self._fijadas.insertar(tipo_id, cantidad - 1)
        self.fichas.liberar(tipo_id)

    def _fijar_sala(self, sala: Sala) -> None:
        for objeto in sala.objetos_suelo:
            self._fijar(objeto.tipo_id)
        for trampa in sala.trampas:
            self._fijar(trampa.tipo_id)

    def _liberar_sala(self, sala: Sala) -> None:
        for objeto in sala.objetos_suelo:
            self._liberar(objeto.tipo_id)
        for trampa in sala.trampas:
            self._liberar(trampa.tipo_id)

    def _fijaciones_deseadas(self) -> TablaOrdenada[str, int]:
        """Referencias que DEBERÍA tener el modelo según el estado actual."""
        deseadas: TablaOrdenada[str, int] = TablaOrdenada()
        for objeto in self.jugador.inventario:
            _sumar_uno(deseadas, objeto.tipo_id)
        sala = self.jugador.sala
        for objeto in sala.objetos_suelo:
            _sumar_uno(deseadas, objeto.tipo_id)
        for trampa in sala.trampas:
            _sumar_uno(deseadas, trampa.tipo_id)
        # Aquí solo se CUENTA, no se decide nada del juego (el orden de las
        # llamadas solo afecta la recencia de la caché).
        for enemigo in self.enemigos.valores():
            if enemigo.activo and enemigo.esta_vivo():
                _sumar_uno(deseadas, enemigo.tipo_id)
        return deseadas

    def _reconciliar_fijaciones(self) -> None:
        """Ajusta fijar / liberar para que coincidan con el estado (tras retroceder o cargar).

        Primero se suman las que faltan y después se quitan las que sobran, para
        que una ficha que sigue en uso nunca quede sin referencias.
        """
        deseadas = self._fijaciones_deseadas()
        actuales = self._fijadas
        for tipo_id, cantidad in deseadas.pares():
            for _ in range(cantidad - actuales.obtener(tipo_id, 0)):
                self.fichas.fijar(tipo_id)
        for tipo_id, cantidad in actuales.pares():
            for _ in range(cantidad - deseadas.obtener(tipo_id, 0)):
                self.fichas.liberar(tipo_id)
        self._fijadas = deseadas

    # =========================================================================
    # Internos varios
    # =========================================================================

    def _clase_de(self, tipo_id: str) -> ClaseObjeto:
        return ClaseObjeto.desde_texto(self.fichas.obtener(tipo_id).clase)

    def _siguiente_numero(self, tipo_id: str) -> int:
        numero = self._numeros_por_tipo.obtener(tipo_id, 0) + 1
        self._numeros_por_tipo.insertar(tipo_id, numero)
        return numero

    @staticmethod
    def _registros_efecto(actor: Actor) -> list[RegistroEfecto]:
        registros: list[RegistroEfecto] = []
        for tipo in TipoEfecto:
            efecto: Efecto | None = getattr(actor, ranura_de(tipo))
            if efecto is not None and efecto.activo:
                registros.append(RegistroEfecto(tipo.value, actor.id, efecto.inicio, efecto.fin, efecto.magnitud))
        return registros

    @staticmethod
    def _id_objetivo(objetivo: object) -> str:
        """Id con el que un evento referencia a su objetivo en el archivo de guardado."""
        if isinstance(objetivo, Efecto):
            return objetivo.clave()
        return objetivo.id  # Actor, InstanciaTrampa o Puerta

    def _resolver_objetivo(
        self, tipo: TipoEvento, objetivo_id: str, efectos: TablaOrdenada[str, Efecto], trampas: TablaOrdenada[str, InstanciaTrampa]
    ) -> object:
        """Inverso de ``_id_objetivo`` al cargar una partida."""
        if tipo is TipoEvento.TURNO_JUGADOR:
            objetivo: object | None = self.jugador
        elif tipo is TipoEvento.TURNO_ENEMIGO:
            objetivo = self.enemigos.obtener(objetivo_id)
        elif tipo is TipoEvento.REARME_TRAMPA:
            objetivo = trampas.obtener(objetivo_id)
        elif tipo is TipoEvento.CIERRE_PUERTA:
            objetivo = self.mapa.puertas.obtener(objetivo_id)
        else:
            objetivo = efectos.obtener(objetivo_id)
        if objetivo is None:
            raise ValueError(f"Partida guardada inconsistente: el evento {tipo.name} apunta a {objetivo_id!r}")
        return objetivo


def _normalizar_direccion(direccion: str | None) -> str:
    return (direccion or "").strip().upper()


def _numero(valor: int | None) -> int:
    return valor if valor is not None else 0


def _sumar_uno(tabla: TablaOrdenada[str, int], clave: str) -> None:
    tabla.insertar(clave, tabla.obtener(clave, 0) + 1)


def _como_estado_azar(estado: Any) -> tuple:
    """Acepta el estado del azar como tupla o como listas (si vino de JSON)."""
    version, interno, gauss = estado
    return (version, tuple(interno), gauss)
