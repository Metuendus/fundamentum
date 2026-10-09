#!/usr/bin/env bash
# Crea el proyecto de GCP del chasis y el bucket del estado de Terraform. Idempotente: si algo
# ya existe, sigue. Uso: ./bootstrap.sh <PROJECT_ID> <BILLING_ACCOUNT_ID> [REGION]
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Uso: $0 <PROJECT_ID> <BILLING_ACCOUNT_ID> [REGION]" >&2
  exit 2
fi

proyecto="$1"
facturacion="$2"
region="${3:-us-central1}"

# Los proyectos de las apps y el de trabajo nunca alojan el chasis.
case "$proyecto" in
  travel-planner-509322 | vocatio-mx | epa-turing)
    echo "\"$proyecto\" es el proyecto de otra app o de trabajo. El chasis va en su propio proyecto." >&2
    exit 1
    ;;
esac

if gcloud projects describe "$proyecto" >/dev/null 2>&1; then
  echo "El proyecto $proyecto ya existe."
else
  gcloud projects create "$proyecto" --name="Fundamentum"
fi

gcloud billing projects link "$proyecto" --billing-account="$facturacion"

gcloud services enable --project="$proyecto" \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  cloudbilling.googleapis.com \
  billingbudgets.googleapis.com \
  monitoring.googleapis.com \
  iam.googleapis.com \
  storage.googleapis.com

bucket="${proyecto}-tfstate"
if gcloud storage buckets describe "gs://${bucket}" >/dev/null 2>&1; then
  echo "El bucket gs://${bucket} ya existe."
else
  gcloud storage buckets create "gs://${bucket}" --project="$proyecto" --location="$region" \
    --uniform-bucket-level-access --public-access-prevention
  gcloud storage buckets update "gs://${bucket}" --versioning
fi

dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
printf 'bucket = "%s"\nprefix = "fundamentum"\n' "$bucket" >"${dir}/backend.hcl"
printf 'project_id         = "%s"\nbilling_account_id = "%s"\n' "$proyecto" "$facturacion" >"${dir}/terraform.tfvars"

echo "Listo. Siguiente: cd infra/proyecto && terraform init -backend-config=backend.hcl && terraform apply"
