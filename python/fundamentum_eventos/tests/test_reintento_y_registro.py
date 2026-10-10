"""Reintentos de servicios y el registro de Firestore con un cliente falso."""

import pytest
from fundamentum_eventos import con_reintentos
from fundamentum_eventos.registro_firestore import RegistroFirestore
from pydantic import BaseModel


class ErrorCodigo(Exception):
    def __init__(self, code):
        self.code = code


def test_reintenta_lo_transitorio_y_propaga_lo_demas():
    intentos, esperas = [], []

    def llamada():
        intentos.append(1)
        if len(intentos) < 3:
            raise ErrorCodigo(429)
        return "ok"

    assert con_reintentos(llamada, dormir=esperas.append) == "ok" and esperas == [3.0, 8.0]
    with pytest.raises(ErrorCodigo):
        con_reintentos(lambda: (_ for _ in ()).throw(ErrorCodigo(400)), dormir=esperas.append)


class Doc:
    def __init__(self, db, ruta):
        self.db, self.ruta = db, ruta

    def get(self, transaction=None):
        datos = self.db.docs.get(self.ruta)
        return type("Snap", (), {"to_dict": lambda _s: dict(datos) if datos else None})()

    def set(self, datos, merge=False):
        base = dict(self.db.docs.get(self.ruta, {})) if merge else {}
        for clave, valor in datos.items():
            incremento = getattr(valor, "value", None)
            base[clave] = (
                base.get(clave, 0) + incremento if type(valor).__name__ == "Increment" else valor
            )
        self.db.docs[self.ruta] = base

    def update(self, datos):
        self.db.docs[self.ruta] = {**self.db.docs[self.ruta], **datos}

    def delete(self):
        self.db.docs.pop(self.ruta, None)

    def collection(self, nombre):
        return Col(self.db, f"{self.ruta}/{nombre}")


class Col:
    def __init__(self, db, ruta):
        self.db, self.ruta = db, ruta

    def document(self, id=None):
        self.db.n += 1
        return Doc(self.db, f"{self.ruta}/{id or f'auto{self.db.n}'}")


class DbFalsa:
    def __init__(self):
        self.docs, self.n = {}, 0

    def collection(self, nombre):
        return Col(self, nombre)


class Evento(BaseModel):
    tipo: str
    costo_usd: float | None = None


def test_presupuestos_procesados_y_bitacora():
    db = DbFalsa()
    r = RegistroFirestore(db, presupuesto_por_defecto=0.25, presupuesto_global_por_defecto=2.0)
    assert (r.gasto_hoy("u1"), r.presupuesto("u1"), r.presupuesto_global()) == (0.0, 0.25, 2.0)

    r.sumar_gasto("u1", 0.10)
    r.sumar_gasto("u1", 0.05)
    r.sumar_gasto(None, 0.30)
    assert r.gasto_hoy("u1") == pytest.approx(0.15) and r.gasto_global_hoy() == pytest.approx(0.30)

    assert not r.ya_procesado("e1", "scriba")
    r.marcar_procesado("e1", "scriba")
    assert r.ya_procesado("e1", "scriba") and not r.ya_procesado("e1", "memoria")

    r.registrar_evento("u1", Evento(tipo="llamada_modelo"))
    [ruta] = [k for k in db.docs if k.startswith("usuarios/u1/eventos/")]
    assert db.docs[ruta] == {"tipo": "llamada_modelo"}  # sin nulos
