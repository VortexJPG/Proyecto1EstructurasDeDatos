# Implementation Plan: Fin de partida y cripta no resoluble en la interfaz

**Branch**: `006-fin-de-partida` | **Date**: 2026-11-17 | **Spec**: [spec.md](./spec.md)

## Summary

El controlador repite el ciclo de partida mientras la vista responda
«Reintentar» al ganar o morir (`Vista.pedir_reintentar`). Para reintentar no se
vuelve a preparar la cripta: se reconstruye el mapa con el esqueleto ya cargado,
se reutiliza la caché de catálogo y se monta una precarga nueva que lee de disco
lo ya descargado (`Controlador.reiniciar_partida`). Al elegir de la lista una
cripta no resoluble, el controlador llama a `Vista.mostrar_no_resoluble` y vuelve
a la lista; con `--cripta` sigue saliendo con código 3.

## Technical Context

**Language/Version**: Python 3.11+. **Dependencies**: pygame-ce solo para la
ventana. **Testing**: `unittest` (ventana con el controlador de video "dummy").
**Constraints**: no cambia reglas ni estructuras de datos; sin `dict`/`set`.

## Constitution Check

| Principio | Resultado |
|---|---|
| I. Estructuras a mano | PASA: no agrega estructuras. |
| II. Determinismo | PASA: cada partida es una partida normal con su semilla y su log. |
| III. MVC sin vista | PASA: `--replay`, `--bench` y `--verificar` no pasan por estas pantallas. |
| IV. Sin datos de cripta | PASA. |
| V. Presupuesto | PASA: la lista se pide una vez y reintentar lee de disco. |
| VI. Rendimiento | N/A (interfaz). |
| VII. Spec antes que código | PASA: esta spec se confirma antes que el código. |

## Módulos afectados

```text
cripta/controlador/controlador.py  # ciclo con reintentar, reiniciar_partida, _montar_precarga,
                                   #   volver a la lista con una cripta no resoluble
cripta/vista/base.py               # pedir_reintentar y mostrar_no_resoluble por defecto
cripta/vista/vista_consola.py      # pregunta [R] / [S]
cripta/vista/vista_grafica.py      # botones de la pantalla final, pantalla del reporte,
                                   #   cuadro de controles que se ajusta a la lista
tests/test_reintentar.py, tests/test_interfaz_a_b.py, tests/test_vista_grafica.py
```

## Trazabilidad

| Requisitos | Tareas |
|---|---|
| FR-001, FR-002, FR-003, FR-004, FR-005, FR-006 | T002, T003 |
| FR-007 | T004 |
| FR-008 | T005 |
| FR-009, FR-010, FR-011 | T006, T007 |
| FR-012 | T002, T006 |
