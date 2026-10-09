# Contrato de medición

Dos registros, una línea JSON cada uno en stdout. Cloud Run y Agent Runtime los convierten en
`jsonPayload` de Cloud Logging; el sink de `infra/modulos/medicion` los copia a BigQuery.

## `llamada_modelo`

Lo emite `PluginMedicion` (`fundamentum_adk`) en cada llamada a un modelo, incluidos los
especialistas que corren como `AgentTool`.

| Campo | Tipo | Nota |
|---|---|---|
| `tipo` | `"llamada_modelo"` | |
| `app` | texto | `iterum`, `vocatio`, `domi` |
| `agente` | texto | nombre del agente de ADK |
| `invocacion`, `sesion` | texto | ids de ADK |
| `uid` | texto | `user_id` de la sesión |
| `usuario_interno` | bool | `state["usuario_interno"]`; excluye al fundador de las métricas |
| `modelo` | texto | normalizado, sin ruta ni `@versión` |
| `tokens_entrada` | entero | incluye los leídos de caché |
| `tokens_cache_lectura`, `tokens_cache_escritura` | entero | desglose de la entrada |
| `tokens_salida`, `tokens_pensamiento` | entero | el pensamiento se cobra como salida |
| `costo_usd` | número o nulo | nulo si el modelo no tiene precio |
| `latencia_ms` | entero | |
| `error` | texto o nulo | clase de la excepción o `precio_desconocido` |

## `resultado_entregado`

Lo emite la app cuando cumple el resultado que promete. Desde Python: `emitir_resultado(...)`.
Desde TypeScript basta escribir la misma línea en stdout:

```ts
console.log(JSON.stringify({
  severity: "INFO", message: "resultado_entregado", tipo: "resultado_entregado",
  app: "domi", resultado_tipo: "visita_agendada", resultado_id: inmuebleId, uid,
  usuario_interno: false,
}));
```

| App | `resultado_tipo` |
|---|---|
| Iterum | `viaje_planeado` (definición del roadmap) |
| Vocatio | la estrella del norte del PRD |
| Domi | `visita_agendada`: la marca el usuario; la app nunca contacta al anunciante |

## Vistas (dataset `fundamentum_medicion_vistas`)

- `v_llamadas`: una fila por llamada.
- `v_resultados`: una fila por resultado.
- `v_costo_diario`: costo, tokens, errores y p95 de latencia por día, app, agente y modelo, sin
  usuarios internos.
- `v_costo_por_resultado`: costo de modelos dividido entre resultados, por mes y app.

El costo de las vistas es una estimación con la tarifa estándar. Se concilia contra el export de
facturación. La diferencia esperada viene de las promociones (Gemini 3.8 Flash cuesta la mitad hasta
el 2026-12-31) y de las APIs que no son modelos (Places, Routes).
