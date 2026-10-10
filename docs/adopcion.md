# Adopción por app

Desde 0.2.0 la medición no requiere instalar el chasis: cada app usa el plugin oficial de ADK con
la configuración de abajo y aplica el módulo de Terraform `infra/modulos/medicion`. Los paquetes de
Python (`fundamentum-modelos`, `fundamentum-adk`) siguen publicados en Artifact Registry para lo que
sí se comparte como código (registro tarea→modelo, `modelo_adk`).

## 1. Toda llamada a un modelo pasa por ADK

Un `LlmAgent` (con `output_schema` si es una llamada de una vuelta) ejecutado por un `Runner` o por
Agent Runtime, con el `App` de la app. Nada de `genai.Client(...).models.generate_content` directo.
Cada app tiene `tests/test_solo_adk.py`, que falla si aparece fuera de las pruebas.

## 2. Plugin de analítica, configuración estándar

```toml
# pyproject.toml / requirements del agente
google-adk[bigquery-analytics]==<versión de la app>
```

```python
import os

from google.adk.apps import App
from google.adk.plugins.bigquery_agent_analytics_plugin import (
    BigQueryAgentAnalyticsPlugin,
    BigQueryLoggerConfig,
)


def analitica(app: str) -> list:
    """Sin `<APP>_ANALITICA_DATASET` no hay plugin: pruebas y evals no tocan BigQuery."""
    dataset = os.environ.get(f"{app.upper()}_ANALITICA_DATASET")
    if not dataset:
        return []
    return [
        BigQueryAgentAnalyticsPlugin(
            project_id=os.environ["GOOGLE_CLOUD_PROJECT"],
            dataset_id=dataset,
            config=BigQueryLoggerConfig(
                # Privacidad: ni texto de prompts y respuestas, ni estado de la sesión.
                payload_column_denylist=["content", "content_parts"],
                log_session_metadata=False,
                event_denylist=["STATE_DELTA"],
                custom_tags={"app": app},
            ),
        )
    ]


app = App(name="iterum", root_agent=root_agent, plugins=analitica("iterum"))
```

En Agent Runtime: `AdkApp(app=app, enable_tracing=True)` para Cloud Trace. En Cloud Run, el `Runner`
recibe el mismo `app`.

La cuenta de servicio del agente necesita `roles/cloudtrace.agent` en el proyecto; los permisos de
BigQuery los da el módulo.

## 3. Módulo de Terraform

```hcl
module "medicion" {
  source            = "git::https://github.com/Metuendus/fundamentum.git//infra/modulos/medicion?ref=v0.2.0"
  project_id        = var.project_id
  escritores        = ["serviceAccount:${google_service_account.agentes.email}"]
  usuarios_internos = var.usuarios_internos
  crear_vistas      = var.medicion_vistas # true en un segundo apply, tras la primera llamada
}
```

## 4. Resultado entregado

Ver [`medicion.md`](medicion.md#resultado_entregado).

## Por app

| App | Qué falta |
|---|---|
| Iterum | Plugin en el `App` del Concierge; el lector de documentos (`documents.py`) pasa a `LlmAgent` |
| Vocatio | Memoria y Scriba pasan a `LlmAgent` con `Runner` en Cloud Run (#44) |
| Domi | Iudex nace como `LlmAgent` con el plugin; botón "Agendé visita" |
