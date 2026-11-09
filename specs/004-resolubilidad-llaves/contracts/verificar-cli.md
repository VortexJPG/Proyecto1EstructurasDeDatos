# Contract: `--verificar` y `--forzar`

Contrato de la interfaz de línea de comandos para la verificación de
resolubilidad (`FR-010..FR-013`, `FR-005`, `FR-008`).

## Banderas

```bash
python main.py --verificar <cripta> [--offline [DIR]] [--datos DIR]
python main.py --cripta <cripta> [--forzar] [--offline [DIR]]
```

| Bandera | Efecto |
|---|---|
| `--verificar <cripta>` | Ejecuta solo la verificación, imprime el reporte y termina. **No** instancia la vista, no escribe `partida.log`, no crea partida. |
| `--forzar` | Permite iniciar una partida en una cripta no resoluble. Sin efecto en `--verificar`. |
| `--offline [DIR]` | Usa el paquete local (incluye `llaves.json`); no consume presupuesto. |
| `--datos DIR` | Directorio de caché local (por defecto `datos_locales/`). |

Sin `--forzar`, si la cripta no es resoluble la partida **no inicia**: se
imprime el reporte y se termina con código 3.

## Salida (texto)

### Cripta resoluble

```text
Verificación de cripta-02 (versión 52532a77ee04)
Veredicto: RESOLUBLE
Orden de llaves: itm_llave_bronce, itm_llave_negra
Llaves obtenidas: 2 de 2
Solicitudes: 3/23
```

### Cripta no resoluble

```text
Verificación de cripta-05 (versión 48bfa3b75055)
Veredicto: NO RESOLUBLE
Motivo: la llave de salida no es obtenible

Llaves inobtenibles:
  - itm_llave_negra (sala 23)
  - itm_llave_hierro (sala 24)

Frontera bloqueada:
  - p-22E-23: sala 22 -> sala 23 (E), requiere itm_llave_negra
  - p-23N-24: sala 23 -> sala 24 (N), requiere itm_llave_hierro

Ciclo:
  itm_llave_negra -> p-22E-23 (requiere itm_llave_negra) -> itm_llave_negra
```

El formato exacto de cada línea puede ajustarse en implementación, pero deben
aparecer **todas** las secciones del reporte (`FR-008`) y el ciclo concreto
cuando exista (`FR-009`).

## Códigos de salida

| Código | Significado |
|---|---|
| 0 | verificación completada; la cripta es resoluble (o la partida inició) |
| 1 | error de datos, archivo o red (incluye presupuesto agotado) |
| 2 | replay incompatible (código ya existente en P1) |
| 3 | cripta verificada y **no resoluble**; la partida no inicia |
| 130 | interrupción del usuario |

## Garantías

- `--verificar` no importa ni instancia `pygame`/la vista (`FR-012`).
- No se escribe ninguna línea en la bitácora de partida (`partida.log`).
- No se ejecuta ninguna acción ni se avanza el reloj virtual.
- El reporte se calcula solo con el esqueleto y las ubicaciones de llaves.

## Integración con el inicio de partida

1. `--cripta` (o la selección interactiva) y datos generales.
2. Verificación.
3. Si es resoluble → partida normal; el reporte resumido se muestra al inicio
   (`FR-013`).
4. Si no es resoluble y hay `--forzar` → se muestra el reporte completo con una
   advertencia y la partida continúa (`FR-011`).
5. Si no es resoluble y no hay `--forzar` → reporte completo y salida 3, sin
   crear partida ni bitácora (`FR-010`).
