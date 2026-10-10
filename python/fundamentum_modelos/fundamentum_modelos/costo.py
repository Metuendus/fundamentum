"""Uso de tokens de una llamada y su costo en USD."""

from dataclasses import dataclass
from typing import Any

from fundamentum_modelos.precios import precio


@dataclass(frozen=True)
class Uso:
    """Tokens de una llamada.

    `entrada` incluye los tokens leídos de caché (`cache_lectura` es un desglose, no una suma),
    igual que `prompt_token_count` de Gemini y que ADK al traducir el uso de Claude.
    `pensamiento` se cobra como salida.
    """

    entrada: int = 0
    salida: int = 0
    cache_lectura: int = 0
    cache_escritura: int = 0
    pensamiento: int = 0

    def __add__(self, otro: "Uso") -> "Uso":
        return Uso(
            entrada=self.entrada + otro.entrada,
            salida=self.salida + otro.salida,
            cache_lectura=self.cache_lectura + otro.cache_lectura,
            cache_escritura=self.cache_escritura + otro.cache_escritura,
            pensamiento=self.pensamiento + otro.pensamiento,
        )

    @classmethod
    def desde_metadata(cls, metadata: Any) -> "Uso":
        """Lee un `GenerateContentResponseUsageMetadata` (Gemini, o Claude traducido por ADK)."""

        def n(campo: str) -> int:
            return int(getattr(metadata, campo, None) or 0)

        return cls(
            entrada=n("prompt_token_count") + n("tool_use_prompt_token_count"),
            salida=n("candidates_token_count"),
            cache_lectura=n("cached_content_token_count"),
            cache_escritura=n("cache_creation_input_tokens"),
            pensamiento=n("thoughts_token_count"),
        )


def costo_usd(modelo: str, uso: Uso) -> float:
    """Costo estimado de una llamada con la tarifa de `precios.PRECIOS`."""
    p = precio(modelo)
    if p.umbral_largo is not None and p.largo is not None and uso.entrada >= p.umbral_largo:
        p = p.largo
    sin_cache = max(uso.entrada - uso.cache_lectura - uso.cache_escritura, 0)
    escritura = p.cache_escritura if p.cache_escritura is not None else p.entrada
    total = (
        sin_cache * p.entrada
        + uso.cache_lectura * p.cache_lectura
        + uso.cache_escritura * escritura
        + (uso.salida + uso.pensamiento) * p.salida
    )
    return total / 1_000_000
