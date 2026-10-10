"""Registro del Despachador y escrituras comunes en Firestore (extra `firestore`).

- Idempotencia: `eventos_procesados/{componente}__{evento_id}`, con reclamación atómica que vence a
  los 10 minutos, para que dos entregas simultáneas no llamen dos veces al modelo.
- Presupuesto diario por usuario (`usuarios/{uid}`: `gasto_usd_hoy`, `presupuesto_usd_dia`) y global
  (`sistema/presupuesto`: los mismos campos). Quien reinicia el gasto del día es el reloj de la app.
- Bitácora (`usuarios/{uid}/eventos`) y propuestas (`usuarios/{uid}/propuestas`).

Solo el servidor escribe aquí; las reglas de Firestore de cada app lo garantizan. Los nombres de las
colecciones se pueden cambiar por app.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel

RECLAMACION = timedelta(minutes=10)


class RegistroFirestore:
    def __init__(
        self,
        cliente: Any,
        *,
        usuarios: str = "usuarios",
        procesados: str = "eventos_procesados",
        sistema: str = "sistema",
        presupuesto_por_defecto: float = 0.25,
        presupuesto_global_por_defecto: float = 1.0,
    ) -> None:
        self.db = cliente
        self._usuarios = usuarios
        self._procesados = procesados
        self._sistema = sistema
        self._presupuesto = presupuesto_por_defecto
        self._presupuesto_global = presupuesto_global_por_defecto

    def _usuario(self, uid: str) -> Any:
        return self.db.collection(self._usuarios).document(uid)

    def _procesado(self, evento_id: str, componente: str) -> Any:
        return self.db.collection(self._procesados).document(f"{componente}__{evento_id}")

    def _global(self) -> Any:
        return self.db.collection(self._sistema).document("presupuesto")

    @staticmethod
    def _datos(ref: Any) -> dict[str, Any]:
        return ref.get().to_dict() or {}

    # ─── Registro del Despachador ───────────────────────────────────────────

    def ya_procesado(self, evento_id: str, componente: str) -> bool:
        return self._datos(self._procesado(evento_id, componente)).get("estado") == "hecho"

    def gasto_hoy(self, uid: str) -> float:
        return float(self._datos(self._usuario(uid)).get("gasto_usd_hoy", 0.0))

    def presupuesto(self, uid: str) -> float:
        return float(self._datos(self._usuario(uid)).get("presupuesto_usd_dia", self._presupuesto))

    def gasto_global_hoy(self) -> float:
        return float(self._datos(self._global()).get("gasto_usd_hoy", 0.0))

    def presupuesto_global(self) -> float:
        return float(
            self._datos(self._global()).get("presupuesto_usd_dia", self._presupuesto_global)
        )

    def marcar_procesado(self, evento_id: str, componente: str) -> None:
        self._procesado(evento_id, componente).set(
            {
                "componente": componente,
                "evento_id": evento_id,
                "estado": "hecho",
                "en": datetime.now(UTC).isoformat(),
            }
        )

    def reclamar(self, evento_id: str, componente: str) -> bool:
        """Toma el evento si nadie lo trae en curso. Atómico (transacción de Firestore)."""
        from google.cloud import firestore

        ref = self._procesado(evento_id, componente)
        ahora = datetime.now(UTC)

        @firestore.transactional
        def tomar(tx: Any) -> bool:
            actual = ref.get(transaction=tx).to_dict()
            if actual:
                if actual.get("estado") == "hecho":
                    return False
                if actual.get("vence") and datetime.fromisoformat(actual["vence"]) > ahora:
                    return False
            tx.set(
                ref,
                {
                    "componente": componente,
                    "evento_id": evento_id,
                    "estado": "en_curso",
                    "vence": (ahora + RECLAMACION).isoformat(),
                },
            )
            return True

        return tomar(self.db.transaction())

    def liberar(self, evento_id: str, componente: str) -> None:
        self._procesado(evento_id, componente).delete()

    # ─── Escrituras comunes ─────────────────────────────────────────────────

    def registrar_evento(self, uid: str | None, evento: BaseModel) -> None:
        """La bitácora del usuario; los eventos de sistema van a `sistema/presupuesto/eventos`."""
        destino = self._usuario(uid) if uid else self._global()
        destino.collection("eventos").document().set(
            evento.model_dump(mode="json", exclude_none=True)
        )

    def sumar_gasto(self, uid: str | None, usd: float) -> None:
        """Suma al gasto del día del usuario o, sin uid, al global."""
        from google.cloud import firestore

        destino = self._usuario(uid) if uid else self._global()
        destino.set({"gasto_usd_hoy": firestore.Increment(usd)}, merge=True)

    def guardar_propuesta(self, uid: str, propuesta_id: str, propuesta: BaseModel) -> None:
        self._usuario(uid).collection("propuestas").document(propuesta_id).set(
            propuesta.model_dump(mode="json", exclude_none=True)
        )

    def resolver_propuesta(self, uid: str, propuesta_id: str, estado: str) -> None:
        self._usuario(uid).collection("propuestas").document(propuesta_id).update(
            {"estado": estado, "resuelta_en": datetime.now(UTC).isoformat()}
        )

    def marcar_obsoleta(self, uid: str, propuesta_id: str) -> None:
        self._usuario(uid).collection("propuestas").document(propuesta_id).update(
            {"estado": "obsoleta"}
        )
