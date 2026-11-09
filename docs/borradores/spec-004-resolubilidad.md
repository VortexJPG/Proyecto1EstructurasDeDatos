# Borrador — Spec 004: Resolubilidad y llaves (Parte II)

> **Estado:** borrador de contenido, pendiente de volcar con `/speckit.specify`
> cuando la Persona A inicialice `.specify/` y spec-kit v1.3.2 esté operativo.
> Este documento **no** es todavía el `spec.md` oficial.
>
> Regla de la §1.3: una `spec.md` describe reglas del juego, historias,
> escenarios y requisitos. **No nombra estructuras de datos, clases ni módulos.**
> Esas decisiones van en `plan.md`.

---

## 1. Por qué y prioridad

Antes de empezar a jugar, el jugador debe saber si la cripta publicada puede
ganarse. El servicio puede publicar criptas imposibles (por ejemplo, una llave
encerrada detrás de la única puerta que ella misma abre). Hoy el juego lo
descubre cuando ya es tarde: el jugador entra, gasta tiempo y pierde.

Esta capacidad permite:

1. verificar una cripta sin jugarla (`--verificar`);
2. impedir que una partida imposible empiece, salvo decisión explícita del
   jugador (`--forzar`);
3. explicar **por qué** no se puede ganar, con detalle suficiente para
   corregir la cripta o entender el bloqueo.

**Prioridad:** P1 (bloquea el inicio de la partida y es requisito de la
revisión del Apéndice B).

**Dependencias:**

- Contrato `GET /v1/criptas/<id>/llaves` (Swagger v1.1.0, autoritativo).
- Esqueleto completo de la cripta (salas, salidas, puertas y llaves).
- Presupuesto de solicitudes de la cripta.

**Fuera de alcance de esta spec:**

- El campo `costo` en las salidas y la ficha de enemigo con `rango`
  pertenecen a la spec 001 de la Persona A. La Persona B solo implementa su
  lectura en la capa de red, referenciando los `FR-xxx` de esa spec.
- El comportamiento del enemigo cazador y la ruta más barata (spec 001).
- La niebla de guerra, el mapa conocido y «ir a» (spec 003).

---

## 2. Historias de usuario

### HU-1 — Verificar antes de jugar (P1)

Como jugador, quiero ejecutar `--verificar <cripta>` y obtener un veredicto
claro sin entrar a la partida, para no perder tiempo en una cripta imposible.

**Aceptación:** el comando termina, imprime el reporte y **no instancia la
vista** ni escribe en `partida.log`.

### HU-2 — No empezar una partida imposible (P1)

Como jugador, si la cripta no es resoluble quiero que la partida **no inicie**
y ver el reporte, salvo que use `--forzar`.

**Aceptación:** sin `--forzar` no se crea partida; con `--forzar` sí, y el
reporte queda visible.

### HU-3 — Entender el bloqueo (P1)

Como autor de criptas, cuando una cripta no es resoluble quiero ver qué llaves
no pueden obtenerse, qué puertas forman la frontera bloqueada y, si existe, el
ciclo concreto de dependencias, para corregir el contenido.

### HU-4 — Orden de llaves reproducible (P2)

Como jugador, cuando la cripta es resoluble quiero un orden de obtención de
llaves en el que cada llave aparezca después de las necesarias para
alcanzarla, y que dos ejecuciones den el mismo orden.

### HU-5 — Ubicación de llaves desde el servicio (P1)

Como cliente del servicio, quiero consultar `GET /criptas/<id>/llaves` para
conocer dónde está cada llave, respetando el presupuesto de solicitudes y la
versión de la cripta.

---

## 3. Reglas (modelo de verificación)

### 3.1 Supuestos

- Se puede atravesar **cualquier salida abierta**.
- Se puede atravesar **cualquier salida cerrada cuya llave ya se obtuvo**.
- Las llaves **no se consumen** al abrir una puerta.
- **Todo enemigo puede ser derrotado**; si una llave está en el campo `suelta`
  de un enemigo, se considera obtenible **en la sala donde ese enemigo inicia**.
- **Trampas y cierres automáticos no bloquean**: una puerta puede reabrirse con
  la misma llave.
- La verificación usa el **estado inicial** del esqueleto (qué puertas empiezan
  cerradas), no el estado de una partida en curso.

### 3.2 Definición de resoluble

Una cripta es **resoluble** si, partiendo de `sala_inicial`, el jugador puede:

1. obtener `llave_salida`; y
2. llegar a `sala_salida` por una puerta que requiere `llave_salida`.

Si no se cumple (1) o (2), la cripta **no es resoluble**.

### 3.3 Orden de obtención

Si es resoluble, el reporte incluye una secuencia de llaves donde cada una
aparece **después** de todas las que hacen falta para alcanzarla.

- Puede haber varios órdenes válidos; cualquiera sirve.
- El orden debe ser **determinista**: mismas entradas ⇒ mismo orden.
- Desempate propuesto (a confirmar en `clarify`): menor id de llave primero.

### 3.4 Reporte de no resolubilidad

Debe incluir, como mínimo:

- las **llaves que no pueden obtenerse**;
- las **puertas de la frontera bloqueada**: cerradas y adyacentes a la región
  alcanzable, con la llave que requiere cada una;
- **dónde se encuentra** cada una de esas llaves (sala; y enemigo, si aplica);
- si una llave está detrás de puertas que **solo ella abre** (directamente o
  por cadena de llaves), el **ciclo concreto** como secuencia de llaves/puertas.

El reporte debe ser legible por una persona, no solo un booleano.

---

## 4. Banderas y comportamiento

| Bandera | Comportamiento |
|---|---|
| `--verificar <cripta>` | Ejecuta solo la verificación e imprime el reporte. No instancia la vista. No escribe en `partida.log`. |
| `--forzar` | Permite iniciar una partida en una cripta no resoluble. El reporte sigue disponible. |
| (sin bandera) | Al iniciar partida se verifica; si no es resoluble, **no inicia** y muestra el reporte. |
| `--offline` | La verificación funciona con el paquete local (`llaves.json` incluido), sin red. |

---

## 5. Contrato del servicio

Referencia autoritativa: Swagger v1.1.0
(`GET /v1/criptas/{dungeon_id}/llaves`).

```json
{
  "llaves": [
    { "id": "itm_llave_bronce", "sala": 4 },
    { "id": "itm_llave_negra", "sala": 12, "enemigo": "e-1203" }
  ]
}
```

- `id`: id de tipo de la llave.
- `sala`: sala donde se obtiene; si hay `enemigo`, es la sala **inicial** del
  enemigo.
- `enemigo` (opcional): instancia cuyo tipo tiene la llave en `suelta`.
- La respuesta es válida mientras coincida la **versión de la cripta**.
- **Puede persistirse**; se invalida con la validación de versión existente.
- La consulta **cuenta dentro de `presupuesto_solicitudes`**.
- Si el presupuesto está agotado, se informa el error; no se inventa un
  veredicto.

---

## 6. Requisitos funcionales

### 6.1 Verificación

- **FR-001.** Antes de iniciar una partida, el sistema determina si la cripta
  es resoluble usando el esqueleto y la ubicación de llaves.
- **FR-002.** La verificación aplica los supuestos de §3.1.
- **FR-003.** Una cripta es resoluble según §3.2; en caso contrario se reporta
  como no resoluble.
- **FR-004.** Si es resoluble, se devuelve un orden de obtención que cumple
  §3.3.
- **FR-005.** El orden de obtención es determinista entre ejecuciones con las
  mismas entradas.
- **FR-006.** Si no es resoluble, el reporte incluye todos los elementos de
  §3.4.
- **FR-007.** El reporte identifica el ciclo concreto cuando una llave depende
  de sí misma, directa o por cadena.
- **FR-008.** Una cripta no resoluble impide iniciar la partida salvo
  `--forzar`.
- **FR-009.** `--verificar <cripta>` ejecuta solo la verificación, sin
  instanciar la vista.
- **FR-010.** La verificación se integra al inicio de partida y su resultado
  es visible para el jugador.
- **FR-011.** `--forzar` inicia la partida y conserva accesible el reporte de
  no resolubilidad.
- **FR-012.** El veredicto y el orden no dependen de datos de una cripta
  concreta escritos en el código.
- **FR-013.** La verificación puede ejecutarse sin red con `--offline` cuando
  el paquete local contiene la información de llaves.

### 6.2 Llaves y servicio

- **FR-014.** El cliente obtiene las ubicaciones de llaves desde
  `GET /v1/criptas/<id>/llaves` conforme a §5.
- **FR-015.** Si una llave trae `enemigo`, se ubica en la sala inicial de esa
  instancia y se considera obtenible al derrotarlo.
- **FR-016.** La respuesta de llaves se invalida cuando cambia la versión de la
  cripta, usando la validación de versión existente.
- **FR-017.** La consulta de llaves cuenta dentro de `presupuesto_solicitudes`.
- **FR-018.** Un agotamiento de presupuesto produce un error explícito, no un
  veredicto silencioso.
- **FR-019.** La respuesta de llaves puede persistirse y reutilizarse mientras
  la versión coincida.
- **FR-020.** Si una llave requerida por una puerta no aparece en la respuesta
  de llaves, se reporta como no obtenible y la cripta como no resoluble.

### 6.3 Casos ambiguos (a confirmar en `clarify`)

- **FR-021.** Llave duplicada (mismo `id` en dos ubicaciones): se considera
  obtenible si **alguna** ubicación es alcanzable; el reporte usa un orden
  determinista (propuesta: menor sala).
- **FR-022.** Sala inicial de un enemigo que porta una llave inalcanzable: la
  llave se reporta como no obtenible, indicando enemigo y sala inicial.
- **FR-023.** `llave_salida` ausente de la respuesta de llaves: la cripta es no
  resoluble y el reporte lo dice explícitamente.
- **FR-024.** Salida con `llave` pero `cerrada == false`: se considera abierta
  (la llave solo importa si la puerta empieza cerrada).

---

## 7. Requisitos de rendimiento

- **NFR-001.** La verificación de la cripta publicada más grande (hoy 300
  salas) debe completarse en **≤ 200 ms**.
- **NFR-002.** El costo debe crecer aproximadamente de forma lineal en
  (salas + salidas + llaves); no se acepta repetir el recorrido una vez por
  llave como solución final.
- **NFR-003.** Los límites de `--bench` deben ser **configurables**, no
  constantes escritas en el código.
- **NFR-004.** Las mediciones usan semillas fijas y varias repeticiones, y
  reportan mediana o mínimo.
- **NFR-005.** La verificación debe compararse contra una implementación
  ingenua (recorrido repetido por llave) en criptas sintéticas pequeñas y
  coincidir en veredicto y conjunto de llaves obtenibles.

---

## 8. Escenarios de aceptación (Apéndice B — Resolubilidad)

Cada escenario debe convertirse en una prueba automatizada que cite su ID.

### AC-004-01 — Llave de salida detrás de su propia puerta

**Dado** una cripta donde `llave_salida` está detrás de la única puerta que
ella misma abre,
**cuando** se verifica,
**entonces** el veredicto es **no resoluble** y el reporte **señala el ciclo**
de forma concreta.

### AC-004-02 — Llave soltada por un enemigo errante

**Dado** una llave en el campo `suelta` de un enemigo errante que inicia en la
sala X,
**cuando** se verifica,
**entonces** la llave se ubica en la **sala inicial del enemigo** (X), no donde
el enemigo esté en un instante posterior.

### AC-004-03 — Varios órdenes válidos

**Dado** una cripta con más de un orden válido de obtención de llaves,
**cuando** se verifica dos veces con las mismas entradas,
**entonces** las dos ejecuciones producen **el mismo orden**.

### AC-004-04 — Partida bloqueada sin `--forzar`

**Dado** una cripta no resoluble,
**cuando** se intenta iniciar la partida sin `--forzar`,
**entonces** la partida **no inicia** y se muestra el reporte.

---

## 9. Preguntas para `/speckit.clarify`

Cada una con una opción por defecto propuesta para que la decida el grupo:

1. **¿Llave duplicada?** → *Por defecto:* vale si alguna ubicación es
   alcanzable; orden determinista por menor sala.
2. **¿Puerta cerrada con llave no listada?** → *Por defecto:* no obtenible ⇒ no
   resoluble, con la puerta y la llave faltante en el reporte.
3. **¿Sala inicial de un enemigo inalcanzable?** → *Por defecto:* la llave no es
   obtenible; se reporta enemigo y sala.
4. **¿`llave_salida` no aparece?** → *Por defecto:* no resoluble, con motivo
   explícito.
5. **¿Qué significa «llegar a `sala_salida` por una puerta que la requiere» si
   también se llega por una salida libre?** → *Por defecto:* se exige que
   exista una entrada a `sala_salida` que requiera `llave_salida`; si no
   existe, se reporta como no resoluble con ese motivo. *(Decisión de grupo;
   afecta a criptas reales.)*
6. **¿La respuesta de `/llaves` se pide antes o después de conocer el
   presupuesto?** → *Por defecto:* primero `datos_cripta` (fija el
   presupuesto), después `/llaves`.
7. **¿Qué hace `--verificar` si se agota el presupuesto?** → *Por defecto:*
   termina con error claro y código de salida distinto de 0.
8. **¿`--verificar` exige el id de la cripta?** → *Por defecto:* sí; sin id es
   un error de uso.
9. **¿El reporte de `--forzar` se muestra siempre o solo al inicio?** →
   *Por defecto:* se muestra al inicio y queda disponible en la ayuda/estado.
10. **¿Una salida con `cierre_automatico` y sin `llave` puede bloquear?** →
    *Por defecto:* no; los cierres automáticos no bloquean (§3.1).

---

## 10. Criterios de éxito

- [ ] Los 4 escenarios de §8 pasan como pruebas automatizadas.
- [ ] El mismo par (cripta, versión) produce siempre el mismo veredicto y
      orden.
- [ ] El reporte de no resolubilidad incluye frontera, llaves inobtenibles,
      ubicaciones y ciclo concreto cuando aplica.
- [ ] El verificador coincide con el oráculo ingenuo en criptas sintéticas.
- [ ] ≤ 200 ms en la cripta publicada más grande (o desviación documentada).
- [ ] `--verificar` no instancia la vista ni escribe en `partida.log`.
- [ ] El presupuesto de solicitudes se respeta, incluida la consulta de llaves.
- [ ] No se usan estructuras prohibidas (se valida en `plan.md`).
