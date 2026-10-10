"""Despachador: valida, deduplica y aplica presupuestos antes de invocar un pipeline.

El enrutamiento por `tipo` lo hacen los filtros de suscripción de Pub/Sub; aquí solo se decide si
el evento se procesa. Sin LLM en este camino. Cada app declara qué tipos consumen presupuesto:

- `consumen_presupuesto`: eventos de usuario que llaman a un modelo; se cortan al agotar el
  presupuesto diario de ese usuario.
- `consumen_global`: eventos de sistema (sin uid) que llaman a un modelo; se cortan con el tope
  global diario. Un evento con uid que esté aquí también se corta con el tope global.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Generic, Literal, Protocol, TypeVar, runtime_checkable

from fundamentum_eventos.esquemas import EventoBusBase

E = TypeVar("E", bound=EventoBusBase)

Decision = Literal["procesar", "duplicado", "presupuesto_agotado"]


class Registro(Protocol):
    """Lo que el Despachador necesita del almacén. En pruebas, un falso en memoria."""

    def ya_procesado(self, evento_id: str, componente: str) -> bool: ...
    def gasto_hoy(self, uid: str) -> float: ...
    def presupuesto(self, uid: str) -> float: ...


@runtime_checkable
class RegistroGlobal(Protocol):
    def gasto_global_hoy(self) -> float: ...
    def presupuesto_global(self) -> float: ...


@dataclass(frozen=True)
class Resultado(Generic[E]):
    decision: Decision
    evento: E


class Despachador(Generic[E]):
    def __init__(
        self,
        modelo: type[E],
        consumen_presupuesto: Iterable[str],
        consumen_global: Iterable[str] = (),
    ) -> None:
        self.modelo = modelo
        self.consumen_presupuesto = frozenset(consumen_presupuesto)
        self.consumen_global = frozenset(consumen_global)

    def decodificar_push(self, cuerpo: dict) -> E:
        """El cuerpo de un push de Pub/Sub → evento validado. El atributo `tipo` debe coincidir."""
        mensaje = cuerpo["message"]
        evento = self.modelo.model_validate(json.loads(base64.b64decode(mensaje["data"])))
        atributo = mensaje.get("attributes", {}).get("tipo")
        if atributo is not None and atributo != evento.tipo:
            raise ValueError(
                f"atributo tipo={atributo!r} no coincide con el cuerpo {evento.tipo!r}"
            )
        return evento

    def decidir(self, evento: E, componente: str, registro: Registro) -> Resultado[E]:
        if registro.ya_procesado(evento.evento_id, componente):
            return Resultado("duplicado", evento)
        if (
            evento.tipo in self.consumen_presupuesto
            and evento.uid is not None
            and registro.gasto_hoy(evento.uid) >= registro.presupuesto(evento.uid)
        ):
            return Resultado("presupuesto_agotado", evento)
        if evento.tipo in self.consumen_global:
            if not isinstance(registro, RegistroGlobal):
                raise TypeError("Hay tipos con tope global y el registro no lo implementa")
            if registro.gasto_global_hoy() >= registro.presupuesto_global():
                return Resultado("presupuesto_agotado", evento)
        return Resultado("procesar", evento)
