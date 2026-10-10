"""Plugin de medición: un registro `llamada_modelo` por cada llamada a un modelo.

Obsoleto desde 0.2.0 y se borra en 0.3: las apps miden con `BigQueryAgentAnalyticsPlugin` de ADK
y las vistas de `infra/modulos/medicion` (ver `docs/medicion.md`). `emitir_resultado` se queda.

Se registra en el `App` o el `Runner` de ADK y alcanza también a los especialistas que corren como
`AgentTool` (heredan los plugins del runner padre por defecto). Cada registro es una línea JSON en
stdout: Cloud Run y Agent Runtime la convierten en `jsonPayload` de Cloud Logging, y un sink la
lleva a BigQuery (`infra/modulos/medicion`).

La medición nunca rompe una conversación: si algo falla al medir, se registra el error y la
llamada sigue.
"""

import json
import logging
import sys
import time
import warnings
from collections.abc import Callable
from typing import Any

from fundamentum_modelos import Uso, costo_usd, normalizar
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin

TIPO = "llamada_modelo"
TIPO_RESULTADO = "resultado_entregado"
CLAVE_USUARIO_INTERNO = "usuario_interno"

log = logging.getLogger(__name__)
Emisor = Callable[[dict[str, Any]], None]


def emitir_stdout(registro: dict[str, Any]) -> None:
    linea = {"severity": "INFO", "message": registro["tipo"], **registro}
    sys.stdout.write(json.dumps(linea, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def emitir_resultado(
    app: str,
    resultado_tipo: str,
    resultado_id: str,
    uid: str,
    usuario_interno: bool = False,
    emisor: Emisor = emitir_stdout,
) -> None:
    """Registra un resultado entregado (viaje planeado, aplicación preparada, visita agendada)."""
    emisor(
        {
            "tipo": TIPO_RESULTADO,
            "app": app,
            "resultado_tipo": resultado_tipo,
            "resultado_id": resultado_id,
            "uid": uid,
            "usuario_interno": usuario_interno,
        }
    )


class PluginMedicion(BasePlugin):
    def __init__(self, app: str, emisor: Emisor = emitir_stdout) -> None:
        warnings.warn(
            "PluginMedicion es obsoleto y se borra en 0.3; usa BigQueryAgentAnalyticsPlugin de ADK",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(name="fundamentum_medicion")
        self.app = app
        self.emisor = emisor
        self._en_curso: dict[tuple[str, str], list[tuple[str, float]]] = {}

    @staticmethod
    def _clave(ctx: CallbackContext) -> tuple[str, str]:
        return (ctx.invocation_id, ctx.agent_name)

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> LlmResponse | None:
        pila = self._en_curso.setdefault(self._clave(callback_context), [])
        pila.append((llm_request.model or "", time.monotonic()))
        return None

    async def after_model_callback(
        self, *, callback_context: CallbackContext, llm_response: LlmResponse
    ) -> LlmResponse | None:
        # En streaming llegan fragmentos parciales; el uso viene en la respuesta final.
        if llm_response.partial or llm_response.usage_metadata is None:
            return None
        self._registrar(callback_context, Uso.desde_metadata(llm_response.usage_metadata), None)
        return None

    async def on_model_error_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest, error: Exception
    ) -> LlmResponse | None:
        self._registrar(callback_context, Uso(), type(error).__name__)
        return None

    def _registrar(self, ctx: CallbackContext, uso: Uso, error: str | None) -> None:
        try:
            pila = self._en_curso.get(self._clave(ctx)) or [("", time.monotonic())]
            modelo, inicio = pila.pop()
            if not pila:
                self._en_curso.pop(self._clave(ctx), None)
            try:
                costo: float | None = round(costo_usd(modelo, uso), 8)
            except KeyError:
                costo, error = None, error or "precio_desconocido"
            self.emisor(
                {
                    "tipo": TIPO,
                    "app": self.app,
                    "agente": ctx.agent_name,
                    "invocacion": ctx.invocation_id,
                    "sesion": ctx.session.id,
                    "uid": ctx.user_id,
                    "usuario_interno": bool(ctx.state.get(CLAVE_USUARIO_INTERNO, False)),
                    "modelo": normalizar(modelo),
                    "tokens_entrada": uso.entrada,
                    "tokens_cache_lectura": uso.cache_lectura,
                    "tokens_cache_escritura": uso.cache_escritura,
                    "tokens_salida": uso.salida,
                    "tokens_pensamiento": uso.pensamiento,
                    "costo_usd": costo,
                    "latencia_ms": round((time.monotonic() - inicio) * 1000),
                    "error": error,
                }
            )
        except Exception:
            log.exception("No se pudo registrar la llamada al modelo")
