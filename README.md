# Fundamentum

Chasis compartido de **Iterum**, **Vocatio** y **Domi**. Como en la industria automotriz: un chasis
estándar y, encima, varios modelos que no se ven iguales. Aquí vive lo que todas las apps necesitan
y no las diferencia: la capa de modelos, la forma de usar ADK, la medición, los eventos, las
evaluaciones y el design system. Cada app conserva sus agentes, su dominio y su marca.

## Estado

| Pieza | Paquete | Estado |
|---|---|---|
| Registro tarea→modelo, precios, costo | `python/fundamentum_modelos` | 0.1.0 · fase A |
| Plugin de medición, modelos ADK (Gemini y Claude) | `python/fundamentum_adk` | 0.1.0 · fase A |
| Dataset, sink y vistas de medición | `infra/modulos/medicion` | fase A |
| Eventos, Despachador, Propuesta, Fuente | `python/fundamentum_eventos` | fase B |
| Runner de evals con gates de costo y latencia | `python/fundamentum_evals` | fase D |
| Tokens (base MiniMax + temas) y UI | `ts/` | fase E |

Plan completo y razones: [`docs/plan.md`](docs/plan.md). Contrato de medición:
[`docs/medicion.md`](docs/medicion.md). Cómo lo adopta cada app: [`docs/adopcion.md`](docs/adopcion.md).

## Desarrollo

```bash
uv sync --all-packages
uv run ruff check . && uv run ruff format --check . && uv run pytest -q
cd infra/modulos/medicion && terraform fmt -check && terraform init -backend=false && terraform validate
```

## Reglas

- Entra solo lo que ya usan dos apps, o lo que es estándar obligatorio (medición, IA).
- Las apps fijan versión; nada de submódulos ni de `main`.
- Los esquemas base viven aquí; cada app los extiende en su `packages/schemas`.
- El chasis nunca bloquea un release candidate: si una app necesita algo urgente, lo hace local y
  luego lo sube.
