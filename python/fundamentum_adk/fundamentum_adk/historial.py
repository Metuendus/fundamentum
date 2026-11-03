"""Historial visible: lo que la persona ve de sus conversaciones, en cualquier sesión o dispositivo.

Es distinto de la sesión de ADK. La sesión guarda todo lo que el agente necesita (llamadas a
herramientas, estado con la identidad, texto de los especialistas) y solo la lee el servidor. El
historial guarda lo que se le mostró a la persona: su mensaje, la respuesta final, las filas de
trabajo y lo que la respuesta enlazó (tarjetas, propuestas). Lo escribe solo el servidor y la persona
lo lee directo de Firestore con las reglas de `plantillas/historial/firestore.rules`.

Estructura (la raíz se configura, por omisión `historial`):

    historial/{uid}/conversaciones/{id}             título, app, recurso, sesión de ADK, último
    historial/{uid}/conversaciones/{id}/mensajes/*  un documento por mensaje, en orden por `creado`

`PluginHistorial` lo escribe solo, desde dentro del `Runner` (sirve igual en Agent Runtime que en
`Conversacion`): un mensaje de la persona al empezar el turno y uno del agente al terminar. El id de
la conversación es el de la sesión de ADK. Un error al escribir se registra y la conversación sigue.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.plugins.base_plugin import BasePlugin
from google.genai import types

from fundamentum_adk.trazas import trace_id_actual

log = logging.getLogger("fundamentum.historial")

MAX_TITULO = 80
MAX_ULTIMO = 160

Rol = Literal["persona", "agente"]
Estado = Literal["completo", "sin_respuesta", "error"]


@dataclass
class Fila:
    """Una fila de trabajo: qué herramienta o especialista corrió. La app la traduce a su texto."""

    herramienta: str
    estado: Literal["hecho", "error"] = "hecho"


@dataclass
class Mensaje:
    rol: Rol
    texto: str
    creado: float = field(default_factory=time.time)
    filas: list[Fila] = field(default_factory=list)
    # Lo que la respuesta enlazó, en la forma que la app decida: {"tipo": "propuesta", "id": ...}.
    enlaces: list[dict[str, Any]] = field(default_factory=list)
    estado: Estado = "completo"
    trace_id: str | None = None

    def a_firestore(self) -> dict[str, Any]:
        datos = asdict(self)
        return {k: v for k, v in datos.items() if v is not None}


def _texto(contenido: types.Content | None) -> str:
    if contenido is None or not contenido.parts:
        return ""
    return "".join(p.text for p in contenido.parts if p.text and not p.thought)


def _corto(texto: str, maximo: int) -> str:
    texto = " ".join(texto.split())
    return texto if len(texto) <= maximo else texto[: maximo - 1].rstrip() + "…"


class Historial:
    """Lee y escribe el historial visible (async). Uno por proceso.

    `retencion_dias` pone `vence` (renovado en cada mensaje) para la política TTL de Firestore;
    `None` no pone vencimiento.
    """

    def __init__(
        self,
        cliente: Any = None,
        *,
        proyecto: str | None = None,
        raiz: str = "historial",
        retencion_dias: int | None = 365,
    ) -> None:
        self._cliente = cliente
        self.proyecto = proyecto
        self.raiz = raiz
        self.retencion_dias = retencion_dias

    def __getstate__(self) -> dict[str, Any]:
        # Agent Runtime serializa el App con cloudpickle: el cliente se vuelve a crear allá.
        return {**self.__dict__, "_cliente": None}

    @property
    def db(self) -> Any:
        if self._cliente is None:
            from google.cloud import firestore  # extra firestore

            self._cliente = firestore.AsyncClient(project=self.proyecto)
        return self._cliente

    def _vence(self) -> datetime | None:
        if self.retencion_dias is None:
            return None
        return datetime.now(UTC) + timedelta(days=self.retencion_dias)

    def conversacion(self, uid: str, conversacion_id: str) -> Any:
        return (
            self.db.collection(self.raiz)
            .document(uid)
            .collection("conversaciones")
            .document(conversacion_id)
        )

    async def agregar(
        self,
        uid: str,
        conversacion_id: str,
        mensaje: Mensaje,
        *,
        app: str,
        recurso: dict[str, str] | None = None,
        sesion_id: str | None = None,
    ) -> None:
        """Agrega un mensaje y abre la conversación si no existía (con el primer texto de título)."""
        ref = self.conversacion(uid, conversacion_id)
        vence = self._vence()
        resumen: dict[str, Any] = {
            "app": app,
            "actualizada": mensaje.creado,
            "ultimo": _corto(mensaje.texto, MAX_ULTIMO),
            "vence": vence,
        }
        if not (await ref.get()).exists:
            resumen |= {
                "titulo": _corto(mensaje.texto, MAX_TITULO) or "Conversación",
                "creada": mensaje.creado,
                "sesion_id": sesion_id or conversacion_id,
                "recurso": recurso,
            }
        lote = self.db.batch()
        lote.set(ref, resumen, merge=True)
        lote.set(
            ref.collection("mensajes").document(f"{mensaje.creado:018.6f}-{mensaje.rol}"),
            {**mensaje.a_firestore(), "vence": vence},
        )
        await lote.commit()

    async def listar(
        self, uid: str, *, app: str | None = None, limite: int = 20
    ) -> list[dict[str, Any]]:
        """Conversaciones recientes, la más nueva primero (para servidores; la web lee directo)."""
        consulta = (
            self.db.collection(self.raiz)
            .document(uid)
            .collection("conversaciones")
            .order_by("actualizada", direction="DESCENDING")
        )
        if app is None:
            consulta = consulta.limit(limite)
        salida = []
        async for doc in consulta.stream():
            datos = doc.to_dict()
            if app is None or datos.get("app") == app:
                salida.append({"id": doc.id, **datos})
            if len(salida) >= limite:
                break
        return salida

    async def mensajes(self, uid: str, conversacion_id: str) -> list[dict[str, Any]]:
        consulta = self.conversacion(uid, conversacion_id).collection("mensajes").order_by("creado")
        return [d.to_dict() async for d in consulta.stream()]

    async def borrar(self, uid: str, conversacion_id: str) -> None:
        """Borra una conversación y sus mensajes. La sesión de ADK la borra la app aparte."""
        await self.db.recursive_delete(self.conversacion(uid, conversacion_id))

    async def borrar_usuario(self, uid: str) -> None:
        """Todo el historial de la persona (borrado de cuenta)."""
        await self.db.recursive_delete(self.db.collection(self.raiz).document(uid))


Enlazar = Callable[[str, dict[str, Any]], list[dict[str, Any]]]
TextoPersona = Callable[[types.Content, dict[str, Any]], str]


@dataclass
class _Turno:
    filas: list[Fila] = field(default_factory=list)
    enlaces: list[dict[str, Any]] = field(default_factory=list)
    texto: str = ""
    error: bool = False
    trace_id: str | None = None


class PluginHistorial(BasePlugin):
    """Escribe el historial visible de cada turno del agente raíz.

    - `agente`: nombre del agente raíz. Los especialistas que corren como `AgentTool` heredan los
      plugins; sus corridas no se registran como conversación.
    - `uid` / `recursos`: claves del estado de la sesión con la identidad y los recursos
      (`{"trip_id": "viaje"}` guarda `recurso={"tipo": "viaje", "id": ...}`).
    - `enlazar(herramienta, respuesta)`: lo que una respuesta de herramienta enlaza para la persona
      (tarjetas, propuestas). Por omisión, nada.
    - `texto_persona(mensaje, estado)`: el texto visible del mensaje de la persona, si la app le
      agrega contexto que no debe aparecer. Por omisión, el texto tal cual.
    """

    def __init__(
        self,
        historial: Historial,
        *,
        agente: str,
        app: str,
        uid: str = "uid",
        recursos: dict[str, str] | None = None,
        enlazar: Enlazar | None = None,
        texto_persona: TextoPersona | None = None,
    ) -> None:
        super().__init__(name="fundamentum_historial")
        self.historial = historial
        self.agente = agente
        self.app = app
        self.clave_uid = uid
        self.recursos = recursos or {}
        self.enlazar = enlazar
        self.texto_persona = texto_persona
        self._turnos: dict[str, _Turno] = {}

    def __getstate__(self) -> dict[str, Any]:
        return {**self.__dict__, "_turnos": {}}

    def _es_raiz(self, ctx: InvocationContext) -> bool:
        return ctx.agent.name == self.agente and bool(ctx.session.state.get(self.clave_uid))

    def _recurso(self, estado: dict[str, Any]) -> dict[str, str] | None:
        for clave, tipo in self.recursos.items():
            if estado.get(clave):
                return {"tipo": tipo, "id": str(estado[clave])}
        return None

    async def _escribir(self, ctx: InvocationContext, mensaje: Mensaje) -> None:
        estado = ctx.session.state
        try:
            await self.historial.agregar(
                str(estado[self.clave_uid]),
                ctx.session.id,
                mensaje,
                app=self.app,
                recurso=self._recurso(estado),
                sesion_id=ctx.session.id,
            )
        except Exception:  # el historial nunca rompe una conversación
            log.exception("historial: no se pudo escribir", extra={"app": self.app})

    async def on_user_message_callback(
        self, *, invocation_context: InvocationContext, user_message: types.Content
    ) -> types.Content | None:
        if not self._es_raiz(invocation_context):
            return None
        self._turnos[invocation_context.invocation_id] = _Turno(trace_id=trace_id_actual())
        estado = dict(invocation_context.session.state)
        texto = (
            self.texto_persona(user_message, estado) if self.texto_persona else _texto(user_message)
        )
        if texto.strip():
            await self._escribir(invocation_context, Mensaje(rol="persona", texto=texto.strip()))
        return None

    async def on_event_callback(
        self, *, invocation_context: InvocationContext, event: Event
    ) -> Event | None:
        turno = self._turnos.get(invocation_context.invocation_id)
        if turno is None or event.partial:
            return None
        turno.trace_id = turno.trace_id or trace_id_actual()
        for respuesta in event.get_function_responses():
            nombre = respuesta.name or ""
            datos = dict(respuesta.response or {})
            turno.filas.append(Fila(nombre, "error" if "error" in datos else "hecho"))
            if self.enlazar:
                try:
                    turno.enlaces.extend(self.enlazar(nombre, datos))
                except Exception:
                    log.exception("historial: enlazar falló", extra={"herramienta": nombre})
        if event.error_code:
            turno.error = True
        if event.is_final_response() and (texto := _texto(event.content)):
            turno.texto = texto
        return None

    async def after_run_callback(self, *, invocation_context: InvocationContext) -> None:
        turno = self._turnos.pop(invocation_context.invocation_id, None)
        if turno is None:
            return
        turno.trace_id = turno.trace_id or trace_id_actual()
        estado: Estado = (
            "error"
            if turno.error and not turno.texto
            else "completo"
            if turno.texto
            else "sin_respuesta"
        )
        await self._escribir(
            invocation_context,
            Mensaje(
                rol="agente",
                texto=turno.texto,
                filas=turno.filas,
                enlaces=turno.enlaces,
                estado=estado,
                trace_id=turno.trace_id,
            ),
        )
