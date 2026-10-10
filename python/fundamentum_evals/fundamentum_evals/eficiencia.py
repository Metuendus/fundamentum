"""Gate de eficiencia: compara tokens, llamadas al modelo y duración por turno contra una línea base.

ADK reporta `token_usage_v1`, `inference_call_count_v1` e `invocation_duration_v1` en cada eval, pero
como métricas informativas: nunca fallan. Aquí se promedian por caso entre corridas y se comparan
con la línea base guardada en el repo de la app. Falla si una métrica pasa de `factor` veces su
base (por defecto, el doble) y además la diferencia supera un mínimo, para que el ruido de una
duración de milisegundos no tumbe el CI.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

# métrica → diferencia mínima para fallar (en su unidad)
METRICAS = {
    "token_usage_v1": 0.0,
    "inference_call_count_v1": 0.0,
    "invocation_duration_v1": 2.0,  # segundos
}

Resumen = dict[str, dict[str, float]]  # eval_id → métrica → promedio por turno


def resumir(archivos: Iterable[Path]) -> Resumen:
    """Lee los `*.evalset_result.json` de ADK y promedia cada métrica por caso entre corridas."""
    from google.adk.evaluation.eval_result import EvalSetResult

    valores: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for archivo in archivos:
        resultado = EvalSetResult.model_validate_json(Path(archivo).read_text())
        for caso in resultado.eval_case_results:
            for metrica in caso.overall_eval_metric_results:
                if metrica.metric_name in METRICAS and metrica.score is not None:
                    valores[caso.eval_id][metrica.metric_name].append(metrica.score)
    return {
        caso: {m: sum(v) / len(v) for m, v in metricas.items()}
        for caso, metricas in valores.items()
    }


def comparar(actual: Resumen, base: Resumen, factor: float = 2.0) -> tuple[list[str], list[str]]:
    """(problemas, avisos). Un caso o métrica sin línea base es aviso, no falla."""
    problemas, avisos = [], []
    for caso, metricas in sorted(actual.items()):
        if caso not in base:
            avisos.append(f"{caso}: sin línea base")
            continue
        for metrica, valor in sorted(metricas.items()):
            referencia = base[caso].get(metrica)
            if referencia is None:
                avisos.append(f"{caso} · {metrica}: sin línea base")
            elif valor > factor * referencia and valor - referencia > METRICAS[metrica]:
                problemas.append(
                    f"{caso} · {metrica}: {valor:.1f} contra {referencia:.1f} de base "
                    f"(más de {factor:g}×)"
                )
    return problemas, avisos


def leer_linea_base(ruta: Path) -> Resumen:
    return json.loads(ruta.read_text()) if ruta.exists() else {}


def guardar_linea_base(ruta: Path, resumen: Resumen) -> None:
    ruta.write_text(json.dumps(resumen, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
