"""Lista de acceso común a las apps.

Vive en un solo Firestore, fuera de las apps (proyecto `josecarloscorona-web`):

- `acceso/{correo}`: un `Pase` por persona, con un `Permiso` por app.
- `apps/{app}`: el `Modo` de cada app. Sin documento, la app está en beta.
- `solicitudes/{id}`: quien pidió acceso desde la pantalla de beta privada.

El correo va normalizado (minúsculas, sin espacios) y es el id del documento.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


def normalizar_correo(correo: str) -> str:
    return correo.strip().lower()


class Modo(StrEnum):
    BETA = "beta"  # solo entra quien tiene permiso para la app
    ABIERTA = "abierta"  # cualquiera crea su cuenta


class Origen(StrEnum):
    LISTA = "lista"  # lo agregó el administrador
    INVITACION = "invitacion"  # lo invitó alguien con acceso (p. ej. a un viaje de Iterum)
    SOLICITUD = "solicitud"  # pidió acceso y se aprobó


class Permiso(BaseModel):
    origen: Origen = Origen.LISTA
    alta: datetime
    vence: datetime | None = None
    nota: str = ""


class Pase(BaseModel):
    correo: str
    apps: dict[str, Permiso] = Field(default_factory=dict)


class EstadoSolicitud(StrEnum):
    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"


class Solicitud(BaseModel):
    correo: str
    app: str
    motivo: str = Field(default="", max_length=500)
    creada: datetime
    estado: EstadoSolicitud = EstadoSolicitud.PENDIENTE
