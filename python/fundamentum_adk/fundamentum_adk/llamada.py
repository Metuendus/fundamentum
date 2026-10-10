"""Llamadas de una sola vuelta por ADK: extraer, clasificar o redactar con salida por esquema.

Es la forma estándar de llamar a un modelo fuera de una conversación (pipelines de Cloud Run,
lectores dentro de una herramienta). Corre un `Runner` propio y comparte los plugins de la app sin
cerrarlos, como `AgentTool`, así que la llamada queda medida (`analitica`) y trazada. Devuelve el
uso de tokens para que la app lo cargue a su presupuesto.
"""

import asyncio
import time
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from fundamentum_modelos import Uso, costo_usd, normalizar
from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.models.base_llm import BaseLlm
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


class SalidaVacia(RuntimeError):
    """El modelo no devolvió texto."""


@dataclass(frozen=True)
class Llamada:
    texto: str
    modelo: str
    usos: list[Uso] = field(default_factory=list)  # uno por respuesta del modelo
    latencia_ms: int = 0

    @property
    def uso(self) -> Uso:
        return sum(self.usos, Uso())

    def costo_usd(self) -> float:
        """Costo por respuesta (el tramo de contexto largo se aplica a cada una). Un modelo sin
        precio lanza `KeyError`: nunca cuesta 0."""
        return sum(costo_usd(self.modelo, u) for u in self.usos)


def agente_unico(
    nombre: str,
    modelo: BaseLlm,
    esquema: Any = None,
    instruccion: str | None = None,
    temperatura: float | None = None,
    config: types.GenerateContentConfig | None = None,
) -> LlmAgent:
    """Un `LlmAgent` de una sola vuelta: sin herramientas que una inyección pueda llamar, sin
    historial (`include_contents="none"`) y, con `esquema`, salida JSON atada a él.

    `esquema` acepta lo que acepta ADK: un modelo de Pydantic, un `types.Schema` o un dict con el
    formato de Gemini (`{"type": "OBJECT", ...}`). La instrucción va como función para que ADK no
    interprete las llaves del texto como variables del estado.
    """
    config = config.model_copy() if config else types.GenerateContentConfig()
    if temperatura is not None:
        config.temperature = temperatura
    if esquema is not None:
        config.response_mime_type = "application/json"
        if isinstance(esquema, dict):
            esquema = types.Schema.model_validate(esquema)
    texto = instruccion or ""
    return LlmAgent(
        name=nombre,
        model=modelo,
        instruction=(lambda _contexto: texto) if instruccion else "",
        include_contents="none",
        output_schema=esquema,
        generate_content_config=config,
    )


async def llamar(
    agente: LlmAgent,
    partes: Sequence[types.Part | str],
    *,
    plugins: Sequence[BasePlugin] = (),
    usuario: str = "sistema",
    app: str = "fundamentum",
) -> Llamada:
    """Corre `agente` con `partes` como mensaje del usuario y devuelve su texto final y su uso.

    `usuario` es el uid al que se atribuye la llamada en la medición; `app` es el nombre del `App`
    de ADK (el de la app que llama, para que las trazas cuadren).
    """
    contenido = types.Content(
        role="user",
        parts=[types.Part.from_text(text=p) if isinstance(p, str) else p for p in partes],
    )
    runner = Runner(
        app=App(name=app, root_agent=agente, plugins=list(plugins)),
        session_service=InMemorySessionService(),
    )
    # Los plugins son de la app: el Runner de esta llamada no los cierra al terminar.
    runner.plugin_manager.set_skip_closing_plugins(True)
    sesion = await runner.session_service.create_session(app_name=app, user_id=usuario)
    texto, usos = "", []
    inicio = time.monotonic()
    async for evento in runner.run_async(
        user_id=usuario, session_id=sesion.id, new_message=contenido
    ):
        if evento.usage_metadata is not None and not evento.partial:
            usos.append(Uso.desde_metadata(evento.usage_metadata))
        if evento.is_final_response() and evento.content and evento.content.parts:
            texto = "".join(p.text for p in evento.content.parts if p.text and not p.thought)
    if not texto.strip():
        raise SalidaVacia(f"{agente.name}: el modelo no devolvió texto")
    modelo = agente.model if isinstance(agente.model, str) else agente.model.model
    return Llamada(
        texto=texto,
        modelo=normalizar(modelo),
        usos=usos,
        latencia_ms=round((time.monotonic() - inicio) * 1000),
    )


def llamar_sync(agente: LlmAgent, partes: Sequence[types.Part | str], **kwargs: Any) -> Llamada:
    """`llamar` para código síncrono (pipelines). Si ya hay un loop en este hilo, corre en otro."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(llamar(agente, partes, **kwargs))
    with ThreadPoolExecutor(max_workers=1) as hilo:
        return hilo.submit(asyncio.run, llamar(agente, partes, **kwargs)).result()
