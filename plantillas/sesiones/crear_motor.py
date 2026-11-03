"""Crea el motor de Agent Platform que guarda las sesiones de una app (una vez por app).

Es un motor sin código: no corre ningún agente ni cobra cómputo; solo contiene las sesiones que
`sesiones_agent_platform(proyecto, motor)` lee y escribe desde Cloud Run. Iterum no lo necesita:
su Concierge ya corre en Agent Runtime y usa las sesiones de su propio motor.

    uv run --with "fundamentum-adk[agentplatform]" python crear_motor.py <proyecto> <app>

Imprime el nombre del recurso; su id (lo último) va en la variable `<APP>_SESIONES_MOTOR` del
servicio. La cuenta del servicio necesita `roles/aiplatform.user`.
"""

import sys

import agentplatform


def main(proyecto: str, app: str, ubicacion: str = "us-central1") -> None:
    cliente = agentplatform.Client(project=proyecto, location=ubicacion)
    motor = cliente.runtimes.create(
        config={
            "display_name": f"{app}-sesiones",
            "description": f"Sesiones e historial de los agentes de {app} (Fundamentum 1.4.0).",
        }
    )
    print(motor.api_resource.name)


if __name__ == "__main__":
    main(*sys.argv[1:])
