-- Resultados que cada app promete (viaje planeado, aplicación preparada, visita agendada). Las
-- apps escriben una línea JSON `resultado_entregado` y el sink la copia a `${resultados}`.
SELECT
  timestamp,
  jsonPayload.app AS app,
  jsonPayload.resultado_tipo AS resultado_tipo,
  jsonPayload.resultado_id AS resultado_id,
  jsonPayload.uid AS uid,
  IFNULL(jsonPayload.usuario_interno, FALSE)
    OR jsonPayload.uid IN UNNEST(ARRAY<STRING>${usuarios_internos}) AS usuario_interno
FROM `${proyecto}.${resultados}.*`
WHERE jsonPayload.tipo = 'resultado_entregado'
