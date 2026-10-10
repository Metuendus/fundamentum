"""Eventos, propuestas y Despachador comunes a las apps."""

from fundamentum_eventos.despachador import (
    Decision,
    Despachador,
    Registro,
    RegistroGlobal,
    Resultado,
)
from fundamentum_eventos.esquemas import (
    ClasePropuesta,
    EstadoPropuesta,
    EventoBase,
    EventoBusBase,
    Modelo,
    PropuestaBase,
    UsoModelo,
)
from fundamentum_eventos.reintento import con_reintentos, es_transitorio

__all__ = [
    "ClasePropuesta",
    "Decision",
    "Despachador",
    "EstadoPropuesta",
    "EventoBase",
    "EventoBusBase",
    "Modelo",
    "PropuestaBase",
    "Registro",
    "RegistroGlobal",
    "Resultado",
    "UsoModelo",
    "con_reintentos",
    "es_transitorio",
]
