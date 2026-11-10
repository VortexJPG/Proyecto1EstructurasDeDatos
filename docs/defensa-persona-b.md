# Defensa — Persona B (CRIPTA Parte II)

Resumen de una página por especificación, recorrido de trazabilidad y ensayo de
cambio de regla. Sirve para que **cualquier** integrante pueda explicar la
Parte B.

## 1. Spec 004 — Resolubilidad y llaves (una página)

**Qué resuelve.** Antes de jugar se decide si la cripta puede ganarse. Si no,
la partida no inicia salvo `--forzar`; el reporte explica el bloqueo.

**Regla.** Se puede cruzar toda salida abierta y toda cerrada cuya llave ya se
tenga. Las llaves no se consumen; los enemigos pueden soltarlas en su sala
inicial; trampas y cierres automáticos no bloquean. Es resoluble si se obtiene
`llave_salida` y se entra a `sala_salida` por una puerta que la requiera
(condición estricta, decisión del grupo).

**Estructura.** Un **recorrido incremental único** con cola FIFO. Las puertas
cerradas se retienen en una lista por llave; al obtener la llave se liberan solo
esas puertas y se sigue. El mismo recorrido produce orden de llaves, frontera,
llaves inobtenibles y ciclo concreto. Nada de `dict`/`set`/`heapq`/`bisect`/
`collections`/`networkx`.

**Complejidad.** O(R + E + D + K log K). El ingenuo repetido es O(K·(R+E)).

**Evidencia.** `--bench resolubilidad`: en 5000 salas el incremental queda en
~16–17 ms para K = 5..80 y el ingenuo crece de 11 a 57 ms; en 300 salas,
~0.9 ms (límite 200 ms). `cripta-05` real: no resoluble con ciclo
`hierro → negra → hierro`. Coincide con el oráculo en criptas sintéticas.

**Límite.** Para K pequeño el ingenuo tiene menor constante; el incremental
gana al crecer K. `rango`/`cazador` dependen del comportamiento de A.

## 2. Spec 005 — Línea de tiempo (una página)

**Qué resuelve.** `historia <t>` / `historia #k` muestran el pasado sin tocar la
partida, sin reloj y sin `partida.log`. El pergamino recorta la línea. Guardar
y cargar conserva todo; un archivo de P1 se rechaza.

**Estructura.** Línea = **acciones + contenido nuevo + checkpoints cada K**.
Cada checkpoint es un `EstadoGuardable` completo con `random.Random`. La
consulta busca el checkpoint con **búsqueda binaria propia**, reconstruye en un
`Mapa` propio con fichas de solo lectura y re-simula **≤ K acciones**; si el
instante cae entre decisiones, avanza eventos hasta t.

**Complejidad.** Consulta O(K acciones + eventos del intervalo), nunca O(n).
Memoria O(acciones + contenido + (n/K)·estado). Recorte por posición.

**Evidencia.** 5000 acciones:

| K | Consulta | Memoria checkpoints |
|---:|---:|---:|
| 10 | 0.41 ms | 2.95 MB |
| 25 | 0.59 ms | 1.16 MB |
| 50 | 0.81 ms | 0.58 MB |
| 100 | 1.13 ms | 0.29 MB |
| sin CP | 99 ms | 0.006 MB |

K = 50 por defecto; sin checkpoints se excede el límite de 50 ms. El estado
reconstruido coincide con el oráculo de re-simulación y `historia` no altera
reloj, log ni historial.

**Límite.** `historia <t>` entre decisiones depende de `Juego.avanzar_hasta`
(A). La ventana aún no tiene acceso por teclado a `historia`.

## 3. Specs de la Persona A (resumen para la defensa)

Los artefactos de spec-kit de A (001–003) aún no están en el repositorio. Según
el documento de la Parte II cubren:

- **Spec 001 — terreno y cazador:** costo de salida (`costo`), ficha de
  cazador con `rango`, comportamiento de cazador y movimiento con costo.
- **Spec 002 — invalidación de rutas:** recalcular la ruta cuando cambia el
  terreno.
- **Spec 003 — niebla de guerra e «ir a»:** mapa conocido y desplazamiento
  automático.

La Persona B entrega a A la lectura de `costo` y `rango`, la interfaz
`Salida.costo`/`Enemigo.rango`/`Comportamiento.CAZADOR` y el reporte de
resolubilidad (`contracts/interfaz-a-b.md`). A debe confirmar su spec 001 antes
de que B consuma esos datos en el modelo.

## 4. Recorrido de trazabilidad (2 requisitos)

### FR-005 (spec 004) — condición estricta de `sala_salida`

1. **Escenario/spec:** `specs/004.../spec.md` FR-005 y el escenario
   «salida libre no basta».
2. **Tarea:** `T016` y `T024` de `tasks.md` 004.
3. **Código:** `Verificador._salida_por_puerta_con_llave` en
   `cripta/modelo/verificacion.py`.
4. **Prueba:** `tests/test_resolubilidad.py::test_salida_libre_no_basta` y
   `test_puerta_de_salida_con_llave`.
5. **Evidencia:** `cripta-05` real no resoluble; `cripta-02` y `cripta-06`
   resolubles.

### FR-011 (spec 005) — el pergamino recorta la línea

1. **Escenario/spec:** `specs/005.../spec.md` FR-011 y `AC-005-02`.
2. **Tarea:** `T028`/`T029` de `tasks.md` 005.
3. **Código:** `LineaTiempo.recortar` en `cripta/modelo/timeline.py`, llamado
   desde `Controlador.ejecutar_accion` al aceptar `RETROCEDER`.
4. **Prueba:** `tests/test_timeline.py::test_recorte_por_pergamino`.
5. **Evidencia:** tras el pergamino, `len(linea.acciones)` es igual a
   `acciones_ejecutadas` y no quedan checkpoints posteriores.

## 5. Ensayo de cambio pequeño de regla

Cambio propuesto (no ejecutado, para el ensayo): que el mensaje de `--hasta`
posterior al final incluya también el reloj final.

1. **Spec primero:** actualizar FR-024 en
   `specs/005-linea-de-tiempo/spec.md` y su escenario; commit
   `fix(spec): precisar el mensaje de --hasta posterior al final`.
2. **Código después:** cambiar `ReproductorReplay.describir_hasta` y la prueba
   `test_hasta_despues_del_final`; commit
   `feat(historia): incluir el reloj final en el mensaje de --hasta`.
3. **Verificación:** suite completa y `--bench timeline` sin regresiones.

En la defensa se puede mostrar el diff de los dos commits y explicar por qué la
spec va primero (constitución VII).

## 6. Lista de verificación (§8.3)

- [x] Specs 004 y 005 confirmadas antes que su código; correcciones de spec en
      commits separados (`fix(spec)` de NFR).
- [ ] Los 10 casos del Apéndice B: **9/10** con prueba; `AC-005-03` (mismo
      instante entre decisiones) pendiente de `avanzar_hasta` (A).
- [x] Las specs no nombran estructuras; los planes no introducen reglas nuevas.
- [x] Sin `dict`, `set`, `heapq`, `bisect`, `collections`, `networkx` en los
      problemas evaluados (prueba de auditoría).
- [x] Determinismo (dos corridas idénticas, oráculo).
- [x] `--replay`, `--bench` y `--verificar` no instancian la vista.
- [x] Presupuesto de solicitudes respetado, incluida `/llaves`.
- [x] Sin datos de cripta concreta en el código.
- [x] Archivos de P1 no se cargan en silencio; lo persistido se invalida por
      versión.
- [x] `PROMPTS_LLM.md` con todos los prompts y comandos de spec-kit.

## 7. Riesgos para la defensa

- `AC-005-03` es el requisito más vulnerable: si A no entrega
  `Juego.avanzar_hasta`, hay que explicar la limitación y el rechazo explícito.
- `cazador`/`rango`: B transporta los datos, pero A debe aceptar el
  comportamiento; una ficha con cazador todavía rompe `Comportamiento`.
- La ventana no tiene acceso a `historia`; sí la consola.
- La precarga asíncrona puede cargar salas no visitadas en momentos distintos;
  el resumen usa salas visitadas, así que no afecta la historia jugable.
