# Adopción por app (fase A)

## Instalar el chasis

Los paquetes se publican en Artifact Registry, en el proyecto propio del chasis
(`infra/proyecto`). Cada app declara el índice y fija la versión:

```toml
# pyproject.toml del paquete de la app que usa el chasis
[project]
dependencies = ["fundamentum-adk==0.1.0"]

[[tool.uv.index]]
name = "fundamentum"
url = "https://us-central1-python.pkg.dev/fundamentum-mx/fundamentum-py/simple/"
explicit = true

[tool.uv.sources]
fundamentum-adk = { index = "fundamentum" }
fundamentum-modelos = { index = "fundamentum" }
```

Autenticación:
- **En local:** `gcloud auth application-default login` y
  `uv tool install keyring --with keyrings.google-artifactregistry-auth`; luego
  `UV_KEYRING_PROVIDER=subprocess uv sync`.
- **En Cloud Build:** la cuenta de Cloud Build de la app va en `lectores`. El paso de instalación
  usa `UV_INDEX_FUNDAMENTUM_USERNAME=oauth2accesstoken` y
  `UV_INDEX_FUNDAMENTUM_PASSWORD=$(gcloud auth print-access-token)`.

## Iterum (Agent Runtime, ADK 2.10)

1. Agregar `fundamentum-adk` a `agents/pyproject.toml`, desde Artifact Registry y con versión fija.
2. Registrar el plugin en el `App` que despliega `deploy.py`:
   ```python
   from fundamentum_adk import PluginMedicion

   app = App(name="iterum", root_agent=concierge, plugins=[PluginMedicion(app="iterum")])
   ```
   Los especialistas son `AgentTool` y heredan el plugin. Con eso se cubre el hueco de
   `apps/web/src/lib/concierge/usage.ts:6-8`.
3. Poner `state["usuario_interno"] = True` en las sesiones del fundador al crearlas en el BFF.
4. Emitir `viaje_planeado` desde el servidor cuando el viaje cumpla la definición del roadmap.
5. Aplicar `infra/modulos/medicion` con `project_id = travel-planner-509322`. Después del primer
   registro, aplicar de nuevo con `crear_vistas = true`.
6. Más adelante, `config.py` usa `modelo_adk()` y un `Registro("iterum", {...})`.

## Vocatio (Cloud Run, google-genai directo; pasa a ADK en la fase C)

1. Mientras dure M0: el `Evento` actual se emite también como línea JSON `llamada_modelo`, con los
   mismos campos, desde `memoria.py` y `scriba.py`. El sink lo recoge sin cambiar Firestore.
2. `usuario_cero` (#19) se traduce a `usuario_interno` en la línea.
3. Aplicar `infra/modulos/medicion` en `vocatio-mx`.

## Domi (sin llamadas todavía)

1. F2.2 Iudex nace como `LlmAgent` con `modelo_adk(registro.modelo("iudex.ponderacion"))` y un
   `Runner` con `PluginMedicion(app="domi")`.
2. Agregar el botón "Agendé visita", que emite `resultado_entregado` con `visita_agendada`.
3. Aplicar `infra/modulos/medicion` en el proyecto de Domi cuando exista (F0.2).
