# Medición común con el plugin oficial de ADK (BigQueryAgentAnalyticsPlugin).
#
# - El plugin del agente escribe cada evento (llamadas a modelos, herramientas, agentes) en la tabla
#   `agent_events` del dataset `agentes`, que crea él mismo junto con sus vistas `v_*`.
# - Este módulo crea ese dataset, da permiso de escritura a las cuentas de los agentes y agrega las
#   vistas de costo (`costo_*`), que cruzan los tokens con la tabla de precios del chasis.
# - Los resultados entregados (`resultado_entregado`) siguen llegando por una línea JSON en stdout,
#   que un sink de Cloud Logging copia al dataset `fundamentum_resultados`.

resource "google_bigquery_dataset" "agentes" {
  project     = var.project_id
  dataset_id  = var.dataset_id
  location    = var.location
  description = "Eventos de los agentes (plugin BigQuery Agent Analytics de ADK) y vistas de costo de Fundamentum."

  default_partition_expiration_ms = var.retencion_dias * 24 * 60 * 60 * 1000
}

# El plugin escribe con la Storage Write API, crea su tabla y sus vistas al arrancar.
resource "google_bigquery_dataset_iam_member" "escritores" {
  for_each = toset(var.escritores)

  project    = var.project_id
  dataset_id = google_bigquery_dataset.agentes.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = each.value
}

# Crear vistas es un trabajo de consulta.
resource "google_project_iam_member" "escritores_jobs" {
  for_each = toset(var.escritores)

  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = each.value
}

# ─── Resultados entregados ───────────────────────────────────────────────────

resource "google_bigquery_dataset" "resultados" {
  project     = var.project_id
  dataset_id  = "fundamentum_resultados"
  location    = var.location
  description = "Líneas resultado_entregado de las apps, copiadas por el sink de Cloud Logging."
}

resource "google_logging_project_sink" "resultados" {
  project     = var.project_id
  name        = "fundamentum-resultados"
  destination = "bigquery.googleapis.com/projects/${var.project_id}/datasets/${google_bigquery_dataset.resultados.dataset_id}"
  filter      = "jsonPayload.tipo=\"resultado_entregado\""

  unique_writer_identity = true

  bigquery_options {
    use_partitioned_tables = true
  }
}

resource "google_bigquery_dataset_iam_member" "sink" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.resultados.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_logging_project_sink.resultados.writer_identity
}

# ─── Vistas de costo ─────────────────────────────────────────────────────────
#
# Leen `agent_events` (lo crea el plugin con la primera llamada) y las tablas del sink (con el
# primer resultado). Por eso se crean en un segundo `apply` con `crear_vistas = true`.

locals {
  plantilla = {
    proyecto   = var.project_id
    agentes    = google_bigquery_dataset.agentes.dataset_id
    resultados = google_bigquery_dataset.resultados.dataset_id
    precios    = file("${path.module}/vistas/precios.sql")
    # Lista de uids como literal de BigQuery: ["a","b"] (comillas dobles válidas en GoogleSQL).
    usuarios_internos = jsonencode(var.usuarios_internos)
  }
}

resource "google_bigquery_table" "costo_llamadas" {
  count = var.crear_vistas ? 1 : 0

  project             = var.project_id
  dataset_id          = google_bigquery_dataset.agentes.dataset_id
  table_id            = "costo_llamadas"
  deletion_protection = false

  view {
    query          = templatefile("${path.module}/vistas/costo_llamadas.sql", local.plantilla)
    use_legacy_sql = false
  }

  depends_on = [google_bigquery_dataset_iam_member.escritores]
}

resource "google_bigquery_table" "costo_diario" {
  count = var.crear_vistas ? 1 : 0

  project             = var.project_id
  dataset_id          = google_bigquery_dataset.agentes.dataset_id
  table_id            = "costo_diario"
  deletion_protection = false

  view {
    query          = templatefile("${path.module}/vistas/costo_diario.sql", local.plantilla)
    use_legacy_sql = false
  }

  depends_on = [google_bigquery_table.costo_llamadas]
}

resource "google_bigquery_table" "resultados" {
  count = var.crear_vistas ? 1 : 0

  project             = var.project_id
  dataset_id          = google_bigquery_dataset.agentes.dataset_id
  table_id            = "resultados"
  deletion_protection = false

  view {
    query          = templatefile("${path.module}/vistas/resultados.sql", local.plantilla)
    use_legacy_sql = false
  }

  depends_on = [google_bigquery_dataset_iam_member.sink]
}

resource "google_bigquery_table" "costo_por_resultado" {
  count = var.crear_vistas ? 1 : 0

  project             = var.project_id
  dataset_id          = google_bigquery_dataset.agentes.dataset_id
  table_id            = "costo_por_resultado"
  deletion_protection = false

  view {
    query          = templatefile("${path.module}/vistas/costo_por_resultado.sql", local.plantilla)
    use_legacy_sql = false
  }

  depends_on = [google_bigquery_table.costo_diario, google_bigquery_table.resultados]
}
