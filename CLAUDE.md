# Fundamentum · reglas del proyecto

Chasis compartido de Iterum, Vocatio y Domi. Lee `README.md` y `docs/` antes de trabajar. Lo que se
cambia aquí lo heredan tres apps: cada cambio es una versión nueva, con pruebas y nota en
`docs/cambios.md`.

## Reglas

- **Todo en Google Cloud.** Modelos solo vía Model Garden (Gemini y Claude); infraestructura en GCP.
- **ADK Python 2.x** es la única forma de llamar a un modelo. Guardrails y medición son Plugins, no
  callbacks.
- **Ningún modelo sin precio.** `PRECIOS` lleva fuente y fecha; un modelo sin precio falla en voz
  alta y la medición lo registra como `precio_desconocido`, nunca como costo 0. Tarifa estándar, no
  promocional.
- **La medición nunca rompe una conversación.** Un error al medir se registra y la llamada sigue.
- **No usar la familia Gemini 2.5** (retirada el 16 de octubre de 2026).
- Entra solo lo que usan dos apps o lo que es estándar obligatorio. Nada específico de un dominio.
- Python 3.12 con uv. Español en código, docs y commits, como en las apps.

## Verificar

```bash
uv sync --all-packages && uv run ruff check . && uv run ruff format --check . && uv run pytest -q
terraform fmt -check -recursive infra   # el validate de cada módulo corre en CI (cloudbuild-pr.yaml)
```
