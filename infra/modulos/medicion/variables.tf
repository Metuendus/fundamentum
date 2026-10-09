variable "project_id" {
  type        = string
  description = "Proyecto de la app (cada app mide en su propio proyecto)."
}

variable "dataset_id" {
  type    = string
  default = "fundamentum_medicion"
}

variable "location" {
  type    = string
  default = "US"
}

variable "retencion_dias" {
  type        = number
  default     = 400
  description = "Días que se conserva cada partición diaria."
}

variable "crear_vistas" {
  type        = bool
  default     = false
  description = "Activar en un segundo apply, cuando el sink ya creó sus tablas."
}
