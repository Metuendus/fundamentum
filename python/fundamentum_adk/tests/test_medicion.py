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
