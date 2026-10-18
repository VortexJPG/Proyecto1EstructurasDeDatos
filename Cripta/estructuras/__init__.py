"""Estructuras de datos implementadas por el grupo (§7).

Solo se usan estructuras vistas en el curso: arreglos, listas enlazadas
(también dobles), pilas, colas, montículo binario y colas de prioridad.

Reglas para TODO el proyecto:
- Prohibido usar ``dict`` como índice, caché o tabla de búsqueda
  → usar TablaOrdenada / ConjuntoOrdenado (arreglo ordenado + búsqueda binaria).
- Prohibido ``list.sort()`` y ``sorted()`` en los ordenamientos evaluados
  → usar ordenamiento.ordenar.
- ``list`` sí se permite como almacenamiento contiguo de bajo nivel (arreglo).

Responsable de cada archivo:
    tabla_ordenada.py   Persona B   (arreglo ordenado + búsqueda binaria)
    cola.py             Persona B   (cola con nodos enlazados)
    ordenamiento.py     Persona B   (inserción, mezcla y búsqueda binaria)
    lru.py              Persona B   (tabla ordenada + lista doble)
    monticulo.py        Persona A   (montículo binario: la cola de prioridad de la agenda)
    lista_doble.py      Persona A   (lista doblemente enlazada)
    buffer_circular.py  Persona A   (cola de tamaño fijo sobre un arreglo)
"""
