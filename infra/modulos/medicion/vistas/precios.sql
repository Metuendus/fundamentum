-- Generado por `python -m fundamentum_modelos.sql`. No editar a mano.
-- Fuente: https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing (consultado el 2026-10-09). USD por millón de tokens.
SELECT * FROM UNNEST([
  STRUCT('claude-haiku-5-5' AS modelo, 0.1 AS entrada, 0.5 AS salida, 0.01 AS cache_lectura, 100000 AS umbral_largo, 0.5 AS entrada_largo, 2.5 AS salida_largo, 0.05 AS cache_lectura_largo),
  STRUCT('claude-opus-5-5' AS modelo, 4.0 AS entrada, 20.0 AS salida, 0.2 AS cache_lectura, CAST(NULL AS INT64) AS umbral_largo, CAST(NULL AS FLOAT64) AS entrada_largo, CAST(NULL AS FLOAT64) AS salida_largo, CAST(NULL AS FLOAT64) AS cache_lectura_largo),
  STRUCT('claude-sonnet-5-5' AS modelo, 2.0 AS entrada, 10.0 AS salida, 0.1 AS cache_lectura, CAST(NULL AS INT64) AS umbral_largo, CAST(NULL AS FLOAT64) AS entrada_largo, CAST(NULL AS FLOAT64) AS salida_largo, CAST(NULL AS FLOAT64) AS cache_lectura_largo),
  STRUCT('gemini-3.5-flash-lite' AS modelo, 0.3 AS entrada, 2.5 AS salida, 0.03 AS cache_lectura, CAST(NULL AS INT64) AS umbral_largo, CAST(NULL AS FLOAT64) AS entrada_largo, CAST(NULL AS FLOAT64) AS salida_largo, CAST(NULL AS FLOAT64) AS cache_lectura_largo),
  STRUCT('gemini-3.8-flash' AS modelo, 1.5 AS entrada, 7.5 AS salida, 0.15 AS cache_lectura, CAST(NULL AS INT64) AS umbral_largo, CAST(NULL AS FLOAT64) AS entrada_largo, CAST(NULL AS FLOAT64) AS salida_largo, CAST(NULL AS FLOAT64) AS cache_lectura_largo)
])
