"""Decisión de acceso, lector de Firestore con un cliente falso y el portero de Firebase Auth."""

import sys
from datetime import UTC, datetime, timedelta
from types import ModuleType, SimpleNamespace

import pytest
from fundamentum_acceso import (
    LectorFirestore,
    LectorMemoria,
    Modo,
    Motivo,
    Origen,
    Pase,
    Permiso,
    crear_portero,
    decidir,
    evaluar,
)

AHORA = datetime(2026, 10, 29, 12, tzinfo=UTC)


def pase(correo="ana@x.com", **apps):
    return Pase(correo=correo, apps={a: Permiso(alta=AHORA, **p) for a, p in apps.items()})


def caso(**kw):
    base = {
        "app": "iterum",
        "correo": "ana@x.com",
        "verificado": True,
        "proveedor": "google.com",
        "modo": Modo.BETA,
        "pase": pase(iterum={}),
        "ahora": AHORA,
    }
    return decidir(**{**base, **kw})


def test_en_beta_solo_entra_quien_tiene_permiso_para_esa_app():
    assert caso().ok
    assert caso(app="domi").motivo == Motivo.BETA_PRIVADA
    assert caso(pase=None).motivo == Motivo.BETA_PRIVADA


def test_abierta_deja_entrar_a_cualquiera_con_correo_verificado():
    assert caso(modo=Modo.ABIERTA, pase=None).ok
    assert caso(modo=Modo.ABIERTA, correo=None).motivo == Motivo.SIN_CORREO


def test_verificacion_salvo_contrasena_que_la_exige_la_app():
    assert caso(verificado=False).motivo == Motivo.CORREO_NO_VERIFICADO
    assert caso(verificado=False, proveedor="password").ok


def test_pase_de_invitado_vence():
    invitado = pase(iterum={"origen": Origen.INVITACION, "vence": AHORA + timedelta(days=1)})
    assert caso(pase=invitado).ok
    assert caso(pase=invitado, ahora=AHORA + timedelta(days=2)).motivo == Motivo.PASE_VENCIDO


class Snap:
    def __init__(self, datos):
        self.datos = datos

    def to_dict(self):
        return self.datos


class DbFalsa:
    def __init__(self, docs):
        self.docs = docs

    def collection(self, col):
        return SimpleNamespace(
            document=lambda id: SimpleNamespace(get=lambda: Snap(self.docs.get(f"{col}/{id}")))
        )


def test_lector_firestore_normaliza_y_cae_en_beta():
    db = DbFalsa(
        {
            "acceso/ana@x.com": {"apps": {"domi": {"alta": AHORA, "nota": "amiga"}}},
            "apps/vocatio": {"modo": "abierta"},
            "apps/domi": {"modo": "rara"},
        }
    )
    lector = LectorFirestore(db)
    assert lector.pase("  Ana@X.com ").apps["domi"].nota == "amiga"
    assert lector.pase("otro@x.com") is None
    assert (lector.modo("vocatio"), lector.modo("domi"), lector.modo("iterum")) == (
        Modo.ABIERTA,
        Modo.BETA,
        Modo.BETA,
    )


class LectorRoto:
    def modo(self, app):
        raise RuntimeError("Firestore caído")

    def pase(self, correo):
        raise AssertionError


def test_falla_cerrado_si_no_se_lee_la_lista():
    v = evaluar("iterum", LectorRoto(), correo="ana@x.com", verificado=True, proveedor="google.com")
    assert v.motivo == Motivo.ACCESO_NO_DISPONIBLE


@pytest.fixture
def https_fn_falso(monkeypatch):
    class HttpsError(Exception):
        def __init__(self, code, message):
            super().__init__(message)
            self.code, self.message = code, message

    https_fn = SimpleNamespace(
        HttpsError=HttpsError,
        FunctionsErrorCode=SimpleNamespace(PERMISSION_DENIED="permission-denied"),
    )
    paquete = ModuleType("firebase_functions")
    paquete.https_fn = https_fn
    monkeypatch.setitem(sys.modules, "firebase_functions", paquete)
    return https_fn


def evento(correo, verificado=True, proveedor="google.com"):
    return SimpleNamespace(
        data=SimpleNamespace(email=correo, email_verified=verificado, provider_data=[]),
        additional_user_info=SimpleNamespace(provider_id=proveedor),
    )


def test_portero_rechaza_con_el_motivo_y_crea_el_lector_una_vez(https_fn_falso):
    creados = []

    def fabrica():
        creados.append(1)
        return LectorMemoria([pase(iterum={})])

    portero = crear_portero("iterum", fabrica)
    assert portero(evento("ana@x.com")) is None
    with pytest.raises(https_fn_falso.HttpsError) as e:
        portero(evento("intruso@x.com"))
    assert (e.value.code, e.value.message, len(creados)) == ("permission-denied", "beta_privada", 1)
