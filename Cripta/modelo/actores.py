"""Actores: jugador y enemigos.                                      [Persona A]

§2.2. Dos enemigos del mismo tipo comparten la ficha de catálogo pero son
actores distintos: cada uno tiene su vida, sala, id de instancia y tiempo de
próxima acción.

Decisión: el enemigo COPIA sus estadísticas base de la ficha al crearse y no
vuelve a consultar la caché en cada turno. El turno de un enemigo es la
operación más frecuente de la simulación (§5.2); consultar la caché ahí
sumaría una búsqueda por turno y además movería la recencia de la LRU sin
necesidad. Las fichas no cambian durante una partida (la versión del catálogo
se valida al empezar), así que copiar no pierde ninguna actualización.

Velocidad efectiva = base + suma de modificadores de velocidad activos
(interpretación ADITIVA de ``modificador_velocidad``), con un mínimo de 1.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from cripta.constantes import VELOCIDAD_REFERENCIA
from cripta.modelo.objetos import ClaseObjeto

if TYPE_CHECKING:
    from cripta.estructuras.lista_doble import NodoDoble
    from cripta.modelo.datos import EstadisticasIniciales, Ficha
    from cripta.modelo.efectos import Efecto
    from cripta.modelo.eventos import Evento
    from cripta.modelo.inventario import Inventario
    from cripta.modelo.mapa import Sala
    from cripta.modelo.objetos import InstanciaObjeto

# Ninguna velocidad efectiva baja de aquí (evita dividir entre 0 en §2.3).
VELOCIDAD_MINIMA = 1


class Comportamiento(Enum):
    GUARDIAN = "guardián"
    ERRANTE = "errante"
    RASTREADOR = "rastreador"

    @staticmethod
    def desde_texto(texto: str) -> Comportamiento:
        """Convierte el texto de la ficha. ValueError si no es válido.

        Acepta "guardián" con o sin tilde y sin importar mayúsculas.
        """
        normalizado = texto.strip().lower().replace("á", "a")
        if normalizado == "guardian":
            return Comportamiento.GUARDIAN
        if normalizado == "errante":
            return Comportamiento.ERRANTE
        if normalizado == "rastreador":
            return Comportamiento.RASTREADOR
        raise ValueError(f"Comportamiento de enemigo desconocido: {texto!r}")


class Actor:
    """Base común. ``vida`` nunca supera ``vida_max``; en 0 el actor muere.

    Todos los atributos que cambian durante la partida se modifican con
    ``Juego._asignar`` para que el retroceso pueda revertirlos.
    """

    id: str
    vida: int
    vida_max: int
    ataque_base: int
    defensa_base: int
    velocidad_base: int
    sala: Sala
    evento_turno: Evento | None  # turno pendiente; para cancelar / reprogramar en O(1)
    modificador_velocidad: int  # suma de los efectos de velocidad activos
    bono_ataque: int  # ataque_bonus del arma equipada (0 en enemigos)
    bono_defensa: int  # defensa_bonus de la armadura equipada (0 en enemigos)
    # Efectos activos (como mucho uno de cada tipo; ver efectos.py)
    veneno: Efecto | None
    efecto_velocidad: Efecto | None
    regeneracion: Efecto | None
    antorcha: Efecto | None

    def __init__(
        self,
        id: str,
        vida: int,
        vida_max: int,
        ataque: int,
        defensa: int,
        velocidad: int,
        sala: Sala,
    ) -> None:
        self.id = id
        self.vida_max = vida_max
        self.vida = max(0, min(vida, vida_max))
        self.ataque_base = ataque
        self.defensa_base = defensa
        self.velocidad_base = velocidad
        self.sala = sala
        self.evento_turno = None
        self.modificador_velocidad = 0
        self.bono_ataque = 0
        self.bono_defensa = 0
        self.veneno = None
        self.efecto_velocidad = None
        self.regeneracion = None
        self.antorcha = None

    @property
    def ataque(self) -> int:
        """Ataque efectivo (base + bonos)."""
        return self.ataque_base + self.bono_ataque

    @property
    def defensa(self) -> int:
        """Defensa efectiva (base + bonos)."""
        return self.defensa_base + self.bono_defensa

    @property
    def velocidad(self) -> int:
        """Velocidad efectiva (base + modificadores), nunca menor que 1."""
        return max(VELOCIDAD_MINIMA, self.velocidad_base + self.modificador_velocidad)

    @property
    def tiempo_siguiente(self) -> int | None:
        """Instante de la próxima acción (None si no tiene turno pendiente).

        Se deriva del evento para que nunca quede desincronizado con la agenda.
        """
        evento = self.evento_turno
        return evento.tiempo if evento is not None else None

    def esta_vivo(self) -> bool:
        return self.vida > 0

    def etiqueta(self) -> str:
        """Nombre que se muestra en la interfaz."""
        return self.id


class Jugador(Actor):
    """El jugador. Sus estadísticas iniciales vienen de los datos de la cripta."""

    ID = "jugador"  # id de actor del jugador (en eventos y archivos de guardado)

    nombre: str
    inventario: Inventario
    arma: InstanciaObjeto | None
    armadura: InstanciaObjeto | None
    acciones_ejecutadas: int  # solo acciones que consumen tiempo (§2.12)
    enemigos_derrotados: int
    abrio_puerta_salida: bool  # condición de victoria (§2.12)

    def __init__(
        self,
        nombre: str,
        estadisticas: EstadisticasIniciales,
        sala: Sala,
        inventario: Inventario,
    ) -> None:
        super().__init__(
            Jugador.ID,
            estadisticas.vida_max,
            estadisticas.vida_max,
            estadisticas.ataque,
            estadisticas.defensa,
            estadisticas.velocidad,
            sala,
        )
        self.nombre = nombre
        self.inventario = inventario
        self.arma = None
        self.armadura = None
        self.acciones_ejecutadas = 0
        self.enemigos_derrotados = 0
        self.abrio_puerta_salida = False

    def tiene_llave(self, llave_id: str) -> bool:
        """True si hay en el inventario un objeto de clase llave con ese id de tipo."""
        objeto = self.inventario.buscar_por_tipo(llave_id)
        return objeto is not None and objeto.clase is ClaseObjeto.LLAVE

    def etiqueta(self) -> str:
        return self.nombre


class Enemigo(Actor):
    """Instancia concreta de enemigo."""

    tipo_id: str
    nombre_tipo: str
    # Para mostrar "Rata gigante #2". Se asigna la PRIMERA vez que el enemigo
    # se activa (momento determinista del juego) y nunca se reasigna. 0 = aún
    # no tiene número (enemigo dormido).
    numero: int
    comportamiento: Comportamiento
    activo: bool  # se activa cuando el jugador entra a su sala (§2.4)
    suelta: list[str]  # ids de tipo que deja en el suelo al morir
    regeneracion_por_pulso: int  # 0 = no regenera (§2.10)
    veneno_por_ataque: int  # 0 = sus ataques no envenenan (§2.10)
    nodo_en_sala: NodoDoble[Enemigo] | None  # para sacarlo de su sala en O(1)

    def __init__(
        self,
        instancia: str,
        ficha: Ficha,
        vida_inicial: int | None,
        numero: int,
        sala: Sala,
    ) -> None:
        """``vida_inicial`` None → empieza con ``vida_max`` (API real, e-401)."""
        vida_max = ficha.vida_max if ficha.vida_max is not None and ficha.vida_max > 0 else 1
        if vida_inicial is None or vida_inicial <= 0:
            vida_inicial = vida_max
        super().__init__(
            instancia,
            vida_inicial,
            vida_max,
            ficha.ataque if ficha.ataque is not None else 0,
            ficha.defensa if ficha.defensa is not None else 0,
            ficha.velocidad if ficha.velocidad is not None else VELOCIDAD_REFERENCIA,
            sala,
        )
        self.tipo_id = ficha.id
        self.nombre_tipo = ficha.nombre
        self.numero = numero
        if ficha.comportamiento:
            self.comportamiento = Comportamiento.desde_texto(ficha.comportamiento)
        else:
            self.comportamiento = Comportamiento.GUARDIAN
        self.activo = False
        self.suelta = list(ficha.suelta)
        self.regeneracion_por_pulso = ficha.regeneracion if ficha.regeneracion is not None else 0
        self.veneno_por_ataque = ficha.veneno if ficha.veneno is not None else 0
        self.nodo_en_sala = None

    def etiqueta(self) -> str:
        """Por ejemplo "Rata gigante #1"."""
        if self.numero > 0:
            return f"{self.nombre_tipo} #{self.numero}"
        return f"{self.nombre_tipo} ({self.id})"

    def __repr__(self) -> str:
        return f"Enemigo({self.id!r}, vida={self.vida}/{self.vida_max}, activo={self.activo})"
