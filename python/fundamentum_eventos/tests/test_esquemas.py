"""Los esquemas base se extienden por app y la herencia llega al JSON Schema (tipos de TS)."""

from datetime import UTC, datetime
from typing import Literal

import pytest
from fundamentum_adk import Llamada
from fundamentum_eventos import EventoBase, PropuestaBase
from fundamentum_modelos import Uso
from pydantic import ValidationError
from pydantic.json_schema import models_json_schema

AHORA = datetime(2026, 10, 10, tzinfo=UTC)


class Propuesta(PropuestaBase):
    tipo: Literal["cv_adaptado"]
    origen: Literal["redaccion"]
    expira_en: datetime  # Vocatio la exige
    contenido: dict


class Evento(EventoBase):
    componente: Literal["scriba"]
    creado_en: datetime


def test_la_app_estrecha_y_agrega_campos():
    p = Propuesta(tipo="cv_adaptado", origen="redaccion", clase="revisar", explicacion="x",
                  creada_en=AHORA, expira_en=AHORA, contenido={})  # fmt: skip
    assert p.estado == "pendiente"
    with pytest.raises(ValidationError):
        Propuesta(tipo="otro", origen="redaccion", clase="revisar", explicacion="x",
                  creada_en=AHORA, expira_en=AHORA, contenido={})  # fmt: skip
    with pytest.raises(ValidationError):  # campos de más son error
        Propuesta(tipo="cv_adaptado", origen="redaccion", clase="revisar", explicacion="x",
                  creada_en=AHORA, expira_en=AHORA, contenido={}, extra=1)  # fmt: skip


def test_el_json_schema_trae_los_campos_base():
    _, esquema = models_json_schema([(Propuesta, "serialization"), (Evento, "serialization")])
    propuesta = esquema["$defs"]["Propuesta"]["properties"]
    assert {"clase", "estado", "explicacion", "creada_en", "contenido"} <= set(propuesta)
    evento = esquema["$defs"]["Evento"]["properties"]
    assert {"modelo", "tokens_entrada", "tokens_salida", "costo_usd", "creado_en"} <= set(evento)


def test_evento_desde_una_llamada():
    llamada = Llamada(
        texto="{}", modelo="gemini-3.8-flash", usos=[Uso(entrada=1_000, salida=100, pensamiento=50)]
    )
    e = Evento(
        tipo="llamada_modelo", componente="scriba", creado_en=AHORA, **Evento.de_llamada(llamada)
    )
    assert (e.modelo, e.tokens_entrada, e.tokens_salida) == ("gemini-3.8-flash", 1_000, 150)
    assert e.costo_usd == pytest.approx((1_000 * 1.50 + 150 * 7.50) / 1e6)
    sin_precio = Evento.de_llamada(Llamada(texto="", modelo="raro", usos=[Uso(entrada=1)]))
    assert sin_precio["costo_usd"] is None
