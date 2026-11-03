"""Cloud Trace con los exportadores de ADK, para servicios propios en Cloud Run.

En Agent Runtime basta `AdkApp(app=app, enable_tracing=True)`. En Cloud Run, `activar_trazas`
instala el exportador OTLP de ADK hacia `telemetry.googleapis.com` una vez por proceso; ADK ya
crea los spans de cada invocación, agente, llamada al modelo y herramienta.

Con CPU solo durante la petición, un lote pendiente se pierde: hay que vaciar el proveedor al
final de cada petición (`vaciar`). La cuenta del servicio necesita `roles/cloudtrace.agent`.
"""

from __future__ import annotations

import contextlib
from collections.abc import Mapping
from typing import Any

_proveedor: Any = None


def activar_trazas(proyecto: str) -> Any:
    """Instala el exportador de Cloud Trace (idempotente) y devuelve el `TracerProvider`.

    Sin `gcp.project_id` en el recurso, la API responde 400 a cada lote.
    """
    global _proveedor
    if _proveedor is not None:
        return _proveedor
    from google.adk.telemetry.google_cloud import get_gcp_exporters, get_gcp_resource
    from google.adk.telemetry.setup import maybe_set_otel_providers
    from opentelemetry import trace

    maybe_set_otel_providers(
        [get_gcp_exporters(enable_cloud_tracing=True)],
        otel_resource=get_gcp_resource(proyecto),
    )
    _proveedor = trace.get_tracer_provider()
    return _proveedor


def vaciar(timeout_ms: int = 5_000) -> None:
    """Envía los spans pendientes. No falla: la medición nunca rompe una conversación."""
    if _proveedor is not None and hasattr(_proveedor, "force_flush"):
        with contextlib.suppress(Exception):
            _proveedor.force_flush(timeout_ms)


def trace_id_actual() -> str | None:
    """El trace id del span activo en hex (32 caracteres), o `None` si no hay traza."""
    from opentelemetry import trace

    contexto = trace.get_current_span().get_span_context()
    return format(contexto.trace_id, "032x") if contexto.is_valid else None


def contexto_entrante(cabeceras: Mapping[str, str]) -> Any:
    """El contexto de OpenTelemetry de una petición (`traceparent` de la web o de Pub/Sub), para
    que el turno del agente quede como hijo de la petición web en la misma traza:

        with tracer.start_as_current_span("chat", context=contexto_entrante(request.headers)):
            ...
    """
    from opentelemetry.propagate import extract

    return extract({k.lower(): v for k, v in cabeceras.items()})


def enlace_traza(proyecto: str, trace_id: str) -> str:
    """URL de la traza en la consola de Cloud Trace (para Atrium y los logs)."""
    return f"https://console.cloud.google.com/traces/explorer;traceId={trace_id}?project={proyecto}"
