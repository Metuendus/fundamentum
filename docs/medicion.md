# Medición

Tres piezas, todas nativas de Google salvo la tabla de precios:

| Pieza | Qué da | Dónde |
|---|---|---|
| `BigQueryAgentAnalyticsPlugin` (ADK) | tokens, latencia, modelo y agente de cada llamada | `agentes.agent_events` |
| Cloud Trace (`enable_tracing=True`) | el árbol de cada conversación | consola de Trace |
| Vistas de `infra/modulos/medicion` | costo en USD y costo por resultado | dataset `agentes` |

## Qué se registra y qué no

La configuración estándar está en [`adopcion.md`](adopcion.md). Con ella:

- **Sí:** tipo de evento, agente, `user_id`, sesión, invocación, `model` / `model_version`,
  `usage_metadata` (tokens), `latency_ms`, `finish_reason`, errores y `custom_tags.app`.
- **No:** el texto de prompts y respuestas (`content`, `content_parts`), el estado de la sesión ni
  sus cambios. Las tres apps manejan datos personales.

## Vistas

- `costo_llamadas`: una fila por respuesta final de un modelo, con `costo_usd` y
  `precio_desconocido`. El modelo se normaliza desde `model_version` (sin ruta ni `@versión`) y se
  le asigna el precio del prefijo más largo de `PRECIOS`. Un modelo sin precio deja el costo en
  nulo, nunca en 0.
- `costo_diario`: llamadas, errores, tokens, costo y p95 de latencia por día, app, agente y modelo,
  sin usuarios internos.
- `resultados`: los `resultado_entregado` de la app.
- `costo_por_resultado`: costo de modelos entre resultados, por mes y app.

`usuario_interno` sale de la variable `usuarios_internos` del módulo (lista de uids), así que
cambiar la lista corrige también la historia.

Los tokens de pensamiento se cobran como salida. La entrada leída de caché se cobra a la tarifa de
caché. El tramo de contexto largo (Claude Haiku 5.5 desde 100K tokens) se aplica por llamada.

## `resultado_entregado`

Lo emite la app cuando cumple el resultado que promete: una línea JSON en stdout que el sink del
módulo copia a `fundamentum_resultados`. Desde Python es la misma línea con `json.dumps`
(o `fundamentum_adk.emitir_resultado` si la app ya instala el chasis); desde TypeScript:

```ts
console.log(JSON.stringify({
  severity: "INFO", message: "resultado_entregado", tipo: "resultado_entregado",
  app: "domi", resultado_tipo: "visita_agendada", resultado_id: inmuebleId, uid,
}));
```

| App | `resultado_tipo` |
|---|---|
| Iterum | `viaje_planeado` (definición del roadmap) |
| Vocatio | la estrella del norte del PRD |
| Domi | `visita_agendada`: la marca el usuario; la app nunca contacta al anunciante |

## Conciliación

El costo de las vistas es una estimación con la tarifa estándar. Se concilia contra el export de
facturación. La diferencia esperada viene de las promociones (Gemini 3.8 Flash cuesta la mitad hasta
el 2026-12-31) y de las APIs que no son modelos (Places, Routes).
