"""Nada de datos personales en los logs: `redactar` y un filtro de `logging` que lo aplica.

Cubre lo que se cuela con más frecuencia en un log: correos, teléfonos de México, tarjetas, CURP y
RFC. No sustituye a no registrar contenido: es la red de seguridad.
"""

from __future__ import annotations

import logging
import re

PATRONES = [
    ("correo", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("curp", re.compile(r"\b[A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{5}[A-Z\d]\d\b")),
    ("rfc", re.compile(r"\b[A-ZÑ&]{3,4}\d{6}[A-Z\d]{3}\b")),
    ("tarjeta", re.compile(r"\b(?:\d[ -]?){13,16}\b")),
    (
        "telefono",
        re.compile(r"(?<!\d)(?:\+?52[ -]?)?(?:\(?\d{2,3}\)?[ -]?)\d{3,4}[ -]?\d{4}(?!\d)"),
    ),
]


def redactar(texto: str) -> str:
    for nombre, patron in PATRONES:
        texto = patron.sub(f"[{nombre}]", texto)
    return texto


class FiltroDatosPersonales(logging.Filter):
    """`logging.getLogger().addFilter(...)` en cada handler: redacta mensaje y argumentos."""

    def filter(self, registro: logging.LogRecord) -> bool:
        registro.msg = redactar(registro.getMessage())
        registro.args = None
        return True


def instalar_filtro(logger: logging.Logger | None = None) -> None:
    """Agrega el filtro a los handlers del logger (raíz por defecto). Los filtros de un logger no se
    aplican a lo que propagan sus hijos; los de un handler, sí."""
    for handler in (logger or logging.getLogger()).handlers:
        if not any(isinstance(f, FiltroDatosPersonales) for f in handler.filters):
            handler.addFilter(FiltroDatosPersonales())
