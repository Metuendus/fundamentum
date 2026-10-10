"""Un agente con modelo falso cuyo uso de tokens se controla con FUNDAMENTUM_EVALS_FACTOR."""

import os

from google.adk.agents import LlmAgent
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types


class LlmCaro(BaseLlm):
    async def generate_content_async(self, llm_request, stream=False):
        factor = float(os.environ.get("FUNDAMENTUM_EVALS_FACTOR", "1"))
        yield LlmResponse(
            content=types.Content(role="model", parts=[types.Part(text="Hola, ¿en qué te ayudo?")]),
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=int(1_000 * factor),
                candidates_token_count=int(100 * factor),
                total_token_count=int(1_100 * factor),
            ),
        )


root_agent = LlmAgent(name="saludo", model=LlmCaro(model="gemini-3.8-flash"))
