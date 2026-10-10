# Fundamentum

Chasis compartido de **Iterum**, **Vocatio** y **Domi**. Como en la industria automotriz: un chasis
estándar y, encima, varios modelos que no se ven iguales. Aquí vive lo que todas las apps necesitan
y no las diferencia: la capa de modelos, la forma de usar ADK, la medición, los eventos, las
evaluaciones y el design system. Cada app conserva sus agentes, su dominio y su marca.

## Estado

| Pieza | Paquete | Estado |
|---|---|---|
| Registro tarea→modelo, precios, costo (también como SQL) | `python/fundamentum_modelos` | 0.4.0 · fase A |
| Llamadas de una vuelta, analítica, modelos ADK (Gemini y Claude), resultados | `python/fundamentum_adk` | 0.4.0 · fase A |
| Medición nativa: dataset del plugin de ADK y vistas de costo | `infra/modulos/medicion` | 0.2.0 · fase A |
| Proyecto propio: Artifact Registry y publicación | `infra/proyecto` | fase A |
| Esquemas base de eventos y propuestas, Despachador, registro de Firestore | `python/fundamentum_eventos` | 0.4.0 · fase B |
| Runner de evals con gates de costo y latencia | `python/fundamentum_evals` | fase D |
| Tokens (base MiniMax + temas) y UI | `ts/` | fase E |

Plan completo y razones: [`docs/plan.md`](docs/plan.md). Contrato de medición:
[`docs/medicion.md`](docs/medicion.md). Cómo lo adopta cada app: [`docs/adopcion.md`](docs/adopcion.md).

## Desarrollo

```bash
uv sync --all-packages
uv run ruff check . && uv run ruff format --check . && uv run pytest -q
terraform fmt -check -recursive infra   # el validate de cada módulo corre en CI (cloudbuild-pr.yaml)
```

## Reglas

- Entra solo lo que ya usan dos apps, o lo que es estándar obligatorio (medición, IA).
- Obligatorio en las tres apps; lo compartido nunca se reimplementa en una app.
- Las apps fijan versión por etiqueta de git; nada de submódulos ni de `main`.
- Los esquemas base viven aquí; cada app los extiende en su `packages/schemas`.
- El chasis nunca bloquea un release candidate: si una app necesita algo urgente, lo hace local y
  luego lo sube.
