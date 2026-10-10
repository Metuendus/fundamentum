"""Corre los `*.test.json` de una carpeta con `adk eval` y aplica el gate de eficiencia.

Calidad: la decide ADK con el `test_config.json` de cada conjunto (trayectoria, rúbricas,
`hallucinations_v1`...). Eficiencia: `eficiencia.comparar` contra la línea base del repo.
"""

from __future__ import annotations

import asyncio
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from fundamentum_evals.eficiencia import (
    Resumen,
    comparar,
    guardar_linea_base,
    leer_linea_base,
    resumir,
)


@dataclass
class Informe:
    calidad: list[str] = field(default_factory=list)
    eficiencia: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    resumen: Resumen = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.calidad and not self.eficiencia

    def texto(self) -> str:
        lineas = [f"✗ Calidad: {p}" for p in self.calidad]
        lineas += [f"✗ Eficiencia: {p}" for p in self.eficiencia]
        lineas += [f"· {a}" for a in self.avisos]
        for caso, metricas in sorted(self.resumen.items()):
            valores = ", ".join(f"{m} {v:.1f}" for m, v in sorted(metricas.items()))
            lineas.append(f"  {caso}: {valores}")
        lineas.append("✓ Pasa" if self.ok else "✗ No pasa")
        return "\n".join(lineas)


async def evaluar(
    modulo: str,
    datos: str | Path,
    *,
    runs: int = 2,
    linea_base: Path | None = None,
    factor: float = 2.0,
    actualizar: bool = False,
) -> Informe:
    """`actualizar=True` reescribe la línea base con esta corrida (cuando un cambio de costo es a
    propósito y se revisa en el PR)."""
    from google.adk.evaluation.agent_evaluator import AgentEvaluator
    from google.adk.evaluation.local_eval_set_results_manager import LocalEvalSetResultsManager

    informe = Informe()
    with tempfile.TemporaryDirectory() as carpeta:
        try:
            await AgentEvaluator.evaluate(
                agent_module=modulo,
                eval_dataset_file_path_or_dir=str(datos),
                num_runs=runs,
                print_detailed_results=False,
                app_name="evals",
                eval_set_results_manager=LocalEvalSetResultsManager(carpeta),
            )
        except AssertionError as error:  # el evaluador de ADK falla con assert
            informe.calidad.append(str(error).strip() or "un criterio quedó por debajo del umbral")
        archivos = await asyncio.to_thread(
            lambda: list(Path(carpeta).rglob("*.evalset_result.json"))
        )
        informe.resumen = await asyncio.to_thread(resumir, archivos)

    if linea_base is not None:
        if actualizar:
            guardar_linea_base(linea_base, informe.resumen)
            informe.avisos.append(f"línea base actualizada en {linea_base}")
        else:
            informe.eficiencia, avisos = comparar(
                informe.resumen, leer_linea_base(linea_base), factor
            )
            informe.avisos += avisos
    return informe
