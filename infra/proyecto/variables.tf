# Sin valor por defecto a propósito: el chasis nunca debe aplicarse en el proyecto de una app.
variable "project_id" {
  type        = string
  description = "Proyecto de GCP del chasis (lo crea bootstrap.sh)."
  validation {
    condition     = !contains(["travel-planner-509322", "vocatio-mx", "epa-turing"], var.project_id)
    error_message = "Ese es el proyecto de una app o el de trabajo. El chasis va en su propio proyecto."
  }
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "billing_account_id" {
  type        = string
  description = "Cuenta de facturación (la misma de las apps)."
}

variable "monthly_budget" {
  type        = number
  default     = 100
  description = "Presupuesto mensual en la moneda de la cuenta de facturación (hoy MXN). Solo avisa."
}

variable "alert_email" {
  type    = string
  default = "josecarloscorona.c@gmail.com"
}

variable "lectores" {
  type        = list(string)
  default     = []
  description = "Miembros IAM que instalan los paquetes (p. ej. serviceAccount:…@cloudbuild.gserviceaccount.com de cada app)."
}

variable "crear_trigger" {
  type        = bool
  default     = false
  description = "Crear el trigger de publicación por etiqueta. Requiere conectar antes el repo de GitHub a Cloud Build (paso manual, ver README)."
}

variable "github_owner" {
  type    = string
  default = "Metuendus"
}

variable "github_repo" {
  type    = string
  default = "fundamentum"
}
