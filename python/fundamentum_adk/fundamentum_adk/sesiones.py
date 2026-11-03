"""Sesiones de Agent Platform (Agent Engine Sessions) para conversaciones servidas desde Cloud Run.

Es el servicio administrado de Google para guardar sesiones de ADK: el agente recuerda aunque
Cloud Run escale a cero y la persona ve sus conversaciones desde cualquier dispositivo. No hace falta
desplegar el agente en Agent Runtime: basta un motor (reasoning engine) sin código que sirva de
contenedor de sesiones, uno por app (`plantillas/sesiones/crear_motor.py`).

En Agent Runtime (Iterum) el propio `AdkApp` ya usa este servicio; no hay que configurar nada.

Costo (consultado el 2026-11-03): USD 0.25 por cada 1,000 eventos guardados desde el 11 de febrero
de 2026, según https://www.cloudzero.com/blog/google-vertex-ai-pricing/; verificar la tarifa vigente
en https://cloud.google.com/vertex-ai/pricing antes de cambiar volúmenes.
"""

from __future__ import annotations

from typing import Any

from google.adk.sessions import BaseSessionService

# Cuánto vive una sesión desde que se crea: 365 días. Agent Platform la borra sola al vencer.
RETENCION = "31536000s"


def sesiones_agent_platform(
    proyecto: str, motor: str, ubicacion: str = "us-central1"
) -> BaseSessionService:
    """`VertexAiSessionService` de ADK sobre el motor `motor` (id numérico o nombre completo).

    Requiere el extra `fundamentum-adk[agentplatform]` y `roles/aiplatform.user` en la cuenta del
    servicio. Las sesiones de una persona solo las lee ella: el servicio rechaza otro `user_id`.
    """
    from google.adk.sessions import VertexAiSessionService

    motor = motor.rsplit("/", 1)[-1]
    return VertexAiSessionService(project=proyecto, location=ubicacion, agent_engine_id=motor)


def opciones_por_omision(sesiones: BaseSessionService) -> dict[str, Any]:
    """Argumentos extra de `create_session`: vencimiento en Agent Platform; nada en memoria."""
    from google.adk.sessions import VertexAiSessionService

    return {"ttl": RETENCION} if isinstance(sesiones, VertexAiSessionService) else {}
