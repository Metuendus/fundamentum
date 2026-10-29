# Fundamentum · reglas del proyecto

Chasis compartido de Iterum, Vocatio y Domi. Lee `README.md` y `docs/` antes de trabajar. Lo que se
cambia aquí lo heredan tres apps: cada cambio es una versión nueva, con pruebas y nota en
`docs/cambios.md`.

## Reglas

- **Todo en Google Cloud.** Modelos solo vía Model Garden (Gemini y Claude); infraestructura en GCP.
- **Ninguna llamada a un modelo fuera de ADK.** ADK Python 2.x (`LlmAgent` + `Runner` o Agent
  Runtime) es la única forma; lo que no pasa por ADK no se mide ni se traza. Guardrails son Plugins,
  no callbacks.
- **Medición nativa.** `BigQueryAgentAnalyticsPlugin` con la configuración de `docs/adopcion.md`
  (sin `content`, sin estado de sesión) y Cloud Trace. El chasis solo pone precios y vistas.
- **Ningún modelo sin precio.** `PRECIOS` lleva fuente y fecha; un modelo sin precio falla en voz
  alta y la vista lo marca como `precio_desconocido`, nunca como costo 0. Tras cambiar `PRECIOS`,
  `uv run python -m fundamentum_modelos.sql`. Tarifa estándar, no
  promocional.
- **La medición nunca rompe una conversación.** Un error al medir se registra y la llamada sigue.
- **No usar la familia Gemini 2.5** (retirada el 16 de octubre de 2026).
- Entra solo lo que usan dos apps o lo que es estándar obligatorio. Nada específico de un dominio.
- `apps/` son herramientas del chasis que sirven a las tres apps (hoy Atrium: acceso y uso). Se
  despliegan desde `main` con su propio Cloud Build, aparte de las releases de los paquetes. El repo
  es público: ningún secreto ni dato de usuarios en el código.
- Python 3.12 con uv. Español en código, docs y commits, como en las apps.

## Verificar

```bash
uv sync --all-packages && uv run ruff check . && uv run ruff format --check . && uv run pytest -q
terraform fmt -check -recursive infra   # el validate de cada módulo corre en CI (cloudbuild-pr.yaml)
```
