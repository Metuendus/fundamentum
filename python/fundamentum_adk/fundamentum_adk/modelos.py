"""Objetos de modelo de ADK con los defaults comunes, para Gemini y Claude en Model Garden."""

import logging
import os
from collections.abc import AsyncGenerator
from typing import Any

from fundamentum_modelos import normalizar
from google.adk.models import Gemini
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

# Gemini 3.x solo se sirve en el endpoint global (404 en us-central1). Agent Runtime reserva
# GOOGLE_CLOUD_LOCATION para su región, así que la ubicación del modelo va aparte.
UBICACION_GEMINI = "global"
# Claude en Model Garden se pide con la ruta completa; así no depende de GOOGLE_CLOUD_LOCATION.
UBICACION_CLAUDE = os.environ.get("FUNDAMENTUM_UBICACION_CLAUDE", "global")

# La cuota se agota por momentos (429); 408, 429 y 5xx se reintentan con espera creciente.
REINTENTOS = types.HttpRetryOptions(attempts=5, initial_delay=2.0, max_delay=30.0)
# Sin tope, una llamada que Gemini deja colgada espera para siempre: en Iterum una tardó 7,6 min y
# el turno se perdió (iterum#127). Con el tope, cada intento corta a los 90 s (también en el
# servidor, por `X-Server-Timeout`). google-genai no reintenta el corte de aiohttp, así que
# `GeminiConEspera` lo reintenta hasta INTENTOS_ESPERA veces.
ESPERA_MS = 90_000
INTENTOS_ESPERA = 3

log = logging.getLogger(__name__)


def con_espera(peticion: LlmRequest, espera_ms: int = ESPERA_MS) -> LlmRequest:
    """Pone el tope por intento en la petición si no trae uno propio."""
    opciones = peticion.config.http_options or types.HttpOptions()
    if opciones.timeout is None:
        opciones.timeout = espera_ms
    peticion.config.http_options = opciones
    return peticion


class GeminiConEspera(Gemini):
    """`Gemini` con `ESPERA_MS` por intento. Un tope en `client_kwargs` reemplazaría las
    `http_options` que arma ADK (reintentos y cabeceras), por eso va en cada petición. Solo se
    reintenta si el corte llega antes de la primera respuesta: después ya hay texto entregado."""

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        con_espera(llm_request)
        for intento in range(1, INTENTOS_ESPERA + 1):
            entregadas = 0
            try:
                async for respuesta in super().generate_content_async(llm_request, stream):
                    entregadas += 1
                    yield respuesta
                return
            except TimeoutError:
                if entregadas or intento == INTENTOS_ESPERA:
                    raise
                log.warning(
                    "Gemini no respondió en %s ms (intento %s); reintento.",
                    llm_request.config.http_options.timeout,
                    intento,
                )


def modelo_adk(nombre: str, proyecto: str | None = None, credenciales: Any = None) -> BaseLlm:
    """`gemini-*` → `Gemini` en el endpoint global; `claude-*` → `Claude` vía Model Garden.

    `proyecto` y `credenciales` fijan a qué proyecto se cobra Gemini (p. ej. credenciales
    suplantadas en local); sin ellos, los de ADC y `GOOGLE_CLOUD_PROJECT`.
    """
    base = normalizar(nombre)
    if base.startswith("gemini-"):
        cliente: dict[str, Any] = {"location": UBICACION_GEMINI}
        if proyecto:
            cliente |= {"vertexai": True, "project": proyecto}
        if credenciales is not None:
            cliente["credentials"] = credenciales
        return GeminiConEspera(model=nombre, client_kwargs=cliente, retry_options=REINTENTOS)
    if base.startswith("claude-"):
        from google.adk.models.anthropic_llm import Claude  # requiere anthropic[vertex]

        if nombre.startswith("projects/"):
            return Claude(model=nombre)
        proyecto = proyecto or os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not proyecto:
            raise ValueError("Claude en Model Garden necesita el proyecto de GCP.")
        ruta = (
            f"projects/{proyecto}/locations/{UBICACION_CLAUDE}/publishers/anthropic/models/{nombre}"
        )
        return Claude(model=ruta)
    raise ValueError(f"Modelo fuera de Model Garden o sin soporte en el chasis: {nombre}")
