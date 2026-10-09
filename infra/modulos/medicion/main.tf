# Medición común: los registros `llamada_modelo` y `resultado_entregado` que las apps escriben
# en stdout (JSON) llegan a Cloud Logging y un sink los copia a BigQuery. Un dataset por
# proyecto, con las mismas vistas en las tres apps; Looker Studio las combina.

resource "google_bigquery_dataset" "medicion" {
  project     = var.project_id
  dataset_id  = var.dataset_id
  location    = var.location
  description = "Medición de Fundamentum: llamadas a modelos y resultados entregados."

  default_partition_expiration_ms = var.retencion_dias * 24 * 60 * 60 * 1000
}

resource "google_logging_project_sink" "medicion" {
  project     = var.project_id
  name        = "fundamentum-medicion"
  destination = "bigquery.googleapis.com/projects/${var.project_id}/datasets/${google_bigquery_dataset.medicion.dataset_id}"
  filter      = "jsonPayload.tipo=\"llamada_modelo\" OR jsonPayload.tipo=\"resultado_entregado\""

  unique_writer_identity = true

  bigquery_options {
    use_partitioned_tables = true
  }
}

resource "google_bigquery_dataset_iam_member" "sink" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.medicion.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_logging_project_sink.medicion.writer_identity
}

# Las vistas van en otro dataset: las consultas con comodín (`dataset.*`) no admiten vistas
# entre las tablas que cubren. Leen las tablas que crea el sink, que solo existen después del
# primer registro; por eso se crean en un segundo `apply` con `crear_vistas = true`.
resource "google_bigquery_dataset" "vistas" {
  project     = var.project_id
  dataset_id  = "${var.dataset_id}_vistas"
  location    = var.location
  description = "Vistas de la medición de Fundamentum (mismas en las tres apps)."
}

locals {
  plantilla = {
    proyecto = var.project_id
    datos    = google_bigquery_dataset.medicion.dataset_id
    vistas   = google_bigquery_dataset.vistas.dataset_id
  }
  base = var.crear_vistas ? toset(["llamadas", "resultados"]) : toset([])
}

resource "google_bigquery_table" "base" {
  for_each = local.base

  project             = var.project_id
  dataset_id          = google_bigquery_dataset.vistas.dataset_id
  table_id            = "v_${each.key}"
  deletion_protection = false

  view {
    query          = templatefile("${path.module}/vistas/${each.key}.sql", local.plantilla)
    use_legacy_sql = false
  }

  depends_on = [google_bigquery_dataset_iam_member.sink]
}

resource "google_bigquery_table" "costo_diario" {
  count = var.crear_vistas ? 1 : 0

  project             = var.project_id
  dataset_id          = google_bigquery_dataset.vistas.dataset_id
  table_id            = "v_costo_diario"
  deletion_protection = false

  view {
    query          = templatefile("${path.module}/vistas/costo_diario.sql", local.plantilla)
    use_legacy_sql = false
  }

  depends_on = [google_bigquery_table.base]
}

resource "google_bigquery_table" "costo_por_resultado" {
  count = var.crear_vistas ? 1 : 0

  project             = var.project_id
  dataset_id          = google_bigquery_dataset.vistas.dataset_id
  table_id            = "v_costo_por_resultado"
  deletion_protection = false

  view {
    query          = templatefile("${path.module}/vistas/costo_por_resultado.sql", local.plantilla)
    use_legacy_sql = false
  }

  depends_on = [google_bigquery_table.costo_diario]
}
