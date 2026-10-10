"""Medición nativa de ADK con la configuración estándar del chasis (docs/medicion.md).

`BigQueryAgentAnalyticsPlugin` registra tokens, latencia, modelo y agente de cada llamada en
`<dataset>.agent_events`; las vistas de `infra/modulos/medicion` les ponen costo.
"""

import os

from google.adk.plugins.base_plugin import BasePlugin


def analitica(
    app: str, proyecto: str | None = None, dataset: str | None = None
) -> list[BasePlugin]:
    """`[plugin]` si hay dataset (argumento o `<APP>_ANALITICA_DATASET`); `[]` si no, para que
    pruebas y evals no toquen BigQuery.

    Privacidad, no negociable: no se guarda el texto de prompts y respuestas ni el estado de la
    sesión o sus cambios. Los usuarios internos se marcan por uid en las vistas.
    """
    dataset = dataset or os.environ.get(f"{app.upper()}_ANALITICA_DATASET")
    if not dataset:
        return []
    proyecto = proyecto or os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not proyecto:
        raise ValueError("La analítica necesita el proyecto de GCP.")
    from google.adk.plugins.bigquery_agent_analytics_plugin import (  # extra bigquery-analytics
        BigQueryAgentAnalyticsPlugin,
        BigQueryLoggerConfig,
    )

    return [
        BigQueryAgentAnalyticsPlugin(
            project_id=proyecto,
            dataset_id=dataset,
            config=BigQueryLoggerConfig(
                payload_column_denylist=["content", "content_parts"],
                log_session_metadata=False,
                event_denylist=["STATE_DELTA"],
                custom_tags={"app": app},
            ),
        )
    ]
