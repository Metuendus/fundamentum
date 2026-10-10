"""Esquemas base de eventos y propuestas. Cada app los extiende en su `packages/schemas`.

Solo entran los campos que las apps comparten con el mismo nombre y significado. Lo propio de cada
dominio (tipos de evento, origen de una propuesta, contenido, cómo se llama la fecha) lo declara la
subclase de la app; en Pydantic una subclase puede estrechar un campo (`tipo: str` → `Literal[...]`).
El exportador de TS de cada app resuelve la herencia, así que el tipo generado trae los campos base.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Regla 2 de las tres apps, "proponer, no imponer".
ClasePropuesta = Literal["auto", "confirmar", "revisar"]
EstadoPropuesta = Literal["pendiente", "aprobada", "editada", "descartada", "expirada", "obsoleta"]


class Modelo(BaseModel):
    """Base de todos los modelos: un campo desconocido es error."""

    model_config = ConfigDict(extra="forbid")


class EventoBusBase(Modelo):
    """Mensaje del topic `eventos`. `tipo` va también como atributo para los filtros de Pub/Sub."""

    evento_id: str
    tipo: str
    uid: str | None = Field(default=None, description="None en eventos de sistema (sin usuario)")
    creado_en: datetime


class UsoModelo(Modelo):
    """Campos de una llamada a un modelo. Toda llamada a un modelo registra un evento con ellos."""

    modelo: str | None = None
    tokens_entrada: int | None = None
    tokens_salida: int | None = None
    costo_usd: float | None = None

    @staticmethod
    def de_llamada(llamada: Any) -> dict[str, Any]:
        """Los campos desde una `fundamentum_adk.Llamada`; el costo, nulo si el modelo no tiene
        precio (nunca 0)."""
        uso = llamada.uso
        try:
            costo: float | None = round(llamada.costo_usd(), 8)
        except KeyError:
            costo = None
        return {
            "modelo": llamada.modelo,
            "tokens_entrada": uso.entrada,
            "tokens_salida": uso.salida + uso.pensamiento,
            "costo_usd": costo,
        }


class EventoBase(UsoModelo):
    """Bitácora: una corrida de un componente, con su uso de modelo si llamó a uno."""

    tipo: str
    componente: str | None = None
    error: str | None = None


class PropuestaBase(Modelo):
    """Todo entregable de un pipeline: se acepta, se edita o se rechaza; nunca se impone."""

    tipo: str
    clase: ClasePropuesta
    origen: str
    explicacion: str
    estado: EstadoPropuesta = "pendiente"
    creada_en: datetime
    expira_en: datetime | None = None
    resuelta_en: datetime | None = None
