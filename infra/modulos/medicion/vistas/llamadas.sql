-- Una fila por llamada a un modelo, con el costo calculado por el plugin de medición.
SELECT
  timestamp,
  jsonPayload.app AS app,
  jsonPayload.agente AS agente,
  jsonPayload.modelo AS modelo,
  jsonPayload.uid AS uid,
  jsonPayload.sesion AS sesion,
  jsonPayload.invocacion AS invocacion,
  jsonPayload.usuario_interno AS usuario_interno,
  jsonPayload.tokens_entrada AS tokens_entrada,
  jsonPayload.tokens_cache_lectura AS tokens_cache_lectura,
  jsonPayload.tokens_cache_escritura AS tokens_cache_escritura,
  jsonPayload.tokens_salida AS tokens_salida,
  jsonPayload.tokens_pensamiento AS tokens_pensamiento,
  jsonPayload.costo_usd AS costo_usd,
  jsonPayload.latencia_ms AS latencia_ms,
  jsonPayload.error AS error
FROM `${proyecto}.${datos}.*`
WHERE jsonPayload.tipo = 'llamada_modelo'
