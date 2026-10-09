output "dataset_id" {
  value = google_bigquery_dataset.medicion.dataset_id
}

output "writer_identity" {
  value = google_logging_project_sink.medicion.writer_identity
}
output "vistas_dataset_id" {
  value = google_bigquery_dataset.vistas.dataset_id
}
