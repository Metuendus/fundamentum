"""Piezas de ADK comunes a las apps: modelos, llamadas de una vuelta, conversación en flujo, sesiones e historial
persistentes, trazas, contexto largo, medición, guardrails y resultados."""

from fundamentum_adk.analitica import analitica
from fundamentum_adk.contexto import contexto
from fundamentum_adk.conversacion import (
    Conversacion,
    EventoConversacion,
    Fin,
    LlamadaHerramienta,
    RespuestaHerramienta,
    SesionAjena,
    Trozo,
)
from fundamentum_adk.guardrails import PluginAlcance, PluginPresupuesto, como_dato
from fundamentum_adk.historial import Fila, Historial, Mensaje, PluginHistorial
from fundamentum_adk.llamada import Llamada, SalidaVacia, agente_unico, llamar, llamar_sync
from fundamentum_adk.medicion import TIPO_RESULTADO, emitir_resultado, emitir_stdout
from fundamentum_adk.modelos import ESPERA_MS, REINTENTOS, modelo_adk
from fundamentum_adk.privacidad import FiltroDatosPersonales, instalar_filtro, redactar
from fundamentum_adk.sesiones import SesionesFirestore
from fundamentum_adk.trazas import (
    activar_trazas,
    contexto_entrante,
    enlace_traza,
    trace_id_actual,
    vaciar,
)

__all__ = [
    "ESPERA_MS",
    "REINTENTOS",
    "TIPO_RESULTADO",
    "Conversacion",
    "EventoConversacion",
    "Fila",
    "FiltroDatosPersonales",
    "Fin",
    "Historial",
    "Llamada",
    "LlamadaHerramienta",
    "Mensaje",
    "PluginAlcance",
    "PluginHistorial",
    "PluginPresupuesto",
    "RespuestaHerramienta",
    "SalidaVacia",
    "SesionAjena",
    "SesionesFirestore",
    "Trozo",
    "activar_trazas",
    "agente_unico",
    "analitica",
    "como_dato",
    "contexto",
    "contexto_entrante",
    "emitir_resultado",
    "emitir_stdout",
    "enlace_traza",
    "instalar_filtro",
    "llamar",
    "llamar_sync",
    "modelo_adk",
    "redactar",
    "trace_id_actual",
    "vaciar",
]
