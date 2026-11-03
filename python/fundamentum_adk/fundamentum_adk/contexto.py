"""Contexto largo: compactación de eventos y caché de contexto con los valores del chasis.

- **Compactación** (por omisión, encendida): cuando el prompt de un turno pasa de `UMBRAL_TOKENS`,
  ADK resume los eventos viejos de la sesión con el modelo del agente y conserva crudos los últimos
  `EVENTOS_CRUDOS`. Las conversaciones largas no crecen sin tope en costo ni en latencia. El resumen
  lo pide ADK fuera de los plugins: no aparece en `analitica` (es raro y pequeño).
- **Caché de contexto** (por omisión, apagada): Gemini 3 cachea a partir de 4096 tokens de prefijo
  y cobra el almacenamiento por hora. Conviene solo con instrucciones y herramientas grandes y
  conversaciones de varios turnos seguidos; se prende por app tras medirlo en evals.

Uso: `App(name, root_agent, plugins=..., **contexto())`.
"""

from __future__ import annotations

from typing import Any

UMBRAL_TOKENS = 60_000
EVENTOS_CRUDOS = 20


def contexto(
    *,
    compactar: bool = True,
    umbral_tokens: int = UMBRAL_TOKENS,
    eventos_crudos: int = EVENTOS_CRUDOS,
    cache: bool = False,
    cache_ttl_s: int = 600,
    cache_turnos: int = 10,
) -> dict[str, Any]:
    """Argumentos de `App` para el contexto largo."""
    from google.adk.agents.context_cache_config import ContextCacheConfig
    from google.adk.apps.app import EventsCompactionConfig

    salida: dict[str, Any] = {}
    if compactar:
        salida["events_compaction_config"] = EventsCompactionConfig(
            token_threshold=umbral_tokens, event_retention_size=eventos_crudos
        )
    if cache:
        salida["context_cache_config"] = ContextCacheConfig(
            ttl_seconds=cache_ttl_s, cache_intervals=cache_turnos, min_tokens=4096
        )
    return salida
