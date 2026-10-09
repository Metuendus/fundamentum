"""Registro tarea → modelo de cada app.

Cada app declara sus tareas en un solo lugar y puede sobrescribir una con una variable de entorno
(`{PREFIJO}_MODELO_{TAREA}`, con puntos y guiones como `_`), sin tocar código. Cambiar el modelo de
una tarea es configuración, pero solo debe hacerse cuando su evaluación lo respalde.
"""

import os
from collections.abc import Mapping

from fundamentum_modelos.precios import PRECIOS, normalizar


class Registro:
    def __init__(self, prefijo: str, tareas: Mapping[str, str]) -> None:
        self.prefijo = prefijo.upper()
        self._tareas = dict(tareas)

    def variable(self, tarea: str) -> str:
        clave = tarea.upper().replace(".", "_").replace("-", "_")
        return f"{self.prefijo}_MODELO_{clave}"

    def modelo(self, tarea: str) -> str:
        if tarea not in self._tareas:
            raise KeyError(f"Tarea sin modelo en el registro: {tarea}")
        return os.environ.get(self.variable(tarea), self._tareas[tarea])

    def tareas(self) -> dict[str, str]:
        return {t: self.modelo(t) for t in self._tareas}

    def verificar(self) -> None:
        """Falla si alguna tarea apunta a un modelo sin precio. Correr en las pruebas de cada app."""
        sin_precio = {t: m for t, m in self.tareas().items() if normalizar(m) not in PRECIOS}
        if sin_precio:
            raise ValueError(f"Modelos sin precio registrado: {sin_precio}")
