-- Costo por día, app, agente y modelo, sin usuarios internos. Se concilia contra el export de facturación.
SELECT
  DATE(timestamp, 'America/Mexico_City') AS dia,
  app,
  agente,
  modelo,
  COUNT(*) AS llamadas,
  COUNTIF(error IS NOT NULL) AS errores,
  COUNTIF(precio_desconocido) AS sin_precio,
  SUM(tokens_entrada) AS tokens_entrada,
  SUM(tokens_salida + tokens_pensamiento) AS tokens_salida,
  SUM(costo_usd) AS costo_usd,
  APPROX_QUANTILES(latencia_ms, 100)[OFFSET(95)] AS latencia_p95_ms
FROM `${proyecto}.${agentes}.costo_llamadas`
WHERE NOT usuario_interno
GROUP BY dia, app, agente, modelo
