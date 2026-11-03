variable "project_id" {
  description = "Proyecto de la app (su Firestore guarda sesiones e historial)."
  type        = string
}

variable "database" {
  description = "Base de Firestore."
  type        = string
  default     = "(default)"
}

variable "grupos" {
  description = "Grupos de colecciones con el campo `vence` (sesiones de ADK e historial visible)."
  type        = list(string)
  default     = ["sesiones", "eventos", "conversaciones", "mensajes"]
}
