-- Costo de modelos por resultado entregado, por mes y app, sin usuarios internos.
WITH costo AS (
  SELECT DATE_TRUNC(dia, MONTH) AS mes, app, SUM(costo_usd) AS costo_usd
  FROM `${proyecto}.${agentes}.costo_diario`
  GROUP BY mes, app
),
resultados AS (
  SELECT DATE_TRUNC(DATE(timestamp, 'America/Mexico_City'), MONTH) AS mes, app, resultado_tipo,
    COUNT(DISTINCT resultado_id) AS resultados, COUNT(DISTINCT uid) AS usuarios
  FROM `${proyecto}.${agentes}.resultados`
  WHERE NOT usuario_interno
  GROUP BY mes, app, resultado_tipo
)
SELECT r.mes, r.app, r.resultado_tipo, r.resultados, r.usuarios, c.costo_usd,
  SAFE_DIVIDE(c.costo_usd, r.resultados) AS costo_por_resultado_usd
FROM resultados AS r
LEFT JOIN costo AS c USING (mes, app)
