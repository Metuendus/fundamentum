# CI/CD de las apps

Decisión del 5 de noviembre de 2026: **GitHub Actions corre el CI de cada PR y Cloud Build despliega al
hacer merge a la rama principal**, además de correr los evals con Vertex. Juntos dan 4,500 minutos gratis
al mes (2,000 de Actions en repos privados y 2,500 de Cloud Build por cuenta de facturación), y los dos
cobran 0.006 USD por minuto después. En octubre de 2026 las cinco apps usaron unos 1,410 minutos de
Cloud Build.

## Qué corre dónde

| Momento | Dónde | Qué | Credenciales |
|---|---|---|---|
| Cada PR | GitHub Actions (`ci.yml`) | lint, pruebas, build, reglas, terraform validate, auditoría | Ninguna |
| PR que toca los agentes | Cloud Build (trigger `<app>-evals`) | evals con modelo real (plantilla `plantillas/cloudbuild-evals.yaml`) | Cuenta `<app>-evals` |
| Merge a main | Cloud Build (un trigger por servicio, filtrado por ruta) | build de la imagen con el SHA y despliegue a Cloud Run | Cuenta de despliegue de la app |

El despliegue sale solo con el merge: no hay aprobación ni paso manual después.

## Workflows reutilizables

Viven en `.github/workflows/` de este repo y se llaman fijados por etiqueta
(`uses: Metuendus/fundamentum/.github/workflows/<nombre>.yml@vX.Y.Z`). Un repo privado puede usarlos
porque Fundamentum es público.

| Workflow | Para qué | Entradas principales |
|---|---|---|
| `python-uv.yml` | `uv sync`, ruff, pytest y `pip-audit` sobre el lock; opcionalmente Terraform y comandos de Node en el mismo job | `python-version`, `directorio`, `comando`, `ignorar`, `terraform`, `node-comando` |
| `web-node.yml` | `npm ci`, los comandos de la web y `npm audit` (altas y críticas de producción); con `playwright`, Chromium en caché para el e2e | `directorio`, `comando`, `playwright` |
| `reglas-firebase.yml` | Java 21, Node y caché de los emuladores para probar reglas | `directorio`, `comando` |
| `terraform.yml` | `fmt -check`, `init -backend=false` y `validate` por módulo | `directorios`, `fmt-recursivo` |

La plantilla del `ci.yml` de una app está en [`plantillas/github/ci.yml`](../plantillas/github/ci.yml).

## Reglas

- **`ci-ok` es el único check obligatorio.** Espera a los demás y pasa si cada uno pasó o se saltó por ruta.
- **Filtros por ruta** (`dorny/paths-filter`): un PR que solo toca la web no corre Python.
- **En las apps, el CI corre solo en PR**, no en push a main: el merge ya pasó por `ci-ok` y Cloud Build
  vuelve a construir al desplegar. Repetirlo en push costaba más de la mitad de los minutos de noviembre
  de 2026. Fundamentum y Portafolio, públicos, sí corren en push (Actions es gratis ahí).
- **Pocos jobs.** GitHub cobra cada job redondeado hacia arriba al minuto: un job de 10 segundos cuesta un
  minuto. Terraform y los esquemas van dentro del job de Python (`terraform`, `node-comando`) y el e2e
  dentro del de la web (`playwright`).
- **Un push nuevo cancela la corrida anterior** del mismo PR (`concurrency`).
- **Permisos mínimos**: `contents: read`; el filtro de rutas agrega `pull-requests: read`.
- **Acciones fijadas por SHA**, con la versión en un comentario. Dependabot las sube cada mes.
- **Vulnerabilidades aceptadas** solo con `ignorar` y su razón en un comentario del `ci.yml`. Hoy son dos,
  topadas por dependencias de Google: `opentelemetry-api` (google-adk) y `litellm` (extra `eval`).
- **Dependabot** mensual para uv, npm, GitHub Actions y Terraform, con las menores agrupadas. Cada PR suyo
  corre el CI, así que semanal era el doble de corridas.
- **Rama principal**: en los repos públicos (Fundamentum y Portafolio) una regla pide `ci-ok`. En los
  privados el plan Free de GitHub no permite reglas; se fusiona solo con `ci-ok` en verde.
