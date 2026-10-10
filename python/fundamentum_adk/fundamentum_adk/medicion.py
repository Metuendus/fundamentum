"""Resultados entregados: una línea JSON `resultado_entregado` en stdout.

Cloud Run y Agent Runtime la convierten en `jsonPayload` de Cloud Logging y el sink de
`infra/modulos/medicion` la copia a BigQuery. La medición de llamadas a modelos es nativa de ADK
(`analitica`).
"""

import json
import sys
from collections.abc import Callable
from typing import Any

TIPO_RESULTADO = "resultado_entregado"

Emisor = Callable[[dict[str, Any]], None]


def emitir_stdout(registro: dict[str, Any]) -> None:
    linea = {"severity": "INFO", "message": registro["tipo"], **registro}
    sys.stdout.write(json.dumps(linea, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def emitir_resultado(
    app: str,
    resultado_tipo: str,
    resultado_id: str,
    uid: str,
    usuario_interno: bool = False,
    emisor: Emisor = emitir_stdout,
) -> None:
    """Registra un resultado entregado (viaje planeado, aplicación preparada, visita agendada)."""
    emisor(
        {
            "tipo": TIPO_RESULTADO,
            "app": app,
            "resultado_tipo": resultado_tipo,
            "resultado_id": resultado_id,
            "uid": uid,
            "usuario_interno": usuario_interno,
        }
    )
