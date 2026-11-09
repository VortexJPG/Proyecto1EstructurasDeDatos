# Contract: `GET /v1/criptas/{dungeon_id}/llaves`

Referencia autoritativa: Swagger de Cripta API **v1.1.0**. Este documento
resume el contrato; no añade campos ni rutas.

## Request

```http
GET /v1/criptas/{dungeon_id}/llaves
X-Cripta-Client-Id: <uuid>
```

| Elemento | Obligatorio | Regla |
|---|---|---|
| `dungeon_id` (path) | sí | id de la cripta |
| `X-Cripta-Client-Id` (header) | sí | uuid estable por cliente; sin él el servicio responde 400 |
| Query params | — | ninguno |

La consulta **cuenta** dentro de `presupuesto_solicitudes` (`FR-019`).

## Response 200

```json
{
  "llaves": [
    { "id": "itm_llave_bronce", "sala": 4 },
    { "id": "itm_llave_negra", "sala": 12, "enemigo": "e-1203" }
  ]
}
```

| Campo | Tipo | Obligatorio | Significado |
|---|---|---|---|
| `llaves` | arreglo | sí | una entrada por ubicación |
| `llaves[].id` | string | sí | id de tipo de la llave |
| `llaves[].sala` | integer | sí | sala donde se obtiene |
| `llaves[].enemigo` | string \| null | no | instancia que la suelta; `sala` es su sala inicial |

**Interpretación** (`FR-016`, `FR-017`, `FR-024`):

- Sin `enemigo`: la llave está en el suelo de `sala`.
- Con `enemigo`: la llave está en `suelta` del tipo de esa instancia y se
  obtiene en la **sala inicial** del enemigo.
- Un mismo `id` puede aparecer varias veces; vale cualquier ubicación
  alcanzable.

## Errores

| Código | Cuerpo | Comportamiento esperado |
|---|---|---|
| 400 | `{"error": "..."}` | error de cliente (header o id inválido); no reintentar |
| 404 | `{"error": "..."}` | cripta inexistente; reportar |
| 429 | `{"error": "...", "reintentar_en": N}` | esperar N segundos y reintentar; el reintento cuenta |
| 500 | `{"error": "..."}` | contenido publicado inválido; reportar |

## Versión y persistencia

- La respuesta corresponde a la versión vigente de la cripta. No hay parámetro
  de versión.
- Se puede guardar como `llaves.json` con la versión con la que se obtuvo.
- Al cambiar la versión, la validación existente borra el archivo y se vuelve a
  consultar (`FR-018`, `FR-021`).
- Si el presupuesto se agota antes de la consulta, se informa el error y no se
  emite veredicto (`FR-020`).

## Ejemplo real (2026-11-09)

`cripta-06` (300 salas):

```json
{
  "llaves": [
    { "id": "itm_llave_bronce", "sala": 22 },
    { "id": "itm_llave_plata", "sala": 92 },
    { "id": "itm_llave_negra", "sala": 136 },
    { "id": "itm_llave_hierro", "sala": 247, "enemigo": "e-cripta-06-1" }
  ]
}
```
