"""El gate de eficiencia: una versión que duplica el costo hace fallar el check."""

import sys
from pathlib import Path

import pytest
from fundamentum_evals import comparar, evaluar

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI))  # app_falsa_evals


def test_comparar_con_factor_y_minimo():
    base = {"c": {"token_usage_v1": 1_000, "invocation_duration_v1": 0.2}}
    problemas, _ = comparar({"c": {"token_usage_v1": 2_500, "invocation_duration_v1": 0.9}}, base)
    assert len(problemas) == 1 and "token_usage_v1" in problemas[0]  # 0.9 s no pasa el mínimo
    problemas, _ = comparar({"c": {"token_usage_v1": 1_900}}, base)
    assert problemas == []
    _, avisos = comparar({"nuevo": {"token_usage_v1": 1}}, base)
    assert avisos == ["nuevo: sin línea base"]


async def test_duplicar_el_costo_falla_el_gate(tmp_path, monkeypatch):
    linea_base = tmp_path / "linea_base.json"
    monkeypatch.setenv("FUNDAMENTUM_EVALS_FACTOR", "1")
    informe = await evaluar(
        "app_falsa_evals", AQUI / "datos", runs=1, linea_base=linea_base, actualizar=True
    )
    assert informe.ok and informe.resumen["saluda"]["token_usage_v1"] == pytest.approx(1_100)

    monkeypatch.setenv("FUNDAMENTUM_EVALS_FACTOR", "1.5")
    assert (await evaluar("app_falsa_evals", AQUI / "datos", runs=1, linea_base=linea_base)).ok

    monkeypatch.setenv("FUNDAMENTUM_EVALS_FACTOR", "3")
    informe = await evaluar("app_falsa_evals", AQUI / "datos", runs=1, linea_base=linea_base)
    assert not informe.ok and "token_usage_v1" in informe.eficiencia[0]
    assert "✗ Eficiencia" in informe.texto()
