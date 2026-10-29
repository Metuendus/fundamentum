"""Conversación en flujo: trozos, herramientas, historial, identidad, plugins y costo, con un modelo
falso."""

import pytest
from fundamentum_adk import (
    Conversacion,
    Fin,
    LlamadaHerramienta,
    PluginAlcance,
    PluginPresupuesto,
    RespuestaHerramienta,
    Trozo,
)
from google.adk.agents import LlmAgent
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from pydantic import Field

USO = types.GenerateContentResponseUsageMetadata(
    prompt_token_count=1_000, candidates_token_count=100
)


def _respuesta(*partes: types.Part, partial: bool = False, uso: bool = True) -> LlmResponse:
    return LlmResponse(
        content=types.Content(role="model", parts=list(partes)),
        partial=partial,
        usage_metadata=USO if uso else None,
    )


class LlmGuion(BaseLlm):
    """Responde según el guion, una entrada por llamada al modelo. Una entrada es una lista de
    trozos de texto (en flujo) o una llamada a herramienta."""

    guion: list = Field(default_factory=list)
    peticiones: list = Field(default_factory=list)

    async def generate_content_async(self, llm_request, stream=False):
        self.peticiones.append(llm_request)
        paso = self.guion.pop(0)
        if isinstance(paso, types.FunctionCall):
            yield _respuesta(types.Part(function_call=paso))
            return
        if stream:
            for trozo in paso:
                yield _respuesta(types.Part(text=trozo), partial=True, uso=False)
        yield _respuesta(types.Part(text="".join(paso)))


def guion(*pasos) -> LlmGuion:
    return LlmGuion(model="gemini-3.8-flash", guion=list(pasos))


def ver_inmueble(inmueble_id: str, tool_context: ToolContext) -> dict:
    """Desglose de un inmueble."""
    return {"inmueble_id": inmueble_id, "uid": tool_context.state.get("uid")}


def agente(llm: BaseLlm, herramientas=()) -> LlmAgent:
    return LlmAgent(name="domi", model=llm, instruction="Eres Domi.", tools=list(herramientas))


async def turno(conv: Conversacion, mensaje: str, **kwargs) -> list:
    return [e async for e in conv.conversar(mensaje, **kwargs)]


async def test_trozos_en_flujo_y_fin_con_costo():
    conv = Conversacion(agente(guion(["Hola, ", "soy Domi."])))
    eventos = await turno(conv, "hola", usuario="u1", estado={"uid": "u1"})
    assert eventos[:2] == [Trozo("Hola, "), Trozo("soy Domi.")]
    [fin] = eventos[2:]
    assert (
        isinstance(fin, Fin) and fin.texto == "Hola, soy Domi." and fin.modelo == "gemini-3.8-flash"
    )
    assert fin.uso.entrada == 1_000 and fin.uso.salida == 100 and fin.costo_usd() > 0


async def test_sin_flujo_el_texto_va_entero():
    conv = Conversacion(agente(guion(["Hola, ", "soy Domi."])), en_flujo=False)
    eventos = await turno(conv, "hola", usuario="u1")
    assert eventos[0] == Trozo("Hola, soy Domi.") and isinstance(eventos[1], Fin)


async def test_herramienta_con_identidad_del_estado():
    llm = guion(types.FunctionCall(name="ver_inmueble", args={"inmueble_id": "i-1"}), ["Listo."])
    conv = Conversacion(agente(llm, [ver_inmueble]))
    eventos = await turno(conv, "¿y este?", usuario="u1", estado={"uid": "u1"})
    assert LlamadaHerramienta("ver_inmueble", {"inmueble_id": "i-1"}) in eventos
    assert RespuestaHerramienta("ver_inmueble", {"inmueble_id": "i-1", "uid": "u1"}) in eventos
    fin = eventos[-1]
    assert fin.texto == "Listo." and len(fin.usos) == 2


async def test_el_historial_sigue_en_la_misma_sesion():
    llm = guion(["Uno."], ["Dos."])
    conv = Conversacion(agente(llm))
    primero = await turno(conv, "a", usuario="u1")
    sesion = primero[-1].sesion_id
    segundo = await turno(conv, "b", usuario="u1", sesion_id=sesion)
    assert segundo[-1].sesion_id == sesion
    textos = [p.text for c in llm.peticiones[1].contents for p in c.parts if p.text]
    assert textos == ["a", "Uno.", "b"]


async def test_otra_persona_no_ve_el_historial():
    llm = guion(["Uno."], ["Dos."])
    conv = Conversacion(agente(llm))
    sesion = (await turno(conv, "secreto", usuario="u1"))[-1].sesion_id
    await turno(conv, "b", usuario="u2", sesion_id=sesion)
    textos = [p.text for c in llm.peticiones[1].contents for p in c.parts if p.text]
    assert "secreto" not in textos


async def test_el_estado_del_servidor_se_reescribe_en_cada_turno():
    llm = guion(
        ["Uno."], types.FunctionCall(name="ver_inmueble", args={"inmueble_id": "i-1"}), ["Ok."]
    )
    conv = Conversacion(agente(llm, [ver_inmueble]))
    sesion = (await turno(conv, "a", usuario="u1", estado={"uid": "otro"}))[-1].sesion_id
    eventos = await turno(conv, "b", usuario="u1", sesion_id=sesion, estado={"uid": "u1"})
    assert RespuestaHerramienta("ver_inmueble", {"inmueble_id": "i-1", "uid": "u1"}) in eventos


async def test_alcance_bloquea_sin_identidad():
    llm = guion(types.FunctionCall(name="ver_inmueble", args={"inmueble_id": "i-1"}), ["No pude."])
    conv = Conversacion(agente(llm, [ver_inmueble]), plugins=[PluginAlcance()])
    eventos = await turno(conv, "x", usuario="u1")
    [resp] = [e for e in eventos if isinstance(e, RespuestaHerramienta)]
    assert "error" in resp.respuesta


async def test_presupuesto_agotado_responde_sin_modelo():
    llm = guion()
    conv = Conversacion(agente(llm), plugins=[PluginPresupuesto(lambda uid, _r: True)])
    eventos = await turno(conv, "x", usuario="u1")
    assert llm.peticiones == [] and "límite" in eventos[0].texto
    assert eventos[-1].usos == []


class Observador(BasePlugin):
    def __init__(self) -> None:
        super().__init__(name="testigo")
        self.cerrado = False

    async def close(self) -> None:
        self.cerrado = True


async def test_los_plugins_de_la_app_no_se_cierran():
    testigo = Observador()
    conv = Conversacion(agente(guion(["a"])), plugins=[testigo])
    await turno(conv, "x", usuario="u1")
    await conv.runner.close()
    assert not testigo.cerrado


async def test_modelo_sin_precio_falla_en_voz_alta():
    llm = LlmGuion(model="modelo-sin-precio", guion=[["a"]])
    eventos = await turno(Conversacion(agente(llm)), "x", usuario="u1")
    with pytest.raises(KeyError):
        eventos[-1].costo_usd()
