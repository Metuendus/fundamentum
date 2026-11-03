"""Sesiones de ADK e historial visible en Firestore, contra el emulador.

Corre con `FIRESTORE_EMULATOR_HOST` (p. ej. `firebase emulators:start --only firestore`); sin él,
estas pruebas se saltan. La parte que no necesita Firestore (serializar eventos grandes, contexto
largo) corre siempre.
"""

import os
import uuid

import pytest
from fundamentum_adk import (
    Conversacion,
    Fin,
    Historial,
    PluginHistorial,
    SesionesFirestore,
    contexto,
)
from fundamentum_adk.sesiones import MAX_EVENTO_BYTES, serializar_evento
from google.adk.agents import LlmAgent
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.sessions.base_session_service import GetSessionConfig
from google.adk.tools import AgentTool
from google.genai import types

from .test_conversacion import guion, ver_inmueble

EMULADOR = os.environ.get("FIRESTORE_EMULATOR_HOST")
con_emulador = pytest.mark.skipif(not EMULADOR, reason="sin emulador de Firestore")


def _cliente():
    from google.cloud import firestore

    return firestore.AsyncClient(project="demo-fundamentum")


def _raiz() -> str:
    return f"prueba-{uuid.uuid4().hex[:8]}"


def _evento(texto: str, autor: str = "user", ts: float | None = None, **acciones) -> Event:
    evento = Event(
        author=autor,
        invocation_id="inv",
        content=types.Content(
            role="user" if autor == "user" else "model", parts=[types.Part(text=texto)]
        ),
        actions=EventActions(**acciones),
    )
    if ts is not None:
        evento.timestamp = ts
    return evento


def test_evento_grande_pierde_sus_adjuntos_en_linea():
    grande = Event(
        author="user",
        invocation_id="inv",
        content=types.Content(
            role="user",
            parts=[
                types.Part(text="mi CV"),
                types.Part.from_bytes(data=b"x" * MAX_EVENTO_BYTES, mime_type="application/pdf"),
            ],
        ),
    )
    texto = serializar_evento(grande)
    assert len(texto.encode()) < MAX_EVENTO_BYTES
    leido = Event.model_validate_json(texto)
    assert leido.content.parts[0].text == "mi CV"
    assert "application/pdf" in leido.content.parts[1].text
    chico = _evento("hola")
    assert Event.model_validate_json(serializar_evento(chico)) == chico


def test_contexto_compacta_por_omision_y_cache_opcional():
    base = contexto()
    assert base["events_compaction_config"].token_threshold == 60_000
    assert "context_cache_config" not in base
    assert contexto(compactar=False) == {}
    assert contexto(cache=True)["context_cache_config"].min_tokens == 4096


@con_emulador
async def test_sesion_persiste_eventos_y_estado_por_alcance():
    servicio = SesionesFirestore(_cliente(), raiz=_raiz())
    sesion = await servicio.create_session(
        app_name="domi",
        user_id="u1",
        state={"uid": "u1", "user:idioma": "es", "app:version": 2, "temp:x": 1},
    )
    assert sesion.state == {"uid": "u1", "user:idioma": "es", "app:version": 2}

    await servicio.append_event(sesion, _evento("hola", ts=100.0))
    await servicio.append_event(
        sesion, _evento("¿qué tal?", autor="domi", ts=101.0, state_delta={"paso": 1, "temp:y": 2})
    )
    # Otro proceso (otra instancia de Cloud Run) la lee igual.
    otro = SesionesFirestore(_cliente(), raiz=servicio.raiz)
    leida = await otro.get_session(app_name="domi", user_id="u1", session_id=sesion.id)
    assert [e.content.parts[0].text for e in leida.events] == ["hola", "¿qué tal?"]
    assert leida.state == {"uid": "u1", "paso": 1, "user:idioma": "es", "app:version": 2}
    assert leida.last_update_time == 101.0

    ultimos = await otro.get_session(
        app_name="domi",
        user_id="u1",
        session_id=sesion.id,
        config=GetSessionConfig(num_recent_events=1),
    )
    assert [e.content.parts[0].text for e in ultimos.events] == ["¿qué tal?"]
    despues = await otro.get_session(
        app_name="domi",
        user_id="u1",
        session_id=sesion.id,
        config=GetSessionConfig(after_timestamp=100.5),
    )
    assert len(despues.events) == 1
    assert await otro.get_user_state(app_name="domi", user_id="u1") == {"idioma": "es"}


@con_emulador
async def test_sesiones_son_por_usuario_y_se_borran():
    servicio = SesionesFirestore(_cliente(), raiz=_raiz())
    propia = await servicio.create_session(app_name="domi", user_id="u1", session_id="s1")
    assert await servicio.get_session(app_name="domi", user_id="u2", session_id="s1") is None
    ajena = await servicio.create_session(app_name="domi", user_id="u2", session_id="s1")
    await servicio.append_event(ajena, _evento("de u2"))
    leida = await servicio.get_session(app_name="domi", user_id="u1", session_id="s1")
    assert leida.events == []

    from google.adk.errors.already_exists_error import AlreadyExistsError

    with pytest.raises(AlreadyExistsError):
        await servicio.create_session(app_name="domi", user_id="u1", session_id="s1")

    lista = await servicio.list_sessions(app_name="domi", user_id="u1")
    assert [s.id for s in lista.sessions] == [propia.id]
    await servicio.delete_session(app_name="domi", user_id="u1", session_id="s1")
    assert await servicio.get_session(app_name="domi", user_id="u1", session_id="s1") is None
    assert await servicio.get_session(app_name="domi", user_id="u2", session_id="s1") is not None


@con_emulador
async def test_conversacion_recuerda_tras_reinicio_y_escribe_historial():
    raiz = _raiz()
    historial = Historial(_cliente(), raiz=f"{raiz}-historial")

    def nueva(llm):
        agente = LlmAgent(name="domi", model=llm, instruction="Eres Domi.", tools=[ver_inmueble])
        plugin = PluginHistorial(
            historial,
            agente="domi",
            app="domi",
            recursos={"perfil_id": "perfil"},
            enlazar=lambda nombre, r: (
                [{"tipo": "inmueble", "id": r["inmueble_id"]}] if nombre == "ver_inmueble" else []
            ),
        )
        return Conversacion(
            agente, plugins=[plugin], app="domi", sesiones=SesionesFirestore(_cliente(), raiz=raiz)
        )

    llm = guion(
        types.FunctionCall(name="ver_inmueble", args={"inmueble_id": "i9"}),
        ["Te ", "muestro i9."],
    )
    primera = [
        e
        async for e in nueva(llm).conversar(
            "muéstrame i9", usuario="u1", estado={"uid": "u1", "perfil_id": "p1"}
        )
    ]
    fin = primera[-1]
    assert isinstance(fin, Fin)

    # Proceso nuevo (Cloud Run escaló a cero): el agente ve el turno anterior.
    llm2 = guion(["Sí, i9."])
    segunda = [
        e
        async for e in nueva(llm2).conversar(
            "¿y ese?",
            usuario="u1",
            sesion_id=fin.sesion_id,
            estado={"uid": "u1", "perfil_id": "p1"},
        )
    ]
    assert segunda[-1].sesion_id == fin.sesion_id
    vistos = [p.text for c in llm2.peticiones[0].contents for p in c.parts or [] if p.text]
    assert "muéstrame i9" in vistos and "Te muestro i9." in vistos

    [conv] = await historial.listar("u1", app="domi")
    assert conv["id"] == fin.sesion_id and conv["titulo"] == "muéstrame i9"
    assert conv["recurso"] == {"tipo": "perfil", "id": "p1"} and conv["ultimo"] == "Sí, i9."
    mensajes = await historial.mensajes("u1", fin.sesion_id)
    assert [(m["rol"], m["texto"]) for m in mensajes] == [
        ("persona", "muéstrame i9"),
        ("agente", "Te muestro i9."),
        ("persona", "¿y ese?"),
        ("agente", "Sí, i9."),
    ]
    assert mensajes[1]["filas"] == [{"herramienta": "ver_inmueble", "estado": "hecho"}]
    assert mensajes[1]["enlaces"] == [{"tipo": "inmueble", "id": "i9"}]
    assert mensajes[1]["estado"] == "completo" and mensajes[1]["vence"]

    await historial.borrar("u1", fin.sesion_id)
    assert await historial.listar("u1") == []


@con_emulador
async def test_especialistas_no_abren_conversacion_propia():
    historial = Historial(_cliente(), raiz=_raiz())
    especialista = LlmAgent(name="cotizador", model=guion(["120 EUR"]), instruction="Cotiza.")
    raiz = LlmAgent(
        name="concierge",
        model=guion(
            types.FunctionCall(name="cotizador", args={"request": "hotel"}), ["Cuesta 120 EUR."]
        ),
        instruction="Eres el Concierge.",
        tools=[AgentTool(especialista)],
    )
    conv = Conversacion(
        raiz,
        plugins=[PluginHistorial(historial, agente="concierge", app="iterum")],
        app="iterum",
    )
    [*_, fin] = [e async for e in conv.conversar("¿hotel?", usuario="u1", estado={"uid": "u1"})]
    conversaciones = await historial.listar("u1")
    assert [c["id"] for c in conversaciones] == [fin.sesion_id]
    mensajes = await historial.mensajes("u1", fin.sesion_id)
    assert [m["texto"] for m in mensajes] == ["¿hotel?", "Cuesta 120 EUR."]
    assert mensajes[1]["filas"] == [{"herramienta": "cotizador", "estado": "hecho"}]


@con_emulador
async def test_historial_no_rompe_la_conversacion():
    class Roto(Historial):
        async def agregar(self, *a, **k):
            raise RuntimeError("Firestore caído")

    conv = Conversacion(
        LlmAgent(name="domi", model=guion(["Hola."]), instruction="Eres Domi."),
        plugins=[PluginHistorial(Roto(_cliente()), agente="domi", app="domi")],
        app="domi",
    )
    [*_, fin] = [e async for e in conv.conversar("hola", usuario="u1", estado={"uid": "u1"})]
    assert fin.texto == "Hola."


@con_emulador
async def test_turno_lleva_su_trace_id():
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider

    if not hasattr(trace.get_tracer_provider(), "add_span_processor"):
        trace.set_tracer_provider(TracerProvider())
    historial = Historial(_cliente(), raiz=_raiz())
    conv = Conversacion(
        LlmAgent(name="domi", model=guion(["Hola."]), instruction="Eres Domi."),
        plugins=[PluginHistorial(historial, agente="domi", app="domi")],
        app="domi",
    )
    [*_, fin] = [e async for e in conv.conversar("hola", usuario="u1", estado={"uid": "u1"})]
    assert fin.trace_id and len(fin.trace_id) == 32
    [_, respuesta] = await historial.mensajes("u1", fin.sesion_id)
    assert respuesta["trace_id"] == fin.trace_id
