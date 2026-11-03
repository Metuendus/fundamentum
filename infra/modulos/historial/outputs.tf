output "grupos_con_ttl" {
  description = "Grupos de colecciones con vencimiento en `vence`."
  value       = [for g in google_firestore_field.vence : g.collection]
}
