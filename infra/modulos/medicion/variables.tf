variable "project_id" {
  type        = string
  description = "Proyecto de la app (cada app mide en su propio proyecto)."
}

variable "dataset_id" {
  type        = string
  default     = "agentes"
  description = "Dataset donde escribe BigQueryAgentAnalyticsPlugin. Debe coincidir con el del plugin."
}

variable "location" {
  type    = string
  default = "US"
}

variable "escritores" {
  type        = list(string)
  default     = []
  description = "Cuentas que corren agentes con el plugin, p. ej. serviceAccount:iterum-agents@…"
}

variable "retencion_dias" {
  type        = number
  default     = 400
  description = "Días que se conserva cada partición diaria."
}

variable "crear_vistas" {
  type        = bool
  default     = false
  description = "Activar en un segundo apply, cuando ya existan agent_events y las tablas del sink."
}

variable "usuarios_internos" {
  type        = list(string)
  default     = []
  description = "uids del fundador y del equipo; las vistas los excluyen de costo y resultados."
}
