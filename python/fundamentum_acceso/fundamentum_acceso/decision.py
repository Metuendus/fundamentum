"""¿Puede esta cuenta entrar a esta app? Código determinista, sin red."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from fundamentum_acceso.modelos import Modo, Pase

# Con correo y contraseña la cuenta nace sin verificar y la app exige verificarla antes de usarla.
# Cualquier otro proveedor (Google) debe traer el correo verificado.
PROVEEDOR_CONTRASENA = "password"


class Motivo(StrEnum):
    SIN_CORREO = "sin_correo"
    CORREO_NO_VERIFICADO = "correo_no_verificado"
    BETA_PRIVADA = "beta_privada"
    PASE_VENCIDO = "pase_vencido"
    ACCESO_NO_DISPONIBLE = "acceso_no_disponible"


class Veredicto(BaseModel):
    ok: bool
    motivo: Motivo | None = None

    @classmethod
    def pasa(cls) -> Veredicto:
        return cls(ok=True)

    @classmethod
    def no(cls, motivo: Motivo) -> Veredicto:
        return cls(ok=False, motivo=motivo)


def decidir(
    *,
    app: str,
    correo: str | None,
    verificado: bool,
    proveedor: str,
    modo: Modo,
    pase: Pase | None,
    ahora: datetime,
) -> Veredicto:
    if not correo:
        return Veredicto.no(Motivo.SIN_CORREO)
    if not verificado and proveedor != PROVEEDOR_CONTRASENA:
        return Veredicto.no(Motivo.CORREO_NO_VERIFICADO)
    if modo == Modo.ABIERTA:
        return Veredicto.pasa()
    permiso = pase.apps.get(app) if pase else None
    if permiso is None:
        return Veredicto.no(Motivo.BETA_PRIVADA)
    if permiso.vence is not None and permiso.vence <= ahora:
        return Veredicto.no(Motivo.PASE_VENCIDO)
    return Veredicto.pasa()
