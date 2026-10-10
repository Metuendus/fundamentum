"""La tabla de precios como SQL de BigQuery, generada desde `PRECIOS` para que no se desfasen.

`infra/modulos/medicion/vistas/precios.sql` es la salida de `python -m fundamentum_modelos.sql`;
una prueba falla si el archivo y `PRECIOS` no coinciden.
"""

import sys
from pathlib import Path

from fundamentum_modelos.precios import CONSULTADO, FUENTE, PRECIOS, Precio

RUTA = Path(__file__).resolve().parents[3] / "infra/modulos/medicion/vistas/precios.sql"


def _num(valor: float | int | None, tipo: str) -> str:
    return f"CAST(NULL AS {tipo})" if valor is None else repr(valor)


def _fila(modelo: str, p: Precio) -> str:
    largo = p.largo
    campos = [
        f"'{modelo}' AS modelo",
        f"{_num(p.entrada, 'FLOAT64')} AS entrada",
        f"{_num(p.salida, 'FLOAT64')} AS salida",
        f"{_num(p.cache_lectura, 'FLOAT64')} AS cache_lectura",
        f"{_num(p.umbral_largo, 'INT64')} AS umbral_largo",
        f"{_num(largo.entrada if largo else None, 'FLOAT64')} AS entrada_largo",
        f"{_num(largo.salida if largo else None, 'FLOAT64')} AS salida_largo",
        f"{_num(largo.cache_lectura if largo else None, 'FLOAT64')} AS cache_lectura_largo",
    ]
    return "  STRUCT(" + ", ".join(campos) + ")"


def precios_sql() -> str:
    filas = ",\n".join(_fila(m, p) for m, p in sorted(PRECIOS.items()))
    return (
        "-- Generado por `python -m fundamentum_modelos.sql`. No editar a mano.\n"
        f"-- Fuente: {FUENTE} (consultado el {CONSULTADO}). USD por millón de tokens.\n"
        f"SELECT * FROM UNNEST([\n{filas}\n])\n"
    )


if __name__ == "__main__":
    RUTA.write_text(precios_sql())
    sys.stdout.write(f"{RUTA}\n")
