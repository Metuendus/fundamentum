output "indice_python" {
  description = "URL del índice para [[tool.uv.index]] en cada app."
  value       = "https://${var.region}-python.pkg.dev/${var.project_id}/${google_artifact_registry_repository.python.repository_id}/simple/"
}

output "registro_npm" {
  value = "https://${var.region}-npm.pkg.dev/${var.project_id}/${google_artifact_registry_repository.npm.repository_id}/"
}

output "publicador" {
  value = google_service_account.publicador.email
}
