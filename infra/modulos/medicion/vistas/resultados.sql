-- Resultados que cada app promete: viaje planeado, aplicación preparada, visita agendada.
SELECT
  timestamp,
  jsonPayload.app AS app,
  jsonPayload.resultado_tipo AS resultado_tipo,
  jsonPayload.resultado_id AS resultado_id,
  jsonPayload.uid AS uid,
  jsonPayload.usuario_interno AS usuario_interno
FROM `${proyecto}.${datos}.*`
WHERE jsonPayload.tipo = 'resultado_entregado'
