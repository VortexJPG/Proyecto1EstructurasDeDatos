# Quickstart: validar resolubilidad y llaves

Guía de validación de la capacidad. Los comandos describen el comportamiento
**esperado tras la implementación**; hoy `--verificar` y `--forzar` todavía no
existen.

## Requisitos

```bash
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

- Python 3.11+.
- Paquete offline actualizado con `crypta-05`/`cripta-06` y `llaves.json`
  (para validar sin red).
- Para probar contra el servicio: conexión y `X-Cripta-Client-Id` (lo genera el
  cliente).

## 1. Pruebas automatizadas

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Esperado: toda la suite en verde, incluida `tests/test_resolubilidad.py` con
pruebas que citan `AC-004-01..04`.

## 2. Verificar una cripta resoluble (offline)

```bash
.venv/bin/python main.py --verificar cripta-02 --offline
```

Esperado:

- `Veredicto: RESOLUBLE`.
- Orden de llaves con `itm_llave_bronce` antes de `itm_llave_negra`.
- Código de salida `0`.
- No se abre ninguna ventana ni se escribe `partida.log`.

## 3. Verificar una cripta no resoluble (offline)

```bash
.venv/bin/python main.py --verificar cripta-05 --offline
```

Esperado:

- `Veredicto: NO RESOLUBLE`.
- Secciones de llaves inobtenibles, frontera bloqueada y, si aplica, ciclo.
- Código de salida `3`.

## 4. Impedir el inicio de una partida imposible

```bash
.venv/bin/python main.py --cripta cripta-05 --offline --nombre Prueba
```

Esperado: no se inicia la partida, se imprime el reporte y se sale con código
`3`. No se crea bitácora de replay.

## 5. Forzar la partida

```bash
.venv/bin/python main.py --cripta cripta-05 --offline --forzar --nombre Prueba
```

Esperado: la partida inicia, el reporte completo aparece antes del primer estado
y el juego continúa normalmente.

## 6. Determinar el mismo orden dos veces

```bash
.venv/bin/python main.py --verificar cripta-02 --offline > /tmp/uno.txt
.venv/bin/python main.py --verificar cripta-02 --offline > /tmp/dos.txt
diff /tmp/uno.txt /tmp/dos.txt
```

Esperado: `diff` sin salida (`AC-004-03`).

## 7. Comparar con el oráculo

```bash
.venv/bin/python -m unittest tests.test_resolubilidad -v
```

Esperado: el verificador incremental coincide con el ingenuo en veredicto y en
el conjunto de llaves obtenibles para criptas sintéticas pequeñas (`SC-005`).

## 8. Medir el rendimiento

```bash
.venv/bin/python main.py --bench resolubilidad
```

Esperado:

- incremental vs. ingenuo para K creciente y tamaños crecientes;
- verificación real de 300 salas ≤ 200 ms (`SC-004`);
- semillas fijas, varias repeticiones y mediana/mínimo.

## 9. Trazabilidad de los escenarios

| Escenario | Cómo se valida |
|---|---|
| `AC-004-01` | `tests/test_resolubilidad.py` + `--verificar` de una cripta con ciclo |
| `AC-004-02` | `tests/test_resolubilidad.py` con llave en `suelta` de un errante |
| `AC-004-03` | pasos 2 y 6 (dos salidas idénticas) |
| `AC-004-04` | paso 4 (sin `--forzar` no inicia) |
