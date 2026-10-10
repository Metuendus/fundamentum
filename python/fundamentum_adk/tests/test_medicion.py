"""El plugin mide a la raíz y a los especialistas que corren como AgentTool, con un modelo falso."""

import json
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from fundamentum_adk import PluginMedicion, emitir_resultado, emitir_stdout, modelo_adk
from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import InMemoryRunner
from google.adk.tools.agent_tool import AgentTool
from google.genai import types

pytestmark = pytest.mark.filterwarnings("ignore:PluginMedicion es obsoleto:DeprecationWarning")


class LlmFalso(BaseLlm):
    """Responde con un guion fijo y reporta un uso conocido."""

    guion: list[LlmResponse]

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        yield self.guion.pop(0)


def texto(t: str, entrada: int, salida: int) -> LlmResponse:
    return LlmResponse(
        content=types.Content(role="model", parts=[types.Part(text=t)]),
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=entrada, candidates_token_count=salida
        ),
    )


def llamada(herramienta: str, entrada: int, salida: int) -> LlmResponse:
    return LlmResponse(
        content=types.Content(
            role="model",
            parts=[
                types.Part(
                    function_call=types.FunctionCall(name=herramienta, args={"request": "x"})
                )
            ],
        ),
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=entrada, candidates_token_count=salida
        ),
    )


async def correr(
    agente: LlmAgent, plugin: PluginMedicion, estado: dict[str, Any] | None = None
) -> None:
    runner = InMemoryRunner(app=App(name="prueba", root_agent=agente, plugins=[plugin]))
    sesion = await runner.session_service.create_session(
        app_name="prueba", user_id="u1", state=estado or {}
    )
    async for _ in runner.run_async(
        user_id="u1",
        session_id=sesion.id,
        new_message=types.Content(role="user", parts=[types.Part(text="hola")]),
    ):
        pass


async def test_mide_raiz_y_especialista():
    registros: list[dict[str, Any]] = []
    plugin = PluginMedicion(app="iterum", emisor=registros.append)
    especialista = LlmAgent(
        name="guia",
        model=LlmFalso(model="gemini-3.5-flash-lite", guion=[texto("lugares", 2_000, 100)]),
    )
    raiz = LlmAgent(
        name="concierge",
        model=LlmFalso(
            model="gemini-3.8-flash",
            guion=[llamada("guia", 10_000, 50), texto("listo", 12_000, 300)],
        ),
        tools=[AgentTool(agent=especialista)],
    )

    await correr(raiz, plugin, {"usuario_interno": True})

    assert [(r["agente"], r["modelo"]) for r in registros] == [
        ("concierge", "gemini-3.8-flash"),
        ("guia", "gemini-3.5-flash-lite"),
        ("concierge", "gemini-3.8-flash"),
    ]
    assert registros[0]["costo_usd"] == pytest.approx((10_000 * 1.50 + 50 * 7.50) / 1e6)
    assert registros[1]["costo_usd"] == pytest.approx((2_000 * 0.30 + 100 * 2.50) / 1e6)
    assert all(r["tipo"] == "llamada_modelo" and r["app"] == "iterum" for r in registros)
    assert registros[0]["uid"] == "u1" and registros[0]["usuario_interno"] is True
    assert all(r["error"] is None for r in registros)


async def test_modelo_sin_precio_no_rompe_la_conversacion():
    registros: list[dict[str, Any]] = []
    agente = LlmAgent(
        name="raro", model=LlmFalso(model="modelo-desconocido", guion=[texto("ok", 10, 10)])
    )
    await correr(agente, PluginMedicion(app="domi", emisor=registros.append))
    assert registros[0]["costo_usd"] is None
    assert registros[0]["error"] == "precio_desconocido"
    assert registros[0]["usuario_interno"] is False


def test_fabrica_de_modelos():
    assert isinstance(modelo_adk("gemini-3.8-flash"), Gemini)
    with pytest.raises(ValueError, match="Model Garden"):
        modelo_adk("gpt-5")


def test_resultado_y_salida_json(capsys):
    emitir_resultado("domi", "visita_agendada", "inm-1", "u1", emisor=emitir_stdout)
    linea = json.loads(capsys.readouterr().out)
    assert linea["tipo"] == linea["message"] == "resultado_entregado"
    assert linea["resultado_tipo"] == "visita_agendada" and linea["severity"] == "INFO"


def test_plugin_avisa_que_es_obsoleto():
    with pytest.warns(DeprecationWarning, match="BigQueryAgentAnalyticsPlugin"):
        PluginMedicion(app="iterum")
