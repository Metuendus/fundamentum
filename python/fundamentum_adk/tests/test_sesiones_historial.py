"""Historial visible leído de las sesiones de ADK, sesiones de Agent Platform y contexto largo.

Las pruebas usan el servicio en memoria de ADK: `Historial` y `PluginResumen` solo dependen de la
interfaz `BaseSessionService`, que Agent Platform Sessions implementa igual.
"""

import pytest
from fundamentum_adk import (
    RETENCION,
    Conversacion,
    Fin,
    Historial,
    PluginResumen,
    SesionAjena,
    contexto,
    sesiones_agent_platform,
)
from fundamentum_adk.sesiones import opciones_por_omision
from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService, VertexAiSessionService
from google.adk.tools import AgentTool
from google.genai import types

from .test_conversacion import guion, ver_inmueble


def test_contexto_compacta_por_omision_y_cache_opcional():
    base = contexto()
    assert base["events_compaction_config"].token_threshold == 60_000
    assert "context_cache_config" not in base
    assert contexto(compactar=False) == {}
    assert contexto(cache=True)["context_cache_config"].min_tokens == 4096


def test_sesiones_de_agent_platform_vencen_a_los_365_dias():
    servicio = sesiones_agent_platform(
        "domi-mx", "projects/1/locations/us-central1/reasoningEngines/987"
    )
    assert isinstance(servicio, VertexAiSessionService)
    assert servicio._agent_engine_id == "987"
    assert opciones_por_omision(servicio) == {"ttl": RETENCION} and RETENCION == "31536000s"
    assert opciones_por_omision(InMemorySessionService()) == {}


def _chat(llm, sesiones, **historial):
    agente = LlmAgent(name="domi", model=llm, instruction="Eres Domi.", tools=[ver_inmueble])
    conv = Conversacion(agente, plugins=[PluginResumen("domi")], app="domi", sesiones=sesiones)
    return conv, Historial(sesiones, app="domi", agente="domi", **historial)


async def _turno(conv, texto, **kw):
    return [e async for e in conv.conversar(texto, usuario="u1", **kw)]


async def test_historial_lista_y_traduce_las_conversaciones():
    sesiones = InMemorySessionService()
    llm = guion(
        types.FunctionCall(name="ver_inmueble", args={"inmueble_id": "i9"}),
        ["Te ", "muestro i9."],
        ["Sí, i9."],
        ["Hola de nuevo."],
    )
    conv, historial = _chat(
        llm,
        sesiones,
        enlazar=lambda nombre, r: (
            [{"tipo": "inmueble", "id": r["inmueble_id"]}] if nombre == "ver_inmueble" else []
        ),
    )
    estado = {"uid": "u1", "perfil_id": "p1"}
    fin = (await _turno(conv, "muéstrame i9", estado=estado))[-1]
    await _turno(conv, "¿y ese?", sesion_id=fin.sesion_id, estado=estado)
    otra = (await _turno(conv, "hola", estado={"uid": "u1", "perfil_id": "p2"}))[-1]

    recientes = await historial.listar("u1")
    assert [c.id for c in recientes] == [otra.sesion_id, fin.sesion_id]
    [del_perfil] = await historial.listar("u1", filtro={"perfil_id": "p1"})
    assert del_perfil.titulo == "muéstrame i9" and del_perfil.ultimo == "Sí, i9."
    assert await historial.listar("u2") == []

    mensajes = await historial.mensajes("u1", fin.sesion_id)
    assert [(m.rol, m.texto) for m in mensajes] == [
        ("persona", "muéstrame i9"),
        ("agente", "Te muestro i9."),
        ("persona", "¿y ese?"),
        ("agente", "Sí, i9."),
    ]
    assert [(f.herramienta, f.estado) for f in mensajes[1].filas] == [("ver_inmueble", "hecho")]
    assert mensajes[1].enlaces == [{"tipo": "inmueble", "id": "i9"}]
    assert all(m.estado == "completo" for m in mensajes)

    await historial.borrar("u1", fin.sesion_id)
    assert [c.id for c in await historial.listar("u1")] == [otra.sesion_id]
    assert await historial.borrar_usuario("u1") == 1
    assert await historial.listar("u1") == []


async def test_un_turno_sin_respuesta_se_marca():
    conv, historial = _chat(guion(["Hola."]), InMemorySessionService())
    fin = (await _turno(conv, "hola", estado={"uid": "u1"}))[-1]
    sesion = await historial.sesiones.get_session(
        app_name="domi", user_id="u1", session_id=fin.sesion_id
    )
    # Se cortó la conexión: el mensaje de la persona quedó, la respuesta no.
    from google.adk.events.event import Event

    pregunta = Event(
        author="user",
        invocation_id="corte",
        content=types.Content(role="user", parts=[types.Part(text="¿sigues?")]),
    )
    await historial.sesiones.append_event(sesion, pregunta)
    mensajes = await historial.mensajes("u1", fin.sesion_id)
    assert [m.texto for m in mensajes] == ["hola", "Hola.", "¿sigues?"]


async def test_especialistas_no_cuentan_como_respuesta():
    sesiones = InMemorySessionService()
    especialista = LlmAgent(name="cotizador", model=guion(["120 EUR"]), instruction="Cotiza.")
    raiz = LlmAgent(
        name="concierge",
        model=guion(
            types.FunctionCall(name="cotizador", args={"request": "hotel"}), ["Cuesta 120 EUR."]
        ),
        instruction="Eres el Concierge.",
        tools=[AgentTool(especialista)],
    )
    conv = Conversacion(raiz, plugins=[PluginResumen("concierge")], app="iterum", sesiones=sesiones)
    fin = [e async for e in conv.conversar("¿hotel?", usuario="u1", estado={"uid": "u1"})][-1]
    historial = Historial(sesiones, app="iterum", agente="concierge")
    [c] = await historial.listar("u1")
    assert c.titulo == "¿hotel?" and c.ultimo == "Cuesta 120 EUR."
    mensajes = await historial.mensajes("u1", fin.sesion_id)
    assert [m.texto for m in mensajes] == ["¿hotel?", "Cuesta 120 EUR."]
    assert [f.herramienta for f in mensajes[1].filas] == ["cotizador"]


async def test_texto_de_contexto_no_aparece_en_el_historial():
    def limpiar(texto: str) -> str:
        return texto.split("\n", 1)[-1] if texto.startswith("(Contexto") else texto

    sesiones = InMemorySessionService()
    agente = LlmAgent(name="domi", model=guion(["Claro."]), instruction="Eres Domi.")
    conv = Conversacion(
        agente,
        plugins=[PluginResumen("domi", texto_persona=limpiar)],
        app="domi",
        sesiones=sesiones,
    )
    fin = [
        e
        async for e in conv.conversar(
            ["(Contexto: viendo i9.)", "\n¿me conviene?"], usuario="u1", estado={"uid": "u1"}
        )
    ][-1]
    historial = Historial(sesiones, app="domi", agente="domi", texto_persona=limpiar)
    [c] = await historial.listar("u1")
    assert c.titulo == "¿me conviene?"
    assert (await historial.mensajes("u1", fin.sesion_id))[0].texto == "¿me conviene?"


async def test_sesion_ajena_en_agent_platform():
    class Ajenas(InMemorySessionService):
        async def get_session(self, **kwargs):
            raise ValueError("Session s1 does not belong to user u2.")

    conv = Conversacion(
        LlmAgent(name="domi", model=guion(["x"]), instruction="Eres Domi."), sesiones=Ajenas()
    )
    with pytest.raises(SesionAjena):
        [e async for e in conv.conversar("hola", usuario="u2", sesion_id="s1")]


async def test_id_vencido_abre_sesion_nueva():
    conv, _ = _chat(guion(["Hola."]), InMemorySessionService())
    fin = (await _turno(conv, "hola", sesion_id="ya-no-existe", estado={"uid": "u1"}))[-1]
    assert isinstance(fin, Fin) and fin.sesion_id != "ya-no-existe"


async def test_turno_lleva_su_trace_id():
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider

    if not hasattr(trace.get_tracer_provider(), "add_span_processor"):
        trace.set_tracer_provider(TracerProvider())
    conv, historial = _chat(guion(["Hola."]), InMemorySessionService())
    fin = (await _turno(conv, "hola", estado={"uid": "u1"}))[-1]
    assert fin.trace_id and len(fin.trace_id) == 32
    [_, respuesta] = await historial.mensajes("u1", fin.sesion_id)
    assert respuesta.trace_id == fin.trace_id
