"""El Despachador común: idempotencia, presupuesto por usuario y tope global (Vocatio y Domi)."""

import base64
import json
from typing import Literal

import pytest
from fundamentum_eventos import Despachador, EventoBusBase


class EventoBus(EventoBusBase):
    tipo: Literal[
        "preparar_aplicacion",
        "etapa_cambiada",
        "correo_recibido",
        "anuncio_nuevo",
        "inmueble_actualizado",
    ]


DESPACHADOR = Despachador(
    EventoBus,
    consumen_presupuesto={"preparar_aplicacion"},
    consumen_global={"anuncio_nuevo"},
)


class RegistroFalso:
    def __init__(
        self, procesados=(), gasto=0.0, presupuesto=0.25, gasto_global=0.0, tope_global=1.0
    ):
        self.procesados = set(procesados)
        self.gasto, self.tope = gasto, presupuesto
        self.gasto_global, self.tope_global = gasto_global, tope_global

    def ya_procesado(self, evento_id, componente):
        return (evento_id, componente) in self.procesados

    def gasto_hoy(self, uid):
        return self.gasto

    def presupuesto(self, uid):
        return self.tope

    def gasto_global_hoy(self):
        return self.gasto_global

    def presupuesto_global(self):
        return self.tope_global


class RegistroSinGlobal:
    def ya_procesado(self, evento_id, componente):
        return False

    def gasto_hoy(self, uid):
        return 0.0

    def presupuesto(self, uid):
        return 0.25


def push(tipo, atributo=None, uid="u1"):
    datos = {"evento_id": "e1", "uid": uid, "tipo": tipo, "creado_en": "2026-10-02T07:00:00Z"}
    return {
        "message": {
            "data": base64.b64encode(json.dumps(datos).encode()).decode(),
            "attributes": {"tipo": atributo or tipo},
        }
    }


def decidir(tipo, registro, componente="c", uid="u1"):
    return DESPACHADOR.decidir(
        DESPACHADOR.decodificar_push(push(tipo, uid=uid)), componente, registro
    ).decision


def test_procesa_evento_nuevo_y_valida_con_el_modelo_de_la_app():
    evento = DESPACHADOR.decodificar_push(push("preparar_aplicacion"))
    assert isinstance(evento, EventoBus)
    assert decidir("preparar_aplicacion", RegistroFalso()) == "procesar"


def test_duplicado_por_evento_y_componente():
    registro = RegistroFalso(procesados={("e1", "scriba")})
    assert decidir("preparar_aplicacion", registro, "scriba") == "duplicado"
    assert decidir("preparar_aplicacion", registro, "memoria") == "procesar"


def test_corta_por_presupuesto_solo_si_consume_modelo():
    agotado = RegistroFalso(gasto=0.30)
    assert decidir("preparar_aplicacion", agotado) == "presupuesto_agotado"
    assert decidir("etapa_cambiada", agotado) == "procesar"
    assert decidir("correo_recibido", agotado) == "procesar"


def test_tope_global_para_eventos_de_sistema():
    agotado = RegistroFalso(gasto_global=1.0)
    assert decidir("anuncio_nuevo", agotado, uid=None) == "presupuesto_agotado"
    # Lo que es código (sin modelo) no se corta: perderlo dejaría datos desactualizados.
    assert decidir("inmueble_actualizado", agotado, uid=None) == "procesar"
    assert decidir("anuncio_nuevo", RegistroFalso(gasto_global=0.5), uid=None) == "procesar"


def test_tope_global_sin_registro_global_falla_en_voz_alta():
    with pytest.raises(TypeError):
        decidir("anuncio_nuevo", RegistroSinGlobal(), uid=None)
    assert decidir("preparar_aplicacion", RegistroSinGlobal()) == "procesar"


def test_atributo_y_cuerpo_deben_coincidir():
    with pytest.raises(ValueError):
        DESPACHADOR.decodificar_push(push("etapa_cambiada", atributo="preparar_aplicacion"))


def test_tipo_desconocido_es_error():
    with pytest.raises(ValueError):
        DESPACHADOR.decodificar_push(push("otro"))
