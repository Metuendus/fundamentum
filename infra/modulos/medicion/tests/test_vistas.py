"""Las vistas parsean como GoogleSQL y `costo_llamadas` calcula bien, ejecutada en DuckDB.

`terraform validate` no revisa el SQL; sin esta prueba un error solo aparece en el `apply`.
"""

import json
from pathlib import Path

import duckdb
import pytest
import sqlglot

VISTAS = Path(__file__).resolve().parents[1] / "vistas"


def renderizar(nombre: str, proyecto: str = "p", agentes: str = "agentes") -> str:
    sql = (VISTAS / nombre).read_text()
    valores = {
        "proyecto": proyecto,
        "agentes": agentes,
        "resultados": "fundamentum_resultados",
        "precios": (VISTAS / "precios.sql").read_text(),
        "usuarios_internos": '["fundador"]',
    }
    for clave, valor in valores.items():
        sql = sql.replace("${" + clave + "}", valor)
    return sql


@pytest.mark.parametrize("nombre", sorted(p.name for p in VISTAS.glob("*.sql")))
def test_vista_es_googlesql_valido(nombre):
    sqlglot.parse_one(renderizar(nombre), read="bigquery")


@pytest.fixture
def eventos():
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE agent_events (timestamp TIMESTAMP, event_id VARCHAR, event_type VARCHAR,"
        " agent VARCHAR, user_id VARCHAR, session_id VARCHAR, invocation_id VARCHAR,"
        " span_id VARCHAR, attributes JSON, latency_ms JSON, error_message VARCHAR)"
    )

    def agregar(event_id, tipo, span, uid, atributos, latencia=None):
        con.execute(
            "INSERT INTO agent_events VALUES (now(), ?, ?, 'concierge', ?, 's', 'i', ?, ?, ?, NULL)",
            [event_id, tipo, uid, span, json.dumps(atributos), json.dumps(latencia or {})],
        )

    return con, agregar


def costo_llamadas(con) -> dict[str, tuple]:
    sql = sqlglot.transpile(
        renderizar("costo_llamadas.sql", proyecto="memory", agentes="main"),
        read="bigquery",
        write="duckdb",
    )[0]
    # DuckDB no admite LIMIT dentro de un agregado; el orden ya deja primero al prefijo más largo.
    sql = sql.replace(" DESC LIMIT 1)[1]", " DESC)[1]")
    filas = con.execute(sql).fetchall()
    columnas = [c[0] for c in con.description]
    return {f[columnas.index("modelo")]: dict(zip(columnas, f, strict=True)) for f in filas}


def test_costo_por_llamada(eventos):
    con, agregar = eventos
    uso = {"prompt_token_count": 10_000, "candidates_token_count": 50}
    agregar("1", "LLM_REQUEST", "a", "u1", {"model": "gemini-3.8-flash"})
    agregar(
        "2",
        "LLM_RESPONSE",
        "a",
        "u1",
        {
            "model_version": "gemini-3.8-flash-001",
            "finish_reason": "STOP",
            "custom_tags": {"app": "iterum"},
            "usage_metadata": {**uso, "cached_content_token_count": 2_000},
        },
        {"total_ms": 900},
    )
    agregar(
        "3",
        "LLM_RESPONSE",
        "b",
        "fundador",
        {
            "model_version": "projects/x/publishers/anthropic/models/claude-haiku-5-5@2026",
            "finish_reason": "STOP",
            "usage_metadata": {"prompt_token_count": 200_000, "candidates_token_count": 1_000},
        },
    )
    agregar(
        "4", "LLM_RESPONSE", "c", "u1", {"model_version": "modelo-raro", "finish_reason": "STOP"}
    )
    agregar("5", "LLM_RESPONSE", "d", "u1", {"model_version": "parcial", "usage_metadata": uso})

    filas = costo_llamadas(con)

    assert set(filas) == {"gemini-3.8-flash-001", "claude-haiku-5-5", "modelo-raro"}
    gemini = filas["gemini-3.8-flash-001"]
    assert gemini["app"] == "iterum" and gemini["latencia_ms"] == 900
    assert gemini["costo_usd"] == pytest.approx((8_000 * 1.50 + 2_000 * 0.15 + 50 * 7.50) / 1e6)
    # Haiku 5.5 desde 100K tokens de entrada usa el tramo largo.
    haiku = filas["claude-haiku-5-5"]
    assert haiku["costo_usd"] == pytest.approx((200_000 * 0.50 + 1_000 * 2.50) / 1e6)
    assert haiku["usuario_interno"] and not gemini["usuario_interno"]
    raro = filas["modelo-raro"]
    assert raro["costo_usd"] is None and raro["precio_desconocido"]
