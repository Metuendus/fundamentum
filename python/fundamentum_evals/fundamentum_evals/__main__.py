"""python -m fundamentum_evals <módulo> <carpeta> [--runs 2] [--linea-base ruta] [--factor 2] [--actualizar]"""

import argparse
import asyncio
import sys
from pathlib import Path

from fundamentum_evals.runner import evaluar


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "modulo", help="Módulo con `agent.root_agent` (y `agent.app`), p. ej. evals.eval_app"
    )
    parser.add_argument("carpeta", help="Carpeta con *.test.json y su test_config.json")
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--linea-base", type=Path)
    parser.add_argument("--factor", type=float, default=2.0)
    parser.add_argument("--actualizar", action="store_true", help="Reescribe la línea base")
    args = parser.parse_args()
    informe = asyncio.run(
        evaluar(
            args.modulo,
            args.carpeta,
            runs=args.runs,
            linea_base=args.linea_base,
            factor=args.factor,
            actualizar=args.actualizar,
        )
    )
    print(informe.texto())
    sys.exit(0 if informe.ok else 1)


if __name__ == "__main__":
    main()
