"""Portero de Firebase Auth: funciones bloqueantes `beforeUserCreated` y `beforeUserSignedIn`.

Falla cerrado: si la lista no se puede leer, nadie entra (`acceso_no_disponible`). El mensaje del
rechazo es el `Motivo`, que la app traduce a su pantalla de beta privada.

Quitar a alguien de la lista no cierra su sesión abierta: `beforeUserSignedIn` no corre al renovar
el token. Quien lo quita debe revocar también sus refresh tokens en el proyecto de la app.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from fundamentum_acceso.decision import Motivo, Veredicto, decidir
from fundamentum_acceso.lector import LectorAcceso

log = logging.getLogger(__name__)


def evaluar(
    app: str,
    lector: LectorAcceso,
    *,
    correo: str | None,
    verificado: bool,
    proveedor: str,
    ahora: datetime | None = None,
) -> Veredicto:
    try:
        modo = lector.modo(app)
        pase = lector.pase(correo) if correo else None
    except Exception:
        log.exception("No se pudo leer la lista de acceso de %s", app)
        return Veredicto.no(Motivo.ACCESO_NO_DISPONIBLE)
    return decidir(
        app=app,
        correo=correo,
        verificado=verificado,
        proveedor=proveedor,
        modo=modo,
        pase=pase,
        ahora=ahora or datetime.now(UTC),
    )


def datos_del_evento(evento: Any) -> dict[str, Any]:
    """Correo, verificación y proveedor de un `AuthBlockingEvent` de firebase-functions."""
    usuario = evento.data
    info = getattr(evento, "additional_user_info", None)
    proveedor = getattr(info, "provider_id", None) or ""
    if not proveedor and getattr(usuario, "provider_data", None):
        proveedor = usuario.provider_data[0].provider_id
    return {
        "correo": getattr(usuario, "email", None),
        "verificado": bool(getattr(usuario, "email_verified", False)),
        "proveedor": proveedor,
    }


def crear_portero(app: str, fabrica: Callable[[], LectorAcceso]) -> Callable[[Any], None]:
    """Devuelve el manejador para `identity_fn.before_user_created` y `before_user_signed_in`.

    `fabrica` crea el lector en la primera llamada y no al importar, porque el despliegue de Cloud
    Functions importa el módulo sin credenciales. En la nube: `LectorFirestore.central`.
    """
    from firebase_functions import https_fn

    lector: list[LectorAcceso] = []

    def manejador(evento: Any) -> None:
        if not lector:
            lector.append(fabrica())
        veredicto = evaluar(app, lector[0], **datos_del_evento(evento))
        if not veredicto.ok:
            assert veredicto.motivo is not None
            log.info("Acceso rechazado en %s: %s", app, veredicto.motivo.value)
            raise https_fn.HttpsError(
                code=https_fn.FunctionsErrorCode.PERMISSION_DENIED,
                message=veredicto.motivo.value,
            )

    return manejador
