"""Resultados entregados, analítica estándar y fábrica de modelos."""

import json

import pytest
from fundamentum_adk import analitica, emitir_resultado, emitir_stdout, modelo_adk
from google.adk.models import Gemini


def test_fabrica_de_modelos():
    gemini = modelo_adk("gemini-3.8-flash", proyecto="vocatio-mx", credenciales="cred")
    assert isinstance(gemini, Gemini)
    assert gemini.client_kwargs == {
        "location": "global",
        "vertexai": True,
        "project": "vocatio-mx",
        "credentials": "cred",
    }
    assert modelo_adk("gemini-3.8-flash").client_kwargs == {"location": "global"}
    with pytest.raises(ValueError, match="Model Garden"):
        modelo_adk("gpt-5")


def test_resultado_y_salida_json(capsys):
    emitir_resultado("domi", "visita_agendada", "inm-1", "u1", emisor=emitir_stdout)
    linea = json.loads(capsys.readouterr().out)
    assert linea["tipo"] == linea["message"] == "resultado_entregado"
    assert linea["resultado_tipo"] == "visita_agendada" and linea["severity"] == "INFO"


def test_analitica_sin_dataset_no_mide(monkeypatch):
    monkeypatch.delenv("DOMI_ANALITICA_DATASET", raising=False)
    assert analitica("domi") == []


def test_analitica_con_dataset_no_guarda_la_conversacion(monkeypatch):
    monkeypatch.setenv("VOCATIO_ANALITICA_DATASET", "agentes")
    [plugin] = analitica("vocatio", proyecto="vocatio-mx")
    assert (plugin.project_id, plugin.dataset_id) == ("vocatio-mx", "agentes")
    assert {"content", "content_parts"} <= set(plugin.config.payload_column_denylist)
    assert plugin.config.log_session_metadata is False
    assert "STATE_DELTA" in plugin.config.event_denylist
    assert plugin.config.custom_tags == {"app": "vocatio"}


async def test_cada_intento_de_gemini_lleva_tope(monkeypatch):
    from fundamentum_adk import ESPERA_MS
    from google.adk.models.llm_request import LlmRequest
    from google.genai import types

    vistas = []

    async def generar(self, llm_request, stream=False):
        vistas.append(llm_request.config.http_options.timeout)
        yield "ok"

    monkeypatch.setattr(Gemini, "generate_content_async", generar)
    gemini = modelo_adk("gemini-3.8-flash")
    propia = LlmRequest(
        config=types.GenerateContentConfig(http_options=types.HttpOptions(timeout=5))
    )
    for peticion in (LlmRequest(), propia):
        assert [r async for r in gemini.generate_content_async(peticion)] == ["ok"]
    assert vistas == [ESPERA_MS, 5]


async def test_un_corte_antes_de_responder_se_reintenta(monkeypatch):
    from fundamentum_adk import modelos
    from google.adk.models.llm_request import LlmRequest

    intentos = []

    async def generar(self, llm_request, stream=False):
        intentos.append(1)
        if len(intentos) < modelos.INTENTOS_ESPERA:
            raise TimeoutError
        yield "ok"

    monkeypatch.setattr(Gemini, "generate_content_async", generar)
    gemini = modelo_adk("gemini-3.8-flash")
    assert [r async for r in gemini.generate_content_async(LlmRequest())] == ["ok"]
    assert len(intentos) == modelos.INTENTOS_ESPERA

    async def siempre(self, llm_request, stream=False):
        intentos.append(1)
        raise TimeoutError
        yield

    intentos.clear()
    monkeypatch.setattr(Gemini, "generate_content_async", siempre)
    with pytest.raises(TimeoutError):
        [r async for r in gemini.generate_content_async(LlmRequest())]
    assert len(intentos) == modelos.INTENTOS_ESPERA


async def test_un_corte_a_media_respuesta_no_se_repite(monkeypatch):
    from google.adk.models.llm_request import LlmRequest

    async def generar(self, llm_request, stream=False):
        yield "parte"
        raise TimeoutError

    monkeypatch.setattr(Gemini, "generate_content_async", generar)
    vistas = []
    with pytest.raises(TimeoutError):
        async for r in modelo_adk("gemini-3.8-flash").generate_content_async(LlmRequest(), True):
            vistas.append(r)
    assert vistas == ["parte"]
