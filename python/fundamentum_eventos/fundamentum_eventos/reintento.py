"""Reintento de llamadas a servicios (Storage, APIs de datos) ante límites o errores pasajeros.

Las llamadas a modelos no lo usan: las reintenta ADK con `retry_options` (`fundamentum_adk`).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

log = logging.getLogger("fundamentum.reintento")
T = TypeVar("T")

ESPERAS = (3.0, 8.0, 15.0)
TRANSITORIOS = {408, 429, 500, 502, 503, 504}


def es_transitorio(error: Exception) -> bool:
    codigo = getattr(error, "code", None) or getattr(error, "status_code", None)
    return codigo in TRANSITORIOS


def con_reintentos(
    llamada: Callable[[], T],
    *,
    esperas: tuple[float, ...] = ESPERAS,
    dormir: Callable[[float], None] = time.sleep,
) -> T:
    """Llama y, si falla por cuota o por el servidor, espera y reintenta. Lo demás se propaga."""
    for espera in (*esperas, None):
        try:
            return llamada()
        except Exception as error:
            if espera is None or not es_transitorio(error):
                raise
            log.warning("transitorio %s; reintento en %s s", getattr(error, "code", "?"), espera)
            dormir(espera)
    raise RuntimeError("inalcanzable")
