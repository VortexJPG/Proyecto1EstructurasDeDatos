# Estado — Persona B (CRIPTA Parte II)

> Bitácora de trabajo para retomar el contexto. Actualizar al cerrar cada fase
> y siempre que se tome una decisión que afecte a la Persona A.

## Fase actual

**Fase 1 — Auditoría y preparación.** Auditoría aprobada (2026-11-09).
Pendiente: verificar spec-kit cuando la Persona A lo inicialice y revisar
`.specify/memory/constitution.md`.

## Hecho

- Auditoría del repositorio de P1 completada (módulos, contratos, pruebas,
  `--bench`, Swagger).
- `.gitattributes` con `text=auto eol=lf` (commit `ec25931`).
- Paquete renombrado de `Cripta/` a `cripta/` para Linux/WSL (commit `6d8117b`).
- `.venv` con `requests` y `pygame-ce` 2.5.8: **91/91 pruebas en verde**.
- Línea base guardada:
  - `docs/mediciones/p1_linea_base.txt` (salida completa de `--bench`).
  - `docs/mediciones/p1_partida_cripta-02_semilla3.log` (victoria, 53
    acciones, reloj 3575; se reproduce con `--replay`).

## Decisiones de la auditoría

- Se normaliza a LF para que los commits sean atómicos (§1.4).
- El paquete se llama en minúsculas (`cripta`) porque los imports ya lo hacían
  así y el sistema de archivos de Linux distingue mayúsculas.
- Se deja `pygame-ce` instalado en `.venv`; la consola, `--replay`, `--bench`
  y `--verificar` no lo necesitan.

## Hallazgos que afectan a la Persona A

Interfaces que hay que acordar antes de implementarlas (no tocar módulos de A
sin avisar):

| Punto | Qué necesita B de A | Qué entrega B |
|---|---|---|
| Costo de salida | `Salida`/`Puerta` deben exponer `costo` y `Juego._mover` usarlo en vez de `COSTO_MOVER` | `DatosSalida.costo` leído del esqueleto (`None` → 100) |
| Enemigo cazador | `Comportamiento.desde_texto` debe aceptar `"cazador"` y la IA debe implementarlo | `Ficha.rango` leído del catálogo |
| Comando historia | La vista debe parsear `historia <t>` / `historia #k` | `TipoComando.HISTORIA` y su despacho en el controlador |
| Persistencia | `Juego.exportar_estado` / `Juego.desde_estado` deben incluir línea de tiempo y conocimiento | Formato binario v3 con detección explícita de P1 |
| Pergamino | El recorte de la línea al retroceder | Registro de deltas y puntos de control |

## Riesgos abiertos

- `Juego._mover` devuelve siempre `COSTO_MOVER = 100`: hoy el campo `costo`
  del servicio se descarta en silencio (`DatosSalida` no lo tiene).
- `Comportamiento.desde_texto("cazador")` lanza `ValueError`: cualquier ficha
  P2 con cazador rompe la carga hasta que A lo implemente.
- El guardado JSON de comparación no tiene envoltura de versión; hay que
  impedir que un archivo de P1 se cargue en silencio.
- El `--replay` actual solo conoce `version_cripta` y `version_catalogo`; no
  hay `--hasta`.
- `datos_ejemplo/` es de P1: sin `costo`, sin `rango`, sin `llaves.json`, sin
  criptas 05/06 y con versiones viejas de 02/03/04.

## Comandos

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python main.py --bench
.venv/bin/python main.py --offline --replay docs/mediciones/p1_partida_cripta-02_semilla3.log
```

## Siguiente

1. Verificar `specify check` y `/speckit.*` cuando A suba `.specify/`.
2. Revisar la constitución (7 principios) y proponer ajustes.
3. Fase 2: `/speckit.specify` de la spec 004 (resolubilidad y llaves).
