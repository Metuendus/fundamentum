-- Una fila por llamada a un modelo, desde la tabla que escribe el plugin oficial de ADK
-- (BigQueryAgentAnalyticsPlugin, `agent_events`), con su costo según la tabla de precios.
-- Solo respuestas finales: las parciales del streaming no traen finish_reason.
WITH
precios AS (
${precios}
),
pedidos AS (
  SELECT span_id, JSON_VALUE(attributes, '$.model') AS modelo_pedido
  FROM `${proyecto}.${agentes}.agent_events`
  WHERE event_type = 'LLM_REQUEST'
),
respuestas AS (
  SELECT
    e.timestamp,
    e.event_id,
    JSON_VALUE(e.attributes, '$.custom_tags.app') AS app,
    e.agent AS agente,
    e.user_id AS uid,
    e.session_id AS sesion,
    e.invocation_id AS invocacion,
    -- El estado de la sesión no se registra (privacidad); los internos se listan por uid.
    e.user_id IN UNNEST(ARRAY<STRING>${usuarios_internos}) AS usuario_interno,
    REGEXP_EXTRACT(
      COALESCE(JSON_VALUE(e.attributes, '$.model_version'), p.modelo_pedido), r'([^/@]+)(?:@.*)?$'
    ) AS modelo,
    IFNULL(CAST(JSON_VALUE(e.attributes, '$.usage_metadata.prompt_token_count') AS INT64), 0)
      + IFNULL(CAST(JSON_VALUE(e.attributes, '$.usage_metadata.tool_use_prompt_token_count') AS INT64), 0)
      AS tokens_entrada,
    IFNULL(CAST(JSON_VALUE(e.attributes, '$.usage_metadata.cached_content_token_count') AS INT64), 0)
      AS tokens_cache_lectura,
    IFNULL(CAST(JSON_VALUE(e.attributes, '$.usage_metadata.candidates_token_count') AS INT64), 0)
      AS tokens_salida,
    IFNULL(CAST(JSON_VALUE(e.attributes, '$.usage_metadata.thoughts_token_count') AS INT64), 0)
      AS tokens_pensamiento,
    CAST(JSON_VALUE(e.latency_ms, '$.total_ms') AS INT64) AS latencia_ms,
    e.error_message AS error
  FROM `${proyecto}.${agentes}.agent_events` AS e
  LEFT JOIN pedidos AS p USING (span_id)
  WHERE e.event_type = 'LLM_RESPONSE'
    AND JSON_VALUE(e.attributes, '$.finish_reason') IS NOT NULL
),
claves AS (
  -- El precio del modelo con el prefijo más largo: `gemini-3.8-flash-001` usa `gemini-3.8-flash`.
  -- Join interno sin igualdad y agregación, no subconsulta correlacionada: BigQuery admite ambos.
  SELECT r.event_id, ARRAY_AGG(p.modelo ORDER BY LENGTH(p.modelo) DESC LIMIT 1)[OFFSET(0)] AS clave_precio
  FROM respuestas AS r
  JOIN precios AS p ON STARTS_WITH(r.modelo, p.modelo)
  GROUP BY r.event_id
),
con_precio AS (
  SELECT r.*, pr.* EXCEPT (modelo), pr.modelo AS modelo_precio
  FROM respuestas AS r
  LEFT JOIN claves AS c USING (event_id)
  LEFT JOIN precios AS pr ON pr.modelo = c.clave_precio
)
SELECT
  timestamp, app, agente, uid, sesion, invocacion, usuario_interno, modelo,
  tokens_entrada, tokens_cache_lectura, tokens_salida, tokens_pensamiento, latencia_ms, error,
  -- Nulo si el modelo no tiene precio: nunca cuenta como costo 0.
  ROUND((
    GREATEST(tokens_entrada - tokens_cache_lectura, 0)
      * IF(umbral_largo IS NOT NULL AND tokens_entrada >= umbral_largo, entrada_largo, entrada)
    + tokens_cache_lectura
      * IF(umbral_largo IS NOT NULL AND tokens_entrada >= umbral_largo, cache_lectura_largo, cache_lectura)
    + (tokens_salida + tokens_pensamiento)
      * IF(umbral_largo IS NOT NULL AND tokens_entrada >= umbral_largo, salida_largo, salida)
  ) / 1e6, 8) AS costo_usd,
  modelo_precio IS NULL AS precio_desconocido
FROM con_precio
