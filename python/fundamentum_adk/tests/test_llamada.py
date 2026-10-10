"""Llamadas de una sola vuelta: texto, uso, costo, plugins y esquema, con un modelo falso."""

import asyncio

import pytest
from fundamentum_adk import SalidaVacia, agente_unico, llamar, llamar_sync
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin
from google.genai import types
from pydantic import BaseModel, Field


class LlmFijo(BaseLlm):
    respuesta: str
    peticiones: list = Field(default_factory=list)

    async def generate_content_async(self, llm_request, stream=False):
        self.peticiones.append(llm_request)
        yield LlmResponse(
            content=types.Content(role="model", parts=[types.Part(text=self.respuesta)]),
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=10_000, candidates_token_count=200
            ),
        )


class Observador(BasePlugin):
    def __init__(self) -> None:
        super().__init__(name="testigo")
        self.agentes: list[str] = []
        self.cerrado = False

    async def after_model_callback(self, *, callback_context, llm_response):
        self.agentes.append(callback_context.agent_name)

    async def close(self) -> None:
        self.cerrado = True


class Reserva(BaseModel):
    nombre: str


def fijo(respuesta: str = '{"nombre": "Alfama"}') -> LlmFijo:
    return LlmFijo(model="gemini-3.5-flash-lite", respuesta=respuesta)


async def test_texto_uso_y_costo():
    llm = fijo()
    r = await llamar(agente_unico("lector", llm, Reserva), ["lee esto"])
    assert r.texto == '{"nombre": "Alfama"}' and r.modelo == "gemini-3.5-flash-lite"
    assert r.uso.entrada == 10_000 and r.uso.salida == 200
    assert r.costo_usd() == pytest.approx((10_000 * 0.30 + 200 * 2.50) / 1e6)


async def test_esquema_temperatura_y_sin_historial():
    llm = fijo()
    agente = agente_unico("lector", llm, {"type": "OBJECT"}, temperatura=0)
    await llamar(agente, ["hola"])
    [peticion] = llm.peticiones
    assert peticion.config.response_mime_type == "application/json"
    assert peticion.config.response_schema is not None and peticion.config.temperature == 0
    assert agente.tools == [] and agente.include_contents == "none"


async def test_la_instruccion_con_llaves_no_se_interpreta():
    llm = fijo()
    await llamar(agente_unico("lector", llm, instruccion='Devuelve {"nombre": ...}'), ["x"])
    assert 'Devuelve {"nombre": ...}' in str(llm.peticiones[0].config.system_instruction)


async def test_los_plugins_de_la_app_alcanzan_la_llamada_y_no_se_cierran():
    testigo = Observador()
    await llamar(agente_unico("lector", fijo()), ["x"], plugins=[testigo], usuario="u1")
    assert testigo.agentes == ["lector"] and not testigo.cerrado


async def test_sin_texto_falla_en_voz_alta():
    with pytest.raises(SalidaVacia):
        await llamar(agente_unico("lector", fijo("")), ["x"])


def test_sync_fuera_y_dentro_de_un_loop():
    assert llamar_sync(agente_unico("lector", fijo()), ["x"]).texto

    async def dentro():
        return llamar_sync(agente_unico("lector", fijo()), ["x"]).texto

    assert asyncio.run(dentro())


async def test_modelo_sin_precio_no_cuesta_cero():
    r = await llamar(agente_unico("raro", LlmFijo(model="raro", respuesta="ok")), ["x"])
    with pytest.raises(KeyError):
        r.costo_usd()
