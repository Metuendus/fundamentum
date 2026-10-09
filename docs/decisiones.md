# Decisiones

## 1. Medición por línea JSON y sink, no solo con el plugin de BigQuery Agent Analytics

ADK trae `BigQueryAgentAnalyticsPlugin`, que registra tokens, latencia y contenido. Registra tokens,
no costo, y escribe directo a BigQuery con la Write API.

El chasis emite una línea JSON por llamada, con el costo ya calculado, y un sink de Cloud Logging la
lleva a BigQuery. Razones:

- Funciona igual en Cloud Run y en Agent Runtime, sin credenciales de BigQuery en el agente.
- El mismo contrato sirve para Vocatio antes de migrar a ADK y para la web en TypeScript.
- No guarda contenido de conversaciones. Es privacidad por defecto, y las tres apps manejan datos
  personales.

El plugin de ADK sigue disponible para depurar trayectorias y se puede agregar al `App` sin
conflicto.

## 2. Tarifa estándar, no promocional

Igual que la decisión 14 de Vocatio: subestimar el costo por resultado es peor que sobrestimarlo
cuando el número sostiene un precio de venta.

## 3. Multiproveedor solo dentro de Model Garden

`modelo_adk()` acepta `gemini-*` y `claude-*`. Claude se pide con la ruta completa
`projects/…/publishers/anthropic/models/…`, para no depender de `GOOGLE_CLOUD_LOCATION`, que Agent
Runtime reserva. ADK advierte que `output_schema` con herramientas es confiable en Gemini 3; en
otros modelos cae a `set_model_response`. Por eso Claude se evalúa primero en tareas sin
herramientas.
