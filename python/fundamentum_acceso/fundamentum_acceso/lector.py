"""De dónde sale la lista: Firestore central en la nube, memoria en pruebas y emuladores."""

from __future__ import annotations

from typing import Any, Protocol

from fundamentum_acceso.modelos import Modo, Pase, normalizar_correo

PROYECTO_CENTRAL = "josecarloscorona-web"


class LectorAcceso(Protocol):
    def pase(self, correo: str) -> Pase | None: ...
    def modo(self, app: str) -> Modo: ...


class LectorMemoria:
    def __init__(self, pases: list[Pase] | None = None, modos: dict[str, Modo] | None = None):
        self._pases = {normalizar_correo(p.correo): p for p in pases or []}
        self._modos = modos or {}

    def pase(self, correo: str) -> Pase | None:
        return self._pases.get(normalizar_correo(correo))

    def modo(self, app: str) -> Modo:
        return self._modos.get(app, Modo.BETA)


class LectorFirestore:
    """Lee `acceso/{correo}` y `apps/{app}`. Un modo desconocido cuenta como beta."""

    def __init__(self, cliente: Any, *, acceso: str = "acceso", apps: str = "apps") -> None:
        self.db = cliente
        self._acceso = acceso
        self._apps = apps

    @classmethod
    def central(cls, proyecto: str = PROYECTO_CENTRAL) -> LectorFirestore:
        from google.cloud import firestore

        return cls(firestore.Client(project=proyecto))

    def pase(self, correo: str) -> Pase | None:
        correo = normalizar_correo(correo)
        datos = self.db.collection(self._acceso).document(correo).get().to_dict()
        return Pase.model_validate({**datos, "correo": correo}) if datos else None

    def modo(self, app: str) -> Modo:
        datos = self.db.collection(self._apps).document(app).get().to_dict() or {}
        try:
            return Modo(datos.get("modo", Modo.BETA))
        except ValueError:
            return Modo.BETA
