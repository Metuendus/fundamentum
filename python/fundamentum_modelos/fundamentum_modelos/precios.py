"""Precios por millón de tokens (USD) de los modelos que las apps consumen vía Model Garden.

Fuente: https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing,
consultada el 2026-10-09, tarifa Standard del endpoint global.

Política: se registra la tarifa estándar, no la promocional. Gemini 3.8 Flash cuesta la mitad
hasta el 2026-12-31 (0.75 / 3.75); usar la estándar evita subestimar el costo por resultado que
sostiene la propuesta de negocio. La conciliación contra el export de facturación muestra la
diferencia real.

Los identificadores de Claude son los de Model Garden sin el sufijo de versión (`@fecha`);
confirmarlos en la tarjeta del modelo antes de usarlos en producción.
"""

from dataclasses import dataclass

FUENTE = "https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing"
CONSULTADO = "2026-10-09"


@dataclass(frozen=True)
class Precio:
    entrada: float
    salida: float
    cache_lectura: float
    cache_escritura: float | None = None  # Claude cobra la escritura de caché (5 min)
    umbral_largo: int | None = None  # tokens de entrada desde los que aplica la tarifa larga
    largo: "Precio | None" = None


PRECIOS: dict[str, Precio] = {
    # Gemini
    "gemini-3.8-flash": Precio(entrada=1.50, salida=7.50, cache_lectura=0.15),
    "gemini-3.5-flash-lite": Precio(entrada=0.30, salida=2.50, cache_lectura=0.03),
    # Anthropic en Model Garden
    "claude-haiku-5-5": Precio(
        entrada=0.10,
        salida=0.50,
        cache_lectura=0.01,
        cache_escritura=0.125,
        umbral_largo=100_000,
        largo=Precio(entrada=0.50, salida=2.50, cache_lectura=0.05, cache_escritura=0.625),
    ),
    "claude-sonnet-5-5": Precio(
        entrada=2.00, salida=10.00, cache_lectura=0.10, cache_escritura=2.50
    ),
    "claude-opus-5-5": Precio(entrada=4.00, salida=20.00, cache_lectura=0.20, cache_escritura=5.00),
}


def normalizar(modelo: str) -> str:
    """`projects/p/locations/l/publishers/anthropic/models/claude-x@2026` → `claude-x`."""
    return modelo.rsplit("/", 1)[-1].split("@", 1)[0]


def precio(modelo: str) -> Precio:
    """Precio de un modelo. Un modelo sin precio falla en voz alta, nunca cuesta 0."""
    return PRECIOS[normalizar(modelo)]
