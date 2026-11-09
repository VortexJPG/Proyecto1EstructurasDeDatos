# Contract: interfaz B → A (costo, rango, cazador y reporte)

Punto 1 de la tabla de contactos (§3): lo que la Persona B entrega a la
Persona A para la Parte II. **No** implementa comportamiento de A.

## 1. Costo de salida

### Dato de entrada (servicio)

`Exit.costo` (Swagger v1.1.0): entero ≥ 1 o nulo.

- Ausente o `null` ⇒ **100**.
- El valor es parte del esqueleto y se persiste con él.

### Lo que entrega B

| Elemento | Tipo | Regla |
|---|---|---|
| `DatosSalida.costo` (`modelo/datos.py`) | `int \| None` | leído del JSON; `None` si no viene |
| `esqueleto.json` | campo `costo` | se escribe solo si el servicio lo trajo |
| `Salida.costo` (`modelo/mapa.py`, A) | `int` | valor efectivo; `None` se resuelve a 100 |

### Lo que debe hacer A

- Exponer el costo en la salida y usarlo en `Juego._mover` en lugar de la
  constante fija `COSTO_MOVER = 100` (regla de la Parte II; FR de la spec 001 de
  A, **IDs por coordinar**).
- Mantener el valor por defecto 100 cuando el servicio no lo traiga.

### Validación

- Si `costo` viene y no es entero ≥ 1, el esqueleto es inválido y se informa el
  error; no se corrige en silencio.

## 2. Ficha de enemigo cazador y rango

### Dato de entrada (servicio)

`Enemy` (Swagger v1.1.0):

- `comportamiento` ∈ `guardián | errante | rastreador | cazador`;
- `rango`: entero ≥ 1 o nulo.

### Lo que entrega B

| Elemento | Tipo | Regla |
|---|---|---|
| `Ficha.rango` (`modelo/datos.py`) | `int \| None` | leído del catálogo |
| Persistencia de la ficha | JSON | `asdict` ya incluye el campo |
| Lectura de `cazador` | texto | B lo transporta; **no** lo interpreta |

### Lo que debe hacer A

- Añadir `CAZADOR` a `Comportamiento` y aceptar `"cazador"` en
  `Comportamiento.desde_texto` (hoy lanza `ValueError`).
- Exponer `rango` en la instancia de enemigo y usarlo en la IA (comportamiento
  cazador; FR de la spec 001 de A, **IDs por coordinar**).

### Validación

- Si `comportamiento == "cazador"` y `rango` falta o no es ≥ 1, la ficha es
  inválida: se informa y no se inventa un rango.

## 3. Reporte de resolubilidad en la vista

### Lo que entrega B

`ResultadoVerificacion` (ver `data-model.md`) disponible desde el controlador
antes de la primera decisión, y el texto del reporte ya formateado:

```python
controlador.reporte_resolubilidad() -> ResultadoVerificacion | None
controlador.texto_resolubilidad() -> str
```

### Lo que debe hacer A

- La vista (consola y ventana) muestra el reporte al iniciar la partida
  (`FR-013`).
- Para una cripta no resoluble con `--forzar`, muestra el reporte completo con
  una advertencia antes del primer estado (`FR-011`).
- La vista **no** calcula el veredicto ni consulta el servicio: solo presenta lo
  que entrega el controlador.

### Interfaz sugerida

```python
class VistaBase:
    def mostrar_resolubilidad(self, resultado: ResultadoVerificacion) -> None: ...
```

## 4. Lo que B NO toca

- `Mapa.construir`, `Mapa.incorporar_contenido`, la IA, `Juego._mover` y la
  vista son de A. B solo entrega los datos y el reporte descritos arriba.
- Cualquier cambio en estos archivos se acuerda como petición de interfaz y va
  en un commit aparte.

## 5. Criterio de aceptación de la interfaz

- Una ficha con `comportamiento: "cazador"` y `rango: 300` se lee sin error y
  llega a A con el rango intacto.
- Un esqueleto con `"costo": 250` produce un costo de movimiento de 250; sin
  `costo`, de 100.
- El reporte de `--verificar` y el del inicio de partida son el mismo objeto
  (mismo veredicto y mismo orden).
