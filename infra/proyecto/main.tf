# Proyecto del chasis: repositorios de paquetes, publicación por etiqueta y aviso de gasto.
# El proyecto, la facturación, las APIs y el bucket del estado los crea bootstrap.sh.

data "google_project" "this" {}

# ─── Repositorios de paquetes ────────────────────────────────────────────────

resource "google_artifact_registry_repository" "python" {
  location      = var.region
  repository_id = "fundamentum-py"
  format        = "PYTHON"
  description   = "Paquetes de Python del chasis (fundamentum-modelos, fundamentum-adk…)."
}

resource "google_artifact_registry_repository" "npm" {
  location      = var.region
  repository_id = "fundamentum-npm"
  format        = "NPM"
  description   = "Paquetes de TypeScript del chasis (@fundamentum/tokens, @fundamentum/ui…)."
}

locals {
  repositorios = {
    python = google_artifact_registry_repository.python.name
    npm    = google_artifact_registry_repository.npm.name
  }
  lectura = { for par in setproduct(keys(local.repositorios), var.lectores) : "${par[0]}|${par[1]}" => par }
}

resource "google_artifact_registry_repository_iam_member" "lectores" {
  for_each = local.lectura

  location   = var.region
  repository = local.repositorios[each.value[0]]
  role       = "roles/artifactregistry.reader"
  member     = each.value[1]
}

# ─── Publicación ─────────────────────────────────────────────────────────────

resource "google_service_account" "publicador" {
  account_id   = "fundamentum-publicador"
  display_name = "Publica los paquetes del chasis desde Cloud Build"
}

resource "google_artifact_registry_repository_iam_member" "publicador" {
  for_each = local.repositorios

  location   = var.region
  repository = each.value
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.publicador.email}"
}

# `gcloud builds submit` sube el código a este bucket (lo crea Cloud Build la primera vez). Los
# proyectos nuevos ya no tienen cuenta de Cloud Build por defecto, así que el build corre como el
# publicador y necesita leer el código que subió.
resource "google_storage_bucket_iam_member" "publicador_fuente" {
  bucket = "${var.project_id}_cloudbuild"
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.publicador.email}"
}

resource "google_project_iam_member" "publicador_logs" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.publicador.email}"
}

# Una etiqueta v* publica la versión. Las versiones no se sobrescriben: Artifact Registry rechaza
# subir dos veces la misma, así que una etiqueta repetida falla en vez de cambiar lo que ya
# instalaron las apps.
resource "google_cloudbuild_trigger" "publicar" {
  count = var.crear_trigger ? 1 : 0

  name            = "fundamentum-publicar"
  description     = "Publica los paquetes del chasis al etiquetar v*."
  filename        = "cloudbuild-publicar.yaml"
  service_account = google_service_account.publicador.id

  github {
    owner = var.github_owner
    name  = var.github_repo
    push {
      tag = "^v[0-9]+\\.[0-9]+\\.[0-9]+$"
    }
  }

  substitutions = {
    _REGION = var.region
  }
}

# ─── Presupuesto ─────────────────────────────────────────────────────────────
#
# Solo avisa. El chasis casi no debería gastar: almacenamiento de paquetes y minutos de build.

resource "google_monitoring_notification_channel" "correo" {
  display_name = "Correo del fundador"
  type         = "email"
  labels = {
    email_address = var.alert_email
  }
}

resource "google_billing_budget" "fundamentum" {
  billing_account = var.billing_account_id
  display_name    = "Fundamentum · mensual"

  budget_filter {
    projects = ["projects/${data.google_project.this.number}"]
  }

  amount {
    specified_amount {
      currency_code = "MXN"
      units         = tostring(var.monthly_budget)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
  }
  threshold_rules {
    threshold_percent = 0.9
  }
  threshold_rules {
    threshold_percent = 1.0
  }
  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "FORECASTED_SPEND"
  }

  all_updates_rule {
    monitoring_notification_channels = [google_monitoring_notification_channel.correo.id]
    disable_default_iam_recipients   = false
  }
}
