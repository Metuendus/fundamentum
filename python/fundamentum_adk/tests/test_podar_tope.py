"""Ahorro de contexto (1.4.1): podar lecturas repetidas del prompt, tope de llamadas por mensaje, y
`PluginResumen` que ya no corta el `on_event_callback` de los plugins que lo siguen."""

from fundamentum_adk import (
    MENSAJE_TOPE,
    Conversacion,
    PluginPodar,
    PluginResumen,
    PluginTopeLlamadas,
)
from fundamentum_adk.contexto import OMITIDA
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .test_conversacion import agente, guion, turno, ver_inmueble


def _respuestas(peticion) -> list[dict]:
    return [
        p.function_response.response
        for c in peticion.contents
        for p in c.parts or []
        if p.function_response is not None
    ]


async def test_podar_deja_solo_la_lectura_mas_reciente_en_el_prompt():
    llm = guion(
        types.FunctionCall(name="ver_inmueble", args={"inmueble_id": "i1"}),
        ["Visto i1."],
        types.FunctionCall(name="ver_inmueble", args={"inmueble_id": "i2"}),
        ["Visto i2."],
    )
    sesiones = InMemorySessionService()
    conv = Conversacion(
        agente(llm, [ver_inmueble]), plugins=[PluginPodar(["ver_inmueble"])], sesiones=sesiones
    )
    fin = (await turno(conv, "i1", usuario="u1", estado={"uid": "u1"}))[-1]
    await turno(conv, "i2", usuario="u1", sesion_id=fin.sesion_id)

    ultima = llm.peticiones[-1]
    respuestas = _respuestas(ultima)
    assert respuestas[0] == OMITIDA
    assert respuestas[1]["inmueble_id"] == "i2"
    # La sesión (historial visible) no cambia.
    sesion = await sesiones.get_session(
        app_name="fundamentum", user_id="u1", session_id=fin.sesion_id
    )
    guardadas = [r.response for e in sesion.events for r in e.get_function_responses()]
    assert [r["inmueble_id"] for r in guardadas] == ["i1", "i2"]


async def test_tope_de_llamadas_corta_un_bucle():
    llm = guion(*[types.FunctionCall(name="ver_inmueble", args={"inmueble_id": "i"})] * 10)
    conv = Conversacion(agente(llm, [ver_inmueble]), plugins=[PluginTopeLlamadas(maximo=3)])
    eventos = await turno(conv, "bucle", usuario="u1", estado={"uid": "u1"})
    assert len(llm.peticiones) == 3
    assert eventos[-1].texto == MENSAJE_TOPE


class Mirador(BasePlugin):
    def __init__(self) -> None:
        super().__init__(name="testigo")
        self.finales = 0

    async def on_event_callback(self, *, invocation_context, event):
        if event.is_final_response() and not event.partial:
            self.finales += 1
        return None


async def test_resumen_no_corta_a_los_plugins_que_siguen():
    testigo = Mirador()
    sesiones = InMemorySessionService()
    conv = Conversacion(
        agente(guion(["Hola."])), plugins=[PluginResumen("domi"), testigo], sesiones=sesiones
    )
    fin = (await turno(conv, "hola", usuario="u1", estado={"uid": "u1"}))[-1]
    assert testigo.finales == 1
    sesion = await sesiones.get_session(
        app_name="fundamentum", user_id="u1", session_id=fin.sesion_id
    )
    assert (
        sesion.state["historial_titulo"] == "hola" and sesion.state["historial_ultimo"] == "Hola."
    )
