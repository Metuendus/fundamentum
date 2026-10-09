"""Objetos de modelo de ADK con los defaults comunes, para Gemini y Claude en Model Garden."""

import os

from fundamentum_modelos import normalizar
from google.adk.models import Gemini
from google.adk.models.base_llm import BaseLlm
from google.genai import types

# Gemini 3.x solo se sirve en el endpoint global (404 en us-central1). Agent Runtime reserva
# GOOGLE_CLOUD_LOCATION para su región, así que la ubicación del modelo va aparte.
UBICACION_GEMINI = "global"
# Claude en Model Garden se pide con la ruta completa; así no depende de GOOGLE_CLOUD_LOCATION.
UBICACION_CLAUDE = os.environ.get("FUNDAMENTUM_UBICACION_CLAUDE", "global")

# La cuota se agota por momentos (429); 408, 429 y 5xx se reintentan con espera creciente.
REINTENTOS = types.HttpRetryOptions(attempts=5, initial_delay=2.0, max_delay=30.0)


def modelo_adk(nombre: str, proyecto: str | None = None) -> BaseLlm:
    """`gemini-*` → `Gemini` en el endpoint global; `claude-*` → `Claude` vía Model Garden."""
    base = normalizar(nombre)
    if base.startswith("gemini-"):
        return Gemini(
            model=nombre,
            client_kwargs={"location": UBICACION_GEMINI},
            retry_options=REINTENTOS,
        )
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
