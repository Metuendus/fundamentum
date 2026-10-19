# Decisiones

## 1. Medición nativa de ADK, no un plugin propio (2026-10-10, reemplaza la de 0.1.0)

Se mide con lo que ya trae Google y el chasis solo agrega la tabla de precios:

- **Tokens y latencia:** `BigQueryAgentAnalyticsPlugin` de ADK escribe cada llamada a un modelo en
  `agentes.agent_events`, incluidos los especialistas que corren como `AgentTool`.
- **Árbol de cada conversación:** Cloud Trace, con `AdkApp(app=app, enable_tracing=True)`.
- **Costo:** la vista `costo_llamadas` cruza los tokens con `PRECIOS`, generada como SQL desde
  `fundamentum_modelos`. Una prueba falla si se desfasan.

Razones:
- El plugin propio (`PluginMedicion`) duplicaba lo que ADK ya hace, y obligaba a cada app a instalar
  el chasis desde Artifact Registry, incluso dentro de Agent Runtime.
- El costo es un cálculo sobre tokens, así que vive mejor en SQL, donde se puede recalcular hacia
  atrás si cambia un precio.

**Privacidad, no negociable:** la configuración estándar (`docs/adopcion.md`) quita `content` y
`content_parts`, no registra el estado de la sesión (`log_session_metadata=False`) ni sus cambios
(`STATE_DELTA`). Los usuarios internos se marcan por uid en la vista, no en el estado.

**Consecuencia:** ninguna llamada a un modelo fuera de ADK. Lo que no pasa por ADK no se mide ni se
traza. Cada app lo vigila con una prueba que falla si aparece `genai.Client` o `generate_content`
fuera de las pruebas.

## 2. Tarifa estándar, no promocional

Igual que la decisión 14 de Vocatio: subestimar el costo por resultado es peor que sobrestimarlo
cuando el número sostiene un precio de venta.

## 3. Multiproveedor solo dentro de Model Garden

`modelo_adk()` acepta `gemini-*` y `claude-*`. Claude se pide con la ruta completa
`projects/…/publishers/anthropic/models/…`, para no depender de `GOOGLE_CLOUD_LOCATION`, que Agent
Runtime reserva. ADK advierte que `output_schema` con herramientas es confiable en Gemini 3; en
otros modelos cae a `set_model_response`. Por eso Claude se evalúa primero en tareas sin
herramientas.

## 4. Núcleo público, firma privada (2026-10-19)

El fundador pivoteó a una firma de service-as-software que construye, opera y mantiene sistemas de IA para
agencias y equipos de marketing, con SLA. Fundamentum pasa a ser la base de su plataforma interna.

- **El chasis sigue público y genérico**, ahora con licencia Apache-2.0. Lo de marketing (conectores de Google
  Ads, Meta y GA4), lo de cada cliente y la operación (runbooks, reportes de SLA) viven en un repo privado
  encima de él.
- **Qué entra:** lo que usan dos consumidores (apps o plataforma de la firma) o lo que es estándar obligatorio.
- **Canarios:** Iterum y Domi adoptan cada versión primero; la firma fija la versión solo después de que pasen
  sus pruebas y evals. Vocatio se suma si adopta el chasis.
- **Candidatas para cuando un cliente real las pida:** costo, presupuesto y vistas por cliente (además de por
  usuario); SLO y alertas de disponibilidad y frescura por pipeline; datos para el reporte mensual de SLA.
