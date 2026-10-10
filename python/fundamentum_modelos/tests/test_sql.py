from fundamentum_modelos import PRECIOS
from fundamentum_modelos.sql import RUTA, precios_sql


def test_precios_sql_al_dia():
    assert RUTA.read_text() == precios_sql(), "Corre `uv run python -m fundamentum_modelos.sql`"


def test_cada_modelo_tiene_fila():
    sql = precios_sql()
    assert all(f"'{modelo}' AS modelo" in sql for modelo in PRECIOS)
