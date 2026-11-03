"""Historial visible: las conversaciones de una persona, leídas de las sesiones de ADK.

No hay una segunda copia: la fuente es el servicio de sesiones (Agent Platform Sessions en
producción). Dos piezas:

- `PluginResumen` deja en cada turno lo que una lista necesita sin leer todos los eventos: en el
  estado de la sesión, `historial_titulo` (primer mensaje) y `historial_ultimo` (última respuesta);
  en la respuesta final, `custom_metadata.trace_id` para ir de un mensaje a su traza.
- `Historial` lista las conversaciones de una persona y traduce los eventos de una sesión a
  mensajes para la pantalla: su texto, la respuesta final, las filas de trabajo y lo que la
  respuesta enlazó. Lo usa el servidor de la app; la web lo pide por su API.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.sessions import BaseSessionService
from google.adk.sessions.base_session_service import GetSessionConfig
from google.genai import types

from fundamentum_adk.trazas import trace_id_actual

TITULO = "historial_titulo"
ULTIMO = "historial_ultimo"
MAX_TITULO = 80
MAX_ULTIMO = 160

Enlazar = Callable[[str, dict[str, Any]], list[dict[str, Any]]]
TextoPersona = Callable[[str], str]


def _texto(contenido: types.Content | None) -> str:
    if contenido is None or not contenido.parts:
        return ""
    return "".join(p.text for p in contenido.parts if p.text and not p.thought)


def corto(texto: str, maximo: int) -> str:
    texto = " ".join(texto.split())
    return texto if len(texto) <= maximo else texto[: maximo - 1].rstrip() + "…"


class PluginResumen(BasePlugin):
    """Marca cada turno del agente raíz `agente` (los `AgentTool` heredan el plugin y se ignoran).

    `texto_persona` limpia el mensaje de la persona si la app le antepone contexto.
    """

    def __init__(self, agente: str, texto_persona: TextoPersona | None = None) -> None:
        super().__init__(name="fundamentum_resumen")
        self.agente = agente
        self.texto_persona = texto_persona or (lambda t: t)
        self._preguntas: dict[str, str] = {}

    def __getstate__(self) -> dict[str, Any]:
        # Agent Runtime serializa el App con cloudpickle.
        return {**self.__dict__, "_preguntas": {}}

    async def on_user_message_callback(
        self, *, invocation_context: InvocationContext, user_message: types.Content
    ) -> types.Content | None:
        if invocation_context.agent.name == self.agente:
            texto = self.texto_persona(_texto(user_message)).strip()
            self._preguntas[invocation_context.invocation_id] = texto
        return None

    async def on_event_callback(
        self, *, invocation_context: InvocationContext, event: Event
    ) -> Event | None:
        pregunta = self._preguntas.get(invocation_context.invocation_id)
        if pregunta is None or event.partial or event.author != self.agente:
            return None
        texto = _texto(event.content)
        if not (event.is_final_response() and texto):
            return None
        self._preguntas.pop(invocation_context.invocation_id, None)
        delta = {ULTIMO: corto(texto, MAX_ULTIMO)}
        if not invocation_context.session.state.get(TITULO):
            delta[TITULO] = corto(pregunta, MAX_TITULO) or "Conversación"
        event.actions.state_delta.update(delta)
        if traza := trace_id_actual():
            event.custom_metadata = {**(event.custom_metadata or {}), "trace_id": traza}
        return event

    async def after_run_callback(self, *, invocation_context: InvocationContext) -> None:
        self._preguntas.pop(invocation_context.invocation_id, None)


@dataclass
class Fila:
    """Una fila de trabajo: qué herramienta o especialista corrió. La app la traduce a su texto."""

    herramienta: str
    estado: Literal["hecho", "error"] = "hecho"


@dataclass
class Mensaje:
    rol: Literal["persona", "agente"]
    texto: str
    creado: float
    filas: list[Fila] = field(default_factory=list)
    enlaces: list[dict[str, Any]] = field(default_factory=list)
    estado: Literal["completo", "sin_respuesta"] = "completo"
    trace_id: str | None = None


@dataclass
class ResumenConversacion:
    id: str
    titulo: str
    ultimo: str
    actualizada: float
    estado: dict[str, Any]


class Historial:
    """Lee el historial visible de una app desde su servicio de sesiones.

    - `agente`: nombre del agente raíz (sus respuestas son las que ve la persona).
    - `enlazar(herramienta, respuesta)`: lo que una respuesta de herramienta enlaza (tarjetas,
      propuestas), para abrirlo desde el historial.
    - `texto_persona`: el mismo de `PluginResumen`.
    """

    def __init__(
        self,
        sesiones: BaseSessionService,
        *,
        app: str,
        agente: str,
        enlazar: Enlazar | None = None,
        texto_persona: TextoPersona | None = None,
    ) -> None:
        self.sesiones = sesiones
        self.app = app
        self.agente = agente
        self.enlazar = enlazar
        self.texto_persona = texto_persona or (lambda t: t)

    async def listar(
        self, uid: str, *, filtro: dict[str, Any] | None = None, limite: int = 20
    ) -> list[ResumenConversacion]:
        """Conversaciones de la persona, la más reciente primero. `filtro` compara claves del estado
        (p. ej. `{"trip_id": "t1"}` para las de un viaje). Las sesiones sin turnos no se listan."""
        respuesta = await self.sesiones.list_sessions(app_name=self.app, user_id=uid)
        salida = []
        for s in reversed(respuesta.sessions):  # ADK las da de la más vieja a la más nueva
            if not s.state.get(TITULO) or s.user_id != uid:
                continue
            if filtro and any(s.state.get(k) != v for k, v in filtro.items()):
                continue
            salida.append(
                ResumenConversacion(
                    id=s.id,
                    titulo=s.state[TITULO],
                    ultimo=s.state.get(ULTIMO, ""),
                    actualizada=s.last_update_time,
                    estado=dict(s.state),
                )
            )
            if len(salida) >= limite:
                break
        return salida

    async def mensajes(
        self, uid: str, sesion_id: str, *, ultimos_eventos: int | None = None
    ) -> list[Mensaje]:
        """Los mensajes visibles de una conversación, en orden. `[]` si no existe."""
        config = GetSessionConfig(num_recent_events=ultimos_eventos) if ultimos_eventos else None
        sesion = await self.sesiones.get_session(
            app_name=self.app, user_id=uid, session_id=sesion_id, config=config
        )
        return self.traducir(sesion.events) if sesion else []

    def traducir(self, eventos: list[Event]) -> list[Mensaje]:
        mensajes: list[Mensaje] = []
        actual: Mensaje | None = None
        for e in eventos:
            if e.partial or (e.actions and e.actions.compaction):
                continue
            if e.author == "user":
                texto = self.texto_persona(_texto(e.content)).strip()
                if not texto:
                    continue  # respuestas de herramientas u otros eventos sin texto de la persona
                if actual and not actual.texto:
                    actual.estado = "sin_respuesta"
                actual = None
                mensajes.append(Mensaje("persona", texto, e.timestamp))
                continue
            if e.author != self.agente:
                continue
            if actual is None:
                actual = Mensaje("agente", "", e.timestamp)
                mensajes.append(actual)
            for r in e.get_function_responses():
                datos = dict(r.response or {})
                nombre = r.name or ""
                actual.filas.append(Fila(nombre, "error" if "error" in datos else "hecho"))
                if self.enlazar:
                    actual.enlaces.extend(self.enlazar(nombre, datos))
            texto = _texto(e.content)
            if e.is_final_response() and texto:
                actual.texto = texto
                actual.creado = e.timestamp
                actual.trace_id = (e.custom_metadata or {}).get("trace_id")
        if actual and not actual.texto:
            actual.estado = "sin_respuesta"
        return mensajes

    async def borrar(self, uid: str, sesion_id: str) -> None:
        """Borra la conversación (la sesión con todos sus eventos)."""
        sesion = await self.sesiones.get_session(
            app_name=self.app,
            user_id=uid,
            session_id=sesion_id,
            config=GetSessionConfig(num_recent_events=0),
        )
        if sesion is not None:
            await self.sesiones.delete_session(app_name=self.app, user_id=uid, session_id=sesion_id)

    async def borrar_usuario(self, uid: str) -> int:
        """Todas las conversaciones de la persona (borrado de cuenta). Devuelve cuántas borró."""
        respuesta = await self.sesiones.list_sessions(app_name=self.app, user_id=uid)
        for s in respuesta.sessions:
            await self.sesiones.delete_session(app_name=self.app, user_id=uid, session_id=s.id)
        return len(respuesta.sessions)
