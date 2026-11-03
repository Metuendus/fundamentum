"""Contexto largo: compactación de eventos y caché de contexto con los valores del chasis.

- **Compactación** (por omisión, encendida): cuando el prompt de un turno pasa de `UMBRAL_TOKENS`,
  ADK resume los eventos viejos de la sesión con el modelo del agente y conserva crudos los últimos
  `EVENTOS_CRUDOS`. Las conversaciones largas no crecen sin tope en costo ni en latencia. El resumen
  lo pide ADK fuera de los plugins: no aparece en `analitica` (es raro y pequeño).
- **Caché de contexto** (por omisión, apagada): Gemini 3 cachea a partir de 4096 tokens de prefijo
  y cobra el almacenamiento por hora. Conviene solo con instrucciones y herramientas grandes y
  conversaciones de varios turnos seguidos; se prende por app tras medirlo en evals.

- **Podar** (`PluginPodar`): quita del prompt las copias viejas de lecturas que se repiten.
- **Tope de llamadas** (`PluginTopeLlamadas`): corta un agente en bucle dentro de un mensaje.

Uso: `App(name, root_agent, plugins=[..., PluginPodar(["leer_viaje"]), PluginTopeLlamadas()],
**contexto())`.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin
from google.genai import types

log = logging.getLogger(__name__)

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


OMITIDA = {
    "omitido": "Lectura anterior quitada del contexto para ahorrar tokens; la más reciente está más "
    "abajo. Si necesitas el dato al día, vuelve a llamar la herramienta."
}


class PluginPodar(BasePlugin):
    """Antes de cada llamada a un modelo, deja solo las últimas `conservar` respuestas de cada
    herramienta de `herramientas` en el prompt; las anteriores se cambian por `OMITIDA`.

    Para lecturas que se repiten y caducan (p. ej. `leer_viaje`): cada copia vieja se reenviaba en
    todos los turnos siguientes. La sesión no cambia (el historial visible sigue completo); solo el
    prompt. Se conserva el `id` y el `name` de cada respuesta para que el modelo empareje sus llamadas.
    """

    def __init__(self, herramientas: Iterable[str], conservar: int = 1) -> None:
        super().__init__(name="fundamentum_podar")
        self.herramientas = frozenset(herramientas)
        self.conservar = max(1, conservar)

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> LlmResponse | None:
        contenidos = llm_request.contents or []
        vistas: dict[str, int] = {}
        # De la más nueva a la más vieja: las primeras `conservar` de cada nombre se quedan.
        for i in range(len(contenidos) - 1, -1, -1):
            contenido = contenidos[i]
            partes = contenido.parts or []
            nuevas, cambio = [], False
            for parte in reversed(partes):
                r = parte.function_response
                if r is not None and r.name in self.herramientas:
                    vistas[r.name] = vistas.get(r.name, 0) + 1
                    if vistas[r.name] > self.conservar:
                        parte = types.Part(
                            function_response=types.FunctionResponse(
                                id=r.id, name=r.name, response=dict(OMITIDA)
                            )
                        )
                        cambio = True
                nuevas.append(parte)
            if cambio:
                # Un `Content` nuevo: el evento de la sesión no se toca.
                contenidos[i] = types.Content(role=contenido.role, parts=list(reversed(nuevas)))
        return None


MENSAJE_TOPE = (
    "Este pedido necesitó más pasos de los que permito en un solo mensaje, así que paré aquí. "
    "Lo que ya se propuso sigue en pie; pídemelo por partes."
)


class PluginTopeLlamadas(BasePlugin):
    """Corta un agente que entra en bucle: a partir de la llamada `maximo` al modelo dentro de una
    misma invocación, responde `mensaje` sin llamar al modelo.

    Cuenta por invocación de ADK: cada especialista que corre como `AgentTool` tiene la suya, así
    que el tope es por agente y por mensaje. Ningún uso normal debería tocarlo; es la red para
    errores (una herramienta que falla siempre y el modelo reintenta).
    """

    def __init__(self, maximo: int = 15, mensaje: str = MENSAJE_TOPE) -> None:
        super().__init__(name="fundamentum_tope_llamadas")
        self.maximo = maximo
        self.mensaje = mensaje
        self._cuentas: dict[str, int] = {}

    def __getstate__(self) -> dict[str, Any]:
        # Agent Runtime serializa el App con cloudpickle.
        return {**self.__dict__, "_cuentas": {}}

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> LlmResponse | None:
        clave = callback_context.invocation_id
        self._cuentas[clave] = self._cuentas.get(clave, 0) + 1
        if self._cuentas[clave] <= self.maximo:
            return None
        log.warning(
            "Tope de llamadas al modelo por mensaje",
            extra={"agente": callback_context.agent_name, "maximo": self.maximo},
        )
        return LlmResponse(
            content=types.Content(role="model", parts=[types.Part(text=self.mensaje)])
        )

    async def after_run_callback(self, *, invocation_context: InvocationContext) -> None:
        self._cuentas.pop(invocation_context.invocation_id, None)
