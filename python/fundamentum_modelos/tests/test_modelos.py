from types import SimpleNamespace

import pytest
from fundamentum_modelos import PRECIOS, Registro, Uso, costo_usd, normalizar, precio


def test_normaliza_rutas_y_versiones():
    ruta = "projects/p/locations/global/publishers/anthropic/models/claude-sonnet-5-5@20260901"
    assert normalizar(ruta) == "claude-sonnet-5-5"
    assert normalizar("gemini-3.8-flash") == "gemini-3.8-flash"


def test_modelo_sin_precio_falla_en_voz_alta():
    with pytest.raises(KeyError):
        precio("gemini-2.5-flash")


def test_costo_gemini_tarifa_estandar():
    # 1M de entrada y 1M de salida con 3.8 Flash = 1.50 + 7.50
    assert costo_usd("gemini-3.8-flash", Uso(entrada=1_000_000, salida=1_000_000)) == pytest.approx(
        9.0
    )


def test_cache_y_pensamiento():
    uso = Uso(entrada=1_000_000, cache_lectura=400_000, salida=0, pensamiento=1_000_000)
    # 600k a 1.50 + 400k a 0.15 + 1M de pensamiento a 7.50
    assert costo_usd("gemini-3.8-flash", uso) == pytest.approx(0.9 + 0.06 + 7.5)


def test_claude_escritura_de_cache():
    uso = Uso(entrada=1_000_000, cache_escritura=1_000_000)
    assert costo_usd("claude-sonnet-5-5", uso) == pytest.approx(2.50)


def test_tarifa_de_contexto_largo():
    corto = costo_usd("claude-haiku-5-5", Uso(entrada=99_999))
    largo = costo_usd("claude-haiku-5-5", Uso(entrada=100_000))
    assert corto == pytest.approx(99_999 * 0.10 / 1e6)
    assert largo == pytest.approx(100_000 * 0.50 / 1e6)


def test_uso_desde_metadata_de_gemini():
    meta = SimpleNamespace(
        prompt_token_count=1000,
        tool_use_prompt_token_count=50,
        candidates_token_count=200,
        cached_content_token_count=300,
        thoughts_token_count=40,
    )
    assert Uso.desde_metadata(meta) == Uso(
        entrada=1050, salida=200, cache_lectura=300, cache_escritura=0, pensamiento=40
    )


def test_registro_con_sobrescritura(monkeypatch):
    registro = Registro(
        "iterum", {"concierge": "gemini-3.8-flash", "lectura.reserva": "gemini-3.5-flash-lite"}
    )
    assert registro.modelo("concierge") == "gemini-3.8-flash"
    monkeypatch.setenv("ITERUM_MODELO_LECTURA_RESERVA", "claude-haiku-5-5")
    assert registro.modelo("lectura.reserva") == "claude-haiku-5-5"
    registro.verificar()
    with pytest.raises(KeyError):
        registro.modelo("inexistente")


def test_registro_detecta_modelos_sin_precio(monkeypatch):
    monkeypatch.setenv("DOMI_MODELO_IUDEX", "gemini-2.5-pro")
    with pytest.raises(ValueError, match="sin precio"):
        Registro("domi", {"iudex": "gemini-3.8-flash"}).verificar()


def test_todos_los_precios_son_positivos():
    for p in PRECIOS.values():
        assert p.entrada > 0 and p.salida > 0 and p.cache_lectura >= 0
