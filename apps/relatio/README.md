# Relatio

Recibe los reportes del botón «Reportar un problema» ([`@fundamentum/relatio`](../../web/relatio)) y
crea el issue en el repo de la app con la GitHub App **Relatio Atrium** (App ID 5823639, solo
*Issues: read & write* en iterum, domi y vocatio).

## Flujo

1. La app manda `POST /reportes` con `Authorization: Bearer <ID token de Firebase>`. CORS solo para
   `RELATIO_ORIGENES`.
2. Se valida el cuerpo (`src/contrato.ts`) y se verifica el token contra el proyecto de la app
   (`src/config.ts`). El repo sale de esa app, nunca del navegador; el correo, del token.
3. Mismo texto, misma persona y misma página en 10 minutos: se agrega como comentario al issue anterior.
4. Cupos diarios: 5 reportes por persona y 30 en total.
5. La captura va a `gs://josecarloscorona-web-relatio/{app}/{AAAA-MM}/{id}.{ext}` (privado, se borra a
   los 180 días). El issue enlaza a `Atrium /reportes/{id}`, detrás de IAP.
6. Issue con etiquetas `origen:usuario`, `tipo:bug`, `requiere-triage` (y `avisar` si pidió aviso).
   El texto va escapado: sin menciones, HTML ni «closes #N».

Firestore central: `reportes/{id}`, `reportes_huellas/{huella}` y `reportes_cupos/{día}_{uid}`.

## Montaje (una vez, en josecarloscorona-web)

```bash
P=josecarloscorona-web
gcloud iam service-accounts create relatio --project $P --display-name "Relatio"
SA=relatio@$P.iam.gserviceaccount.com
gcloud artifacts repositories create relatio --project $P --location us-central1 --repository-format docker
gcloud storage buckets create gs://$P-relatio --project $P --location us-central1 \
  --uniform-bucket-level-access --public-access-prevention
gcloud storage buckets update gs://$P-relatio --lifecycle-file=<(echo '{"rule":[{"action":{"type":"Delete"},"condition":{"age":180}}]}')
gcloud storage buckets add-iam-policy-binding gs://$P-relatio --member serviceAccount:$SA --role roles/storage.objectCreator
gcloud storage buckets add-iam-policy-binding gs://$P-relatio \
  --member serviceAccount:atrium@$P.iam.gserviceaccount.com --role roles/storage.objectViewer
gcloud projects add-iam-policy-binding $P --member serviceAccount:$SA --role roles/datastore.user
gcloud secrets add-iam-policy-binding relatio-github-app-key --project $P \
  --member serviceAccount:$SA --role roles/secretmanager.secretAccessor
```

Verificar el ID token solo usa las llaves públicas de Google: Relatio no necesita permisos en los
proyectos de las apps. Despliegue: `cloudbuild.yaml` (trigger `relatio-main`, push a `main` que toque
`apps/relatio/**`).

## Desarrollo

Fuera de Cloud Run corre en demostración: memoria, sin GitHub y cualquier token vale.

```bash
npm install && npm run typecheck && npm test
npm run dev   # http://localhost:8080, CORS para http://localhost:3000
```
