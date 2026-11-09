"""Algoritmos de ordenamiento propios y selector automático.         [Persona B]

§4.9: dos algoritmos con características distintas, elegidos AUTOMÁTICAMENTE
según propiedades medibles de los datos. No se usa ``list.sort()`` ni
``sorted()``.

- Inserción: rapidísimo con pocos elementos o con datos casi ordenados;
  estable; O(n²) en el peor caso.
- Mezcla (merge sort): O(n log n) siempre; estable.

Los dos son ESTABLES (si dos elementos empatan, conservan su orden original):
así las vistas del inventario y el orden de activación de enemigos son
siempre iguales en cada ejecución.

Decisiones medidas con --bench (ver el Documento de Decisiones, §4.9):
- La clave se calcula UNA vez por elemento (se "decora" la lista con pares
  (clave, elemento)). Calcularla en cada comparación era de 4 a 10 veces más
  lento cuando la clave es costosa (p. ej. buscar la ficha y pasar el nombre
  a minúsculas).
- Hasta ``UMBRAL_TAMANO_PEQUENO`` elementos se usa inserción siempre: gana con
  datos aleatorios o casi ordenados y, aun con datos al revés (su peor caso),
  pierde por poco.
- Con más elementos se usa inserción solo si los datos están casi ordenados:
  como mucho ``FACTOR_DESCENSOS · log2(n)`` "bajadas" entre vecinos. Cada
  bajada puede obligar a la inserción a mover hasta n elementos, así que
  descensos · n debe quedar por debajo de lo que cuesta la mezcla (≈ n·log2 n).

Las funciones reciben ``clave`` (igual que ``sorted``) y devuelven una lista
NUEVA sin modificar la original: las vistas no alteran el orden real (§4.5).
"""

from __future__ import annotations

from typing import Any, Callable, Sequence, TypeVar

T = TypeVar("T")
Clave = Callable[[Any], Any]

# Medido con --bench: con 32 elementos la inserción gana en datos aleatorios y casi
# ordenados; con 48 al revés ya tarda el doble que la mezcla.
UMBRAL_TAMANO_PEQUENO = 32
# Inserción si descensos <= FACTOR_DESCENSOS * log2(n) (medido con datos casi ordenados).
FACTOR_DESCENSOS = 2

INSERCION = "insercion"
MEZCLA = "mezcla"


def _identidad(x: Any) -> Any:
    return x


def _decorar(datos: Sequence[T], clave: Clave | None) -> list[tuple[Any, T]]:
    """Pares (clave, elemento): la clave se calcula una sola vez por elemento."""
    funcion = clave if clave is not None else _identidad
    return [(funcion(elemento), elemento) for elemento in datos]


def _quitar_claves(pares: list[tuple[Any, T]]) -> list[T]:
    return [par[1] for par in pares]


def _insercion_pares(pares: list[tuple[Any, T]], descendente: bool) -> list[tuple[Any, T]]:
    salida = list(pares)
    for i in range(1, len(salida)):
        actual = salida[i]
        clave_actual = actual[0]
        j = i - 1
        # Solo se corre un elemento si va ESTRICTAMENTE después: eso la hace estable.
        if descendente:
            while j >= 0 and salida[j][0] < clave_actual:
                salida[j + 1] = salida[j]
                j -= 1
        else:
            while j >= 0 and salida[j][0] > clave_actual:
                salida[j + 1] = salida[j]
                j -= 1
        salida[j + 1] = actual
    return salida


def _mezcla_pares(pares: list[tuple[Any, T]], descendente: bool) -> list[tuple[Any, T]]:
    if len(pares) <= 1:
        return list(pares)
    medio = len(pares) // 2
    izquierda = _mezcla_pares(pares[:medio], descendente)
    derecha = _mezcla_pares(pares[medio:], descendente)
    salida: list[tuple[Any, T]] = []
    i = j = 0
    while i < len(izquierda) and j < len(derecha):
        # Ante un empate se toma primero el de la izquierda: eso la hace estable.
        if descendente:
            toma_derecha = derecha[j][0] > izquierda[i][0]
        else:
            toma_derecha = derecha[j][0] < izquierda[i][0]
        if toma_derecha:
            salida.append(derecha[j])
            j += 1
        else:
            salida.append(izquierda[i])
            i += 1
    salida.extend(izquierda[i:])
    salida.extend(derecha[j:])
    return salida


def _contar_descensos(pares: list[tuple[Any, T]], descendente: bool) -> int:
    """Pares de vecinos que están al revés del orden pedido. O(n)."""
    descensos = 0
    for i in range(len(pares) - 1):
        if descendente:
            if pares[i][0] < pares[i + 1][0]:
                descensos += 1
        elif pares[i][0] > pares[i + 1][0]:
            descensos += 1
    return descensos


def _log2(n: int) -> int:
    """Parte entera de log2(n) (sin importar ``math``)."""
    resultado = 0
    while n > 1:
        n //= 2
        resultado += 1
    return resultado


def _elegir(pares: list[tuple[Any, T]], descendente: bool) -> str:
    cantidad = len(pares)
    if cantidad <= UMBRAL_TAMANO_PEQUENO:
        return INSERCION
    if _contar_descensos(pares, descendente) <= FACTOR_DESCENSOS * _log2(cantidad):
        return INSERCION
    return MEZCLA


# --- API pública ------------------------------------------------------------------


def ordenar_insercion(datos: Sequence[T], clave: Clave | None = None, descendente: bool = False) -> list[T]:
    """Ordenamiento por inserción, estable. Devuelve una lista nueva."""
    return _quitar_claves(_insercion_pares(_decorar(datos, clave), descendente))


def ordenar_mezcla(datos: Sequence[T], clave: Clave | None = None, descendente: bool = False) -> list[T]:
    """Ordenamiento por mezcla (merge sort), estable. Devuelve una lista nueva."""
    return _quitar_claves(_mezcla_pares(_decorar(datos, clave), descendente))


def ordenar(datos: Sequence[T], clave: Clave | None = None, descendente: bool = False) -> list[T]:
    """Punto de entrada ÚNICO que usa el resto del programa (selector automático)."""
    pares = _decorar(datos, clave)
    if _elegir(pares, descendente) == INSERCION:
        return _quitar_claves(_insercion_pares(pares, descendente))
    return _quitar_claves(_mezcla_pares(pares, descendente))


def ordenar_con_algoritmo(
    datos: Sequence[T], algoritmo: str, clave: Clave | None = None, descendente: bool = False
) -> list[T]:
    """Fuerza un algoritmo (lo usa --bench para comparar)."""
    if algoritmo == INSERCION:
        return ordenar_insercion(datos, clave, descendente)
    if algoritmo == MEZCLA:
        return ordenar_mezcla(datos, clave, descendente)
    raise ValueError(f"algoritmo desconocido: {algoritmo}")


def busqueda_binaria(
    datos_ordenados: Sequence[T], objetivo: Any, clave: Clave | None = None, descendente: bool = False
) -> int:
    """Posición de ``objetivo`` en una lista ordenada por ``clave``, o -1. O(log n).

    La usa el guardado binario para encontrar una sala en el índice del archivo
    sin leerlo completo (§4.10).
    """
    funcion = clave if clave is not None else _identidad
    bajo, alto = 0, len(datos_ordenados) - 1
    while bajo <= alto:
        medio = (bajo + alto) // 2
        valor = funcion(datos_ordenados[medio])
        if valor == objetivo:
            return medio
        va_despues = valor > objetivo if descendente else valor < objetivo
        if va_despues:
            bajo = medio + 1
        else:
            alto = medio - 1
    return -1
