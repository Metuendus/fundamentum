"""Conversación en flujo por ADK: un agente con herramientas, historial y respuesta en trozos.

Es la forma estándar de hablar con la persona desde un servicio propio (un endpoint SSE en Cloud
Run), cuando la app no corre en Agent Runtime. Comparte los plugins de la app sin cerrarlos, como
`llamar`, así que cada turno queda medido (`analitica`), trazado y con los guardrails puestos
(`PluginAlcance`, `PluginPresupuesto`).

La identidad (uid y recurso) la pone el servidor en el estado de la sesión con `estado`; nunca viene
del mensaje. Cada turno devuelve eventos tipados que la app traduce a su propio protocolo:
`Trozo` (texto), `LlamadaHerramienta`, `RespuestaHerramienta` y, al final, `Fin` con el texto
completo, el uso y el costo.
"""

import time
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Any

from fundamentum_modelos import Uso, costo_usd, normalizar
from google.adk.agents import LlmAgent
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.apps import App
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService, InMemorySessionService
from google.genai import types


class SesionAjena(PermissionError):
    """El servicio de sesiones rechazó el id porque ya es de otra persona."""


@dataclass(frozen=True)
class Trozo:
    texto: str


@dataclass(frozen=True)
class LlamadaHerramienta:
    nombre: str
    args: dict[str, Any]


@dataclass(frozen=True)
class RespuestaHerramienta:
    nombre: str
    respuesta: dict[str, Any]


@dataclass(frozen=True)
class Fin:
    texto: str
    modelo: str
    sesion_id: str
    usos: list[Uso] = field(default_factory=list)  # uno por respuesta del modelo
    latencia_ms: int = 0

    @property
    def uso(self) -> Uso:
        return sum(self.usos, Uso())

    def costo_usd(self) -> float:
        """Costo por respuesta del modelo. Un modelo sin precio lanza `KeyError`: nunca cuesta 0."""
        return sum(costo_usd(self.modelo, u) for u in self.usos)


EventoConversacion = Trozo | LlamadaHerramienta | RespuestaHerramienta | Fin


def _texto(contenido: types.Content | None) -> str:
    if contenido is None or not contenido.parts:
        return ""
    return "".join(p.text for p in contenido.parts if p.text and not p.thought)


class Conversacion:
    """Un agente conversacional con su `Runner`. Se crea una vez por proceso y atiende a todos.

    `sesiones` guarda el historial (por omisión en memoria, que basta para una instancia de Cloud
    Run; para varias, un servicio persistente de ADK). `en_flujo=False` pide la respuesta entera al
    modelo y la entrega como un solo `Trozo`.
    """

    def __init__(
        self,
        agente: LlmAgent,
        *,
        plugins: Sequence[BasePlugin] = (),
        app: str = "fundamentum",
        sesiones: BaseSessionService | None = None,
        en_flujo: bool = True,
    ) -> None:
        self.agente = agente
        self.app = app
        self.runner = Runner(
            app=App(name=app, root_agent=agente, plugins=list(plugins)),
            session_service=sesiones or InMemorySessionService(),
        )
        # Los plugins son de la app: este Runner no los cierra.
        self.runner.plugin_manager.set_skip_closing_plugins(True)
        self.config = RunConfig(
            streaming_mode=StreamingMode.SSE if en_flujo else StreamingMode.NONE
        )

    async def _sesion(self, usuario: str, sesion_id: str | None, estado: dict[str, Any]) -> str:
        servicio = self.runner.session_service
        if sesion_id:
            sesion = await servicio.get_session(
                app_name=self.app, user_id=usuario, session_id=sesion_id
            )
            if sesion is not None:
                return sesion.id
        try:
            sesion = await servicio.create_session(
                app_name=self.app, user_id=usuario, state=dict(estado), session_id=sesion_id
            )
        except Exception as e:  # el id ya existe con otro usuario
            raise SesionAjena(f"la sesión {sesion_id} no es de {usuario}") from e
        return sesion.id

    async def conversar(
        self,
        mensaje: str | Sequence[types.Part | str],
        *,
        usuario: str,
        sesion_id: str | None = None,
        estado: dict[str, Any] | None = None,
    ) -> AsyncIterator[EventoConversacion]:
        """Un turno: manda `mensaje` y entrega los eventos del agente hasta `Fin`.

        `estado` (p. ej. `{"uid": ..., "perfil_id": ...}`) lo fija el servidor: crea la sesión con
        él y, si ya existía, lo vuelve a escribir antes del turno, así que el modelo no puede
        cambiar la identidad entre turnos. Las sesiones son por usuario: con el id de otra persona
        no se ve su historial (se abre una sesión propia, o `SesionAjena` si el servicio de
        sesiones no admite el id repetido).
        """
        estado = estado or {}
        sesion = await self._sesion(usuario, sesion_id, estado)
        partes = [mensaje] if isinstance(mensaje, str) else list(mensaje)
        contenido = types.Content(
            role="user",
            parts=[types.Part.from_text(text=p) if isinstance(p, str) else p for p in partes],
        )
        final, usos, en_curso = "", [], False
        inicio = time.monotonic()
        async for evento in self.runner.run_async(
            user_id=usuario,
            session_id=sesion,
            new_message=contenido,
            state_delta=dict(estado) or None,
            run_config=self.config,
        ):
            texto = _texto(evento.content)
            if evento.partial:
                if texto:
                    en_curso = True
                    yield Trozo(texto)
                continue
            if evento.usage_metadata is not None:
                usos.append(Uso.desde_metadata(evento.usage_metadata))
            for llamada in evento.get_function_calls():
                yield LlamadaHerramienta(llamada.name or "", dict(llamada.args or {}))
            for respuesta in evento.get_function_responses():
                yield RespuestaHerramienta(respuesta.name or "", dict(respuesta.response or {}))
            # Sin trozos previos (modelo sin flujo o respuesta de un plugin), el texto va entero.
            if texto and not en_curso:
                yield Trozo(texto)
            en_curso = False
            if evento.is_final_response() and texto:
                final = texto
        modelo = (
            self.agente.model if isinstance(self.agente.model, str) else self.agente.model.model
        )
        yield Fin(
            texto=final,
            modelo=normalizar(modelo),
            sesion_id=sesion,
            usos=usos,
            latencia_ms=round((time.monotonic() - inicio) * 1000),
        )
