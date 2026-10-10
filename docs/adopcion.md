# Adopción por app

El chasis es **obligatorio** en Iterum, Vocatio y Domi (decisión del 10 de octubre de 2026). Lo
compartido se usa desde aquí y nunca se reimplementa en la app; si falta algo, se agrega primero al
chasis.

## 1. Instalar, fijado por etiqueta

El repo es público: cada app lo instala desde git, con la etiqueta de la versión. No hace falta
Artifact Registry, credenciales ni pasos extra en CI ni en Agent Runtime.

```toml
# pyproject.toml del paquete de agentes
[project]
dependencies = [
  "fundamentum-adk==1.0.0",
  "fundamentum-modelos==1.0.0",
  "fundamentum-eventos[firestore]==1.0.0",
]

[dependency-groups]
dev = ["fundamentum-evals==1.0.0"]

[tool.uv.sources]
fundamentum-adk = { git = "https://github.com/Metuendus/fundamentum", tag = "v1.0.0", subdirectory = "python/fundamentum_adk" }
fundamentum-modelos = { git = "https://github.com/Metuendus/fundamentum", tag = "v1.0.0", subdirectory = "python/fundamentum_modelos" }
fundamentum-eventos = { git = "https://github.com/Metuendus/fundamentum", tag = "v1.0.0", subdirectory = "python/fundamentum_eventos" }
fundamentum-evals = { git = "https://github.com/Metuendus/fundamentum", tag = "v1.0.0", subdirectory = "python/fundamentum_evals" }
```

Con pip (Iterum, Agent Runtime):
`fundamentum-adk @ git+https://github.com/Metuendus/fundamentum@v1.0.0#subdirectory=python/fundamentum_adk`
y lo mismo para `fundamentum-modelos`.

Para subir de versión se cambian juntas la versión y las etiquetas, y se corre `uv lock`.

## 2. Toda llamada a un modelo pasa por ADK

- **Conversación** (Iterum): `App(name, root_agent, plugins=analitica("iterum"))`. En Agent Runtime,
  `AdkApp(app=app, enable_tracing=True)` para Cloud Trace.
- **Una sola vuelta** (extraer, clasificar, redactar):

```python
from fundamentum_adk import agente_unico, analitica, llamar_sync, modelo_adk

PLUGINS = analitica("vocatio")  # una vez por proceso; [] sin VOCATIO_ANALITICA_DATASET

agente = agente_unico(
    "memoria",
    modelo_adk("gemini-3.8-flash", proyecto="vocatio-mx", credenciales=cred),
    esquema=ExtraccionCv,  # Pydantic, types.Schema o dict de Gemini
    instruccion=INSTRUCCION,
    temperatura=0.1,
)
r = llamar_sync(agente, [parte_pdf, "Extrae el CV."], plugins=PLUGINS, usuario=uid, app="vocatio")
r.texto, r.uso, r.costo_usd()  # el costo va al Evento y al presupuesto del Despachador
```

`llamar` (async) es lo mismo dentro de una herramienta. Ahí se pasan los plugins del `App`, para que
la llamada quede medida.

Nada de `genai.Client(...).models.generate_content`.

## 3. Eventos, propuestas y Despachador

```python
# packages/schemas de la app: extender, no copiar
from fundamentum_eventos import EventoBase, EventoBusBase, PropuestaBase


class EventoBus(EventoBusBase):
    tipo: TipoEvento  # Literal de la app
    payload: dict = {}


class Evento(EventoBase):
    componente: Componente | None = None
    creado_en: datetime


# agents/: el Despachador común con los tipos que consumen modelo
from fundamentum_eventos import Despachador
from fundamentum_eventos.registro_firestore import RegistroFirestore

DESPACHADOR = Despachador(EventoBus, consumen_presupuesto={...}, consumen_global={...})
evento = DESPACHADOR.decodificar_push(cuerpo)
if DESPACHADOR.decidir(evento, "scriba", registro).decision == "procesar":
    ...

# Tras una llamada al modelo
registro.registrar_evento(
    uid, Evento(tipo="llamada_modelo", componente="scriba", creado_en=ahora, **Evento.de_llamada(r))
)
registro.sumar_gasto(uid, r.costo_usd())
```

## 4. Guardrails

Se registran una vez en el `App`, junto con `analitica`:

```python
from fundamentum_adk import PluginAlcance, PluginPresupuesto, analitica, instalar_filtro

instalar_filtro()  # nada de datos personales en los logs
plugins = [
    PluginAlcance(
        requeridas=("uid", "trip_id"), vinculos={"trip_id": "trip_id"}, verificar=es_miembro
    ),
    PluginPresupuesto(agotado=registro_agotado, clave_recurso="trip_id"),
    *analitica("iterum"),
]
app = App(name="iterum", root_agent=root_agent, plugins=plugins)
```

El texto externo entra al prompt con `como_dato(texto, "correo")`.

## 4b. Evals con gate de costo y latencia

`python -m fundamentum_evals <módulo> <carpeta> --runs 2 --linea-base evals/linea_base.json`. La
primera vez, y cuando un aumento sea a propósito, se agrega `--actualizar` y la línea base se revisa
en el PR. Plantilla: `plantillas/cloudbuild-evals.yaml`.

## 4c. Analítica

`analitica(app)` devuelve el plugin oficial de ADK con la configuración privada del chasis: sin
texto de la conversación y sin estado de la sesión (ver `medicion.md`). Lee
`<APP>_ANALITICA_DATASET` y `GOOGLE_CLOUD_PROJECT`, o los recibe como argumentos. La cuenta del
agente necesita `roles/cloudtrace.agent`; los permisos de BigQuery los da el módulo.

## 5. Módulo de Terraform

```hcl
module "medicion" {
  source            = "git::https://github.com/Metuendus/fundamentum.git//infra/modulos/medicion?ref=v1.0.0"
  project_id        = var.project_id
  escritores        = ["serviceAccount:${google_service_account.agentes.email}"]
  usuarios_internos = var.usuarios_internos
  crear_vistas      = var.medicion_vistas # true en un segundo apply, tras la primera llamada
}
```

## 6. Resultado entregado

Ver [`medicion.md`](medicion.md#resultado_entregado).

## Estado por app

Fundamentum 1.0 (backend) está listo. Cada app lo adopta completo antes de cualquier rebanada nueva:

| App | Adopción |
|---|---|
| Iterum | El lector (`documents.py`) y `analitica` desde el chasis; Python 3.11 ya es compatible |
| Vocatio | Memoria y Scriba con `agente_unico` y `llamar_sync`; `Evento`, `Propuesta` y Despachador de `fundamentum_eventos` |
| Domi | Iudex nace con `agente_unico`; Despachador de `fundamentum_eventos` (`consumen_global` para Interpres y Vicinus) |
