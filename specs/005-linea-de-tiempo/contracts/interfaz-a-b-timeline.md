# Contract: interfaz B → A para la línea de tiempo

Lo que la Persona B necesita de la Persona A (y lo que entrega) para §5.5.

## 1. Avance con límite de tiempo

### Lo que necesita B

```python
class Juego:
    def avanzar_hasta(self, tiempo: int) -> None:
        """Ejecuta eventos de la agenda mientras su tiempo sea <= ``tiempo``.
        No ejecuta acciones del jugador ni consume la decisión pendiente."""

    def ejecutar_accion(self, accion: Accion, hasta: int | None = None) -> ResultadoAccion:
        """Con ``hasta``: aplica la acción y avanza eventos solo hasta ese
        instante. Sin ``hasta``: comportamiento actual (hasta la próxima
        decisión)."""
```

**Por qué.** Reconstruir `historia <t>` con t entre decisiones exige detenerse
en t; hoy `ejecutar_accion` avanza hasta la siguiente decisión y se pasa.

**Reglas**

- No cambia ninguna regla del juego: solo el punto de parada.
- `hasta` nunca es menor que el reloj actual.
- Si la partida termina antes de `hasta`, se detiene y deja el estado final.

### Lo que entrega B

- La llamada correcta desde la línea y desde `--replay --hasta`.
- Pruebas de equivalencia con el oráculo de re-simulación.

## 2. Conocimiento del mapa

### Lo que necesita B

```python
class Juego:
    def serializar_conocimiento(self) -> str: ...
    def restaurar_conocimiento(self, datos: str) -> None: ...
```

- `serializar_conocimiento` devuelve una representación estable del mapa
  conocido (salas exploradas, contenido visible, lo que defina A).
- `restaurar_conocimiento` la aplica a un juego reconstruido.
- El estado guardable incluye ese texto como `conocimiento`.

Hasta que A lo entregue, B usa un doble de prueba con una lista de salas
conocidas.

### Lo que entrega B

- El campo `conocimiento` en la línea y en el formato v3.
- El resumen histórico lo muestra sin interpretarlo.

## 3. Comando `historia`

### Contrato A↔B

```python
class TipoComando(Enum):
    ...
    HISTORIA = "historia"   # argumento: "1200" o "#4"

@dataclass
class ComandoUsuario:
    tipo: TipoComando
    accion: Accion | None = None
    argumento: str | None = None
```

- La vista (A) parsea `historia 1200` / `historia #4` y entrega el argumento.
- El controlador (B) valida, reconstruye y devuelve `ResumenHistorico` o un
  error.
- La vista (A) implementa:

```python
class VistaBase:
    def mostrar_historia(self, resumen: ResumenHistorico) -> None: ...
```

- La vista **no** calcula la reconstrucción ni consulta el servicio.
- `historia` no se registra en `partida.log` ni avanza el reloj.

## 4. Lo que B NO toca

- `Juego._despachar`, `_avanzar_hasta_decision`, la agenda y el mapa son de A.
  B solo usa las operaciones públicas acordadas.
- La vista es de A; B entrega el resumen y el texto ya formateado si hace falta.

## 5. Criterio de aceptación de la interfaz

- `historia <t>` con t entre dos decisiones devuelve el estado en t, no el de la
  siguiente decisión.
- Reconstruir un checkpoint y re-simular K acciones da el mismo estado que
  re-simular desde cero (oráculo).
- `historia` no altera la partida viva.
