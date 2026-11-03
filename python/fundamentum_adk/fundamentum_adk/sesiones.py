"""Sesiones de ADK en Firestore: el agente recuerda la conversación aunque Cloud Run escale a cero.

ADK trae sesiones en memoria, en SQL y en Agent Runtime. Las apps del chasis ya usan Firestore y no
quieren un Cloud SQL con costo fijo, así que esta es la implementación de `BaseSessionService` que
usa `Conversacion` fuera de Agent Runtime.

Estructura (la raíz se configura, por omisión `adk`):

    adk/{app}                                         estado de la app   (claves `app:`)
    adk/{app}/usuarios/{uid}                          estado del usuario (claves `user:`)
    adk/{app}/usuarios/{uid}/sesiones/{sid}           estado de la sesión, `actualizada`, `vence`
    adk/{app}/usuarios/{uid}/sesiones/{sid}/eventos/* un documento por evento, en orden por `ts`

Las sesiones viven bajo su usuario: un id de sesión ajeno abre una sesión propia con ese id, nunca
la de otra persona. Nadie fuera del servidor lee esta raíz (las reglas de Firestore la cierran).
`vence` es para la política TTL de Firestore (`infra/modulos/historial`). El estado `temp:` no se
guarda, como en ADK.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from google.adk.events.event import Event
from google.adk.sessions import BaseSessionService, Session
from google.adk.sessions.base_session_service import GetSessionConfig, ListSessionsResponse
from google.adk.sessions.state import State
from google.genai import types
from pydantic_core import to_jsonable_python

try:  # extra firestore; sin él solo falla al construir el servicio
    from google.cloud.firestore_v1.base_query import FieldFilter
except ImportError:  # pragma: no cover
    FieldFilter = None  # type: ignore[assignment,misc]

# Firestore guarda hasta 1 MiB por documento; un evento más grande pierde sus adjuntos en línea.
MAX_EVENTO_BYTES = 900_000
_ID = re.compile(r"^[^/]{1,700}$")


def _id(valor: str, que: str) -> str:
    valor = valor.strip()
    if not _ID.match(valor) or valor in {".", ".."} or valor.startswith("__"):
        raise ValueError(f"{que} no válido para Firestore: {valor!r}")
    return valor


def _separar(estado: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """(app, usuario, sesión) sin prefijos; las claves `temp:` se descartan."""
    app, usuario, sesion = {}, {}, {}
    for clave, valor in (estado or {}).items():
        if clave.startswith(State.APP_PREFIX):
            app[clave.removeprefix(State.APP_PREFIX)] = valor
        elif clave.startswith(State.USER_PREFIX):
            usuario[clave.removeprefix(State.USER_PREFIX)] = valor
        elif not clave.startswith(State.TEMP_PREFIX):
            sesion[clave] = valor
    return app, usuario, sesion


def _json(valor: dict[str, Any]) -> str:
    return json.dumps(to_jsonable_python(valor, fallback=str), ensure_ascii=False)


def _clave_evento(evento: Event) -> str:
    return f"{evento.timestamp:018.6f}-{evento.id}"


def serializar_evento(evento: Event) -> str:
    """El evento en JSON. Si pasa del tope de Firestore, los adjuntos en línea se cambian por una
    nota con su tipo: el agente sabe que hubo un archivo, aunque ya no lo vea."""
    texto = evento.model_dump_json(exclude_none=True)
    if len(texto.encode()) <= MAX_EVENTO_BYTES or evento.content is None:
        return texto
    copia = evento.model_copy(deep=True)
    partes = []
    for parte in copia.content.parts or []:
        if parte.inline_data is not None:
            tipo = parte.inline_data.mime_type or "archivo"
            parte = types.Part.from_text(text=f"[adjunto {tipo} omitido al guardar la sesión]")
        partes.append(parte)
    copia.content.parts = partes
    return copia.model_dump_json(exclude_none=True)


class SesionesFirestore(BaseSessionService):
    """`BaseSessionService` sobre Firestore (async). Uno por proceso, como el `Runner`.

    `retencion_dias` pone `vence` en sesiones y eventos (renovado en cada turno); `None` no pone
    vencimiento. La TTL la aplica Firestore solo si el proyecto tiene la política activa.
    """

    def __init__(
        self,
        cliente: Any = None,
        *,
        proyecto: str | None = None,
        raiz: str = "adk",
        retencion_dias: int | None = 365,
    ) -> None:
        if cliente is None:
            from google.cloud import firestore  # extra firestore

            cliente = firestore.AsyncClient(project=proyecto)
        self.db = cliente
        self.raiz = raiz
        self.retencion_dias = retencion_dias

    # Referencias

    def _app(self, app: str):
        return self.db.collection(self.raiz).document(_id(app, "app"))

    def _usuario(self, app: str, uid: str):
        return self._app(app).collection("usuarios").document(_id(uid, "usuario"))

    def _sesion(self, app: str, uid: str, sid: str):
        return self._usuario(app, uid).collection("sesiones").document(_id(sid, "sesión"))

    def _vence(self) -> datetime | None:
        if self.retencion_dias is None:
            return None
        return datetime.now(UTC) + timedelta(days=self.retencion_dias)

    async def _estado(self, ref) -> dict[str, Any]:
        doc = await ref.get()
        datos = doc.to_dict() if doc.exists else None
        return json.loads(datos.get("estado") or "{}") if datos else {}

    async def _mezclar(self, app: str, uid: str, sesion: Session) -> Session:
        for clave, valor in (await self._estado(self._app(app))).items():
            sesion.state[State.APP_PREFIX + clave] = valor
        for clave, valor in (await self._estado(self._usuario(app, uid))).items():
            sesion.state[State.USER_PREFIX + clave] = valor
        return sesion

    async def _sumar_estado(self, ref, delta: dict[str, Any]) -> None:
        if delta:
            actual = await self._estado(ref)
            await ref.set({"estado": _json({**actual, **delta})}, merge=True)

    # BaseSessionService

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> Session:
        from google.adk.errors.already_exists_error import AlreadyExistsError

        sid = _id(session_id, "sesión") if session_id else uuid.uuid4().hex
        ref = self._sesion(app_name, user_id, sid)
        if (await ref.get()).exists:
            raise AlreadyExistsError(f"La sesión {sid} ya existe.")
        app, usuario, propio = _separar(state or {})
        await self._sumar_estado(self._app(app_name), app)
        await self._sumar_estado(self._usuario(app_name, user_id), usuario)
        ahora = time.time()
        await ref.set(
            {
                "app": app_name,
                "uid": user_id,
                "id": sid,
                "estado": _json(propio),
                "actualizada": ahora,
                "vence": self._vence(),
            }
        )
        sesion = Session(
            app_name=app_name, user_id=user_id, id=sid, state=propio, last_update_time=ahora
        )
        return await self._mezclar(app_name, user_id, sesion)

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: GetSessionConfig | None = None,
    ) -> Session | None:
        ref = self._sesion(app_name, user_id, session_id)
        doc = await ref.get()
        if not doc.exists:
            return None
        datos = doc.to_dict()
        consulta = ref.collection("eventos")
        if config and config.after_timestamp is not None:
            consulta = consulta.where(filter=FieldFilter("ts", ">=", config.after_timestamp))
        recientes = config.num_recent_events if config else None
        if recientes == 0:
            eventos: list[Event] = []
        else:
            if recientes is not None:
                consulta = consulta.order_by("ts", direction="DESCENDING").limit(recientes)
            else:
                consulta = consulta.order_by("ts")
            eventos = [Event.model_validate_json(d.get("evento")) async for d in consulta.stream()]
            if recientes is not None:
                eventos.reverse()
        sesion = Session(
            app_name=app_name,
            user_id=user_id,
            id=datos["id"],
            state=json.loads(datos.get("estado") or "{}"),
            events=eventos,
            last_update_time=datos.get("actualizada", 0.0),
        )
        return await self._mezclar(app_name, user_id, sesion)

    async def list_sessions(
        self, *, app_name: str, user_id: str | None = None
    ) -> ListSessionsResponse:
        if user_id is not None:
            consulta = self._usuario(app_name, user_id).collection("sesiones")
        else:
            consulta = self.db.collection_group("sesiones").where(
                filter=FieldFilter("app", "==", app_name)
            )
        sesiones = []
        async for doc in consulta.stream():
            datos = doc.to_dict()
            if datos.get("app") != app_name:
                continue
            sesion = Session(
                app_name=app_name,
                user_id=datos["uid"],
                id=datos["id"],
                state=json.loads(datos.get("estado") or "{}"),
                last_update_time=datos.get("actualizada", 0.0),
            )
            sesiones.append(await self._mezclar(app_name, datos["uid"], sesion))
        sesiones.sort(key=lambda s: (s.last_update_time, s.user_id, s.id))
        return ListSessionsResponse(sessions=sesiones)

    async def delete_session(self, *, app_name: str, user_id: str, session_id: str) -> None:
        await self.db.recursive_delete(self._sesion(app_name, user_id, session_id))

    async def get_user_state(self, *, app_name: str, user_id: str) -> dict[str, Any]:
        return await self._estado(self._usuario(app_name, user_id))

    async def append_event(self, session: Session, event: Event) -> Event:
        from google.adk.errors.session_not_found_error import SessionNotFoundError

        if event.partial:
            return event
        delta = dict(event.actions.state_delta) if event.actions else {}
        event = await super().append_event(session=session, event=event)
        session.last_update_time = event.timestamp
        ref = self._sesion(session.app_name, session.user_id, session.id)
        if not (await ref.get()).exists:
            raise SessionNotFoundError(f"La sesión {session.id} no existe.")
        app, usuario, _ = _separar(delta)
        await self._sumar_estado(self._app(session.app_name), app)
        await self._sumar_estado(self._usuario(session.app_name, session.user_id), usuario)
        _, _, propio = _separar(session.state)
        vence = self._vence()
        lote = self.db.batch()
        lote.set(
            ref.collection("eventos").document(_clave_evento(event)),
            {"ts": event.timestamp, "evento": serializar_evento(event), "vence": vence},
        )
        lote.update(ref, {"estado": _json(propio), "actualizada": event.timestamp, "vence": vence})
        await lote.commit()
        return event
