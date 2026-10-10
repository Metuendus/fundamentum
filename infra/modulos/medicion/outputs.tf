output "dataset_id" {
  description = "Dataset que se pasa al plugin (BigQueryAgentAnalyticsPlugin(dataset_id=…))."
  value       = google_bigquery_dataset.agentes.dataset_id
}

output "resultados_dataset_id" {
  value = google_bigquery_dataset.resultados.dataset_id
}
