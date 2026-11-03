# Vencimiento automático (TTL) de las sesiones de ADK y del historial visible.
# `SesionesFirestore` e `Historial` ponen `vence` en cada documento y lo renuevan en cada turno;
# Firestore borra los vencidos en las 24 h siguientes, sin costo de lectura.
# Los índices de un solo campo de `vence` se apagan: nadie consulta por él y cuestan escrituras.

resource "google_firestore_field" "vence" {
  for_each = toset(var.grupos)

  project    = var.project_id
  database   = var.database
  collection = each.value
  field      = "vence"

  ttl_config {}

  index_config {}
}
