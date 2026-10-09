# Proyecto de GCP del chasis

Aloja lo que comparten las apps y que no pertenece a ninguna:

- Repositorios de paquetes en Artifact Registry: `fundamentum-py` para Python y `fundamentum-npm`
  para TypeScript.
- Cuenta de servicio que publica desde Cloud Build y trigger por etiqueta.
- Presupuesto con avisos al 50, 90 y 100 %, que solo avisa.

La medición no vive aquí. Cada app aplica `infra/modulos/medicion` en su propio proyecto.

## Crear el proyecto (una vez)

Necesitas `gcloud` con una cuenta que pueda crear proyectos y ligar facturación.

```bash
./infra/proyecto/bootstrap.sh fundamentum-mx <BILLING_ACCOUNT_ID>
cd infra/proyecto
terraform init -backend-config=backend.hcl
terraform apply
```

`bootstrap.sh` crea el proyecto, liga la facturación, habilita las APIs y crea el bucket del
estado. También escribe `backend.hcl` y `terraform.tfvars`, que no se suben al repo. Rechaza los
proyectos de las apps y el de trabajo.

## Publicar una versión

1. Sube la versión en `python/*/pyproject.toml` y anota el cambio en `docs/cambios.md`.
2. Conecta el repo a Cloud Build una sola vez: Consola → Cloud Build → Repositorios → Conectar
   `Metuendus/fundamentum` (GitHub App). Luego aplica con `-var crear_trigger=true`.
3. Etiqueta y sube la etiqueta:

```bash
git tag v0.1.0 && git push origin v0.1.0
```

Mientras no exista el trigger, puedes publicar a mano:

```bash
gcloud builds submit --project fundamentum-mx --config cloudbuild-publicar.yaml \
  --service-account projects/fundamentum-mx/serviceAccounts/fundamentum-publicador@fundamentum-mx.iam.gserviceaccount.com \
  --substitutions TAG_NAME=v0.1.0 .
```

`--service-account` es obligatorio. Los proyectos nuevos ya no traen la cuenta de servicio de Cloud
Build por defecto, y sin ella el build falla con `NOT_FOUND ... ServiceAccountInfoDataType`. La
primera vez, el bucket `fundamentum-mx_cloudbuild` aún no existe; después del primer intento, vuelve
a aplicar Terraform para que el publicador pueda leerlo.

Artifact Registry rechaza que se suba dos veces la misma versión, así que una versión publicada no
cambia.

## Dar acceso a una app

Agrega el miembro que instala los paquetes (la cuenta de Cloud Build de la app y, en local, tu
usuario) a `lectores` y vuelve a aplicar:

```hcl
lectores = [
  "user:josecarloscorona.c@gmail.com",
  "serviceAccount:<NUMERO>@cloudbuild.gserviceaccount.com",
]
```
