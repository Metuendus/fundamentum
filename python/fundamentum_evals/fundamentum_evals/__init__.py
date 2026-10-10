"""Evals comunes: calidad con adk eval y gate de costo y latencia contra una línea base."""

from fundamentum_evals.eficiencia import METRICAS, comparar, resumir
from fundamentum_evals.runner import Informe, evaluar

__all__ = ["METRICAS", "Informe", "comparar", "evaluar", "resumir"]
