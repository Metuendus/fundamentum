# Plan · Fundamentum: chasis compartido para Iterum, Vocatio y Domi

## Contexto

Tres PoC agent-native (Iterum, Vocatio, Domi) validan el desarrollo agent-native y el modelo AaaS.
Hoy cada app resolvió por su cuenta lo mismo:

- **IA:** Iterum usa ADK 2.10 en Agent Runtime; Vocatio usa `google-genai` directo; Domi aún no llama
  a modelos.
- **Medición:** Iterum no calcula costo y `apps/web/src/lib/concierge/usage.ts:6-8` no ve a los
  especialistas; Vocatio guarda `Evento` con costo solo en Firestore; Domi no tiene nada.
- **Esquemas duplicados:** `Evento`, `Propuesta` y `Fuente` están en Vocatio y en Domi, y el
  Despachador de Domi es copia del de Vocatio.
- **Frontend:** varios design systems en Claude Design y componentes repetidos (Button, IconButton,
  ChipOrigen/SourceChip, Esqueleto/Skeleton, BarraInferior/BottomNav, PilaTarjetas/SwipeDeck, el
  semáforo FitBand/ChipScore/FeasibilityBadge y la tarjeta de propuesta). En tokens: Iterum 129,
  Vocatio 108, Domi 105, y solo 34 nombres comunes a las tres.

**Decisiones ya tomadas por el usuario:**
- Todo en GCP. Los modelos se consumen solo vía Model Garden, **Gemini y Anthropic**; modelos locales
  en fases posteriores.
- Ningún tercero recibe datos de usuario. Jev queda descartado.
- Repos separados más un repo nuevo con lo reutilizado de front y back.
- Homologar el uso de IA con ADK y Gemini Enterprise Agent Platform.
- Medición en las tres apps.
- Un solo design system **basado en MiniMax**, con prioridad en la **fidelidad al handoff**.
- Resultados por app: Iterum y Vocatio ya definidos; **Domi = visitas agendadas**.
- Vocatio M0 dura semanas.
- Alex (socio comercial y de marketing) recibe un tablero de Looker Studio cuando haga falta.

Analogía guía: un chasis estándar, varios modelos de auto.

## Repo `fundamentum`

```
fundamentum/
├─ python/   (uv workspace → Artifact Registry PyPI privado, semver)
│  ├─ fundamentum_modelos   registro tarea→modelo (Gemini y Claude vía Model Garden), precios, costo_usd
│  ├─ fundamentum_adk       plugins ADK: telemetría+costo, presupuesto, guardrails;
│  │                        fábrica de LlmAgent (endpoint global, reintentos 429, caché de contexto)
│  ├─ fundamentum_eventos   Evento, EventoBus, Despachador, Propuesta base, Fuente, usuario_interno
│  └─ fundamentum_evals     runner sobre adk eval + gates de calidad, costo y latencia
├─ ts/       (npm workspace → Artifact Registry npm privado)
│  ├─ @fundamentum/schemas    tipos generados de los esquemas base
│  ├─ @fundamentum/tokens     base MiniMax + capa semántica + temas iterum/vocatio/domi
│  ├─ @fundamentum/ui         primitivas + componentes de dominio en CSS Modules
│  └─ @fundamentum/telemetria eventos de producto desde la web
├─ infra/    módulos Terraform: topic eventos, dataset BigQuery + vistas de costo, sink, alertas
└─ plantillas/ CLAUDE.md base, cloudbuild de PR y de evals
```

**Reglas del repo:**
- Entra solo lo que ya usan dos apps, o lo que es estándar obligatorio (medición, IA).
- Las apps fijan versión.
- Los esquemas base viven aquí y cada `packages/schemas` los extiende.
- El chasis nunca bloquea un RC.

**Código que se reutiliza como punto de partida:**
- `vocatio/agents/vocatio_agents/config.py`: `costo_usd()` y `PRECIOS_USD_POR_MILLON`. Ya coincide
  con la tarifa oficial estándar de Gemini; hay que agregar los modelos Claude con precio verificado.
- `vocatio/agents/vocatio_agents/despachador.py` y `domi/agents/domi_agents/despachador.py` (aporta
  `CONSUMEN_GLOBAL`).
- `vocatio/agents/vocatio_agents/reintento.py`, `registro_firestore.py` y `vertex.py`.
- `iterum/agents/iterum_agents/config.py`: `gemini()` y `RETRY`, como base de la fábrica.
- `iterum/cloudbuild-evals.yaml` e `iterum/agents/evals/`, como base del runner.
- `vocatio/packages/schemas/scripts`: el generador Pydantic→TS.

## IA homologada con ADK 2.x y Agent Platform

**Estándar:**
- Todo agente es ADK Python 2.x (última versión: 2.11.0).
- Las llamadas de una sola vuelta son `LlmAgent` con `output_schema`.
- Los pipelines de Vocatio y Domi corren en Cloud Run con Pub/Sub y ejecutan un `Runner` de ADK con
  los plugins del chasis. Agent Runtime queda solo para agentes conversacionales.
- Guardrails como **Plugins**, no callbacks, que es lo que recomienda ADK. Iterum #75 se reescribe así.
- **Multiproveedor:** el registro mapea cada tarea a cualquier modelo de Model Garden (Gemini o
  Claude). Cambiar de modelo es configuración, pero **solo pasa el gate de evals de esa tarea**. ADK
  advierte que `output_schema` junto con herramientas es confiable en Gemini 3 y que en otros modelos
  cae a `set_model_response`, que "may not work reliably". Por eso Claude entra primero en tareas de
  redacción sin herramientas, como Scriba, que es justo donde el spec de Vocatio ya lo contempla.
- **Tokens:** plugin BigQuery Agent Analytics.
- **Costo:** una vista en BigQuery cruza los tokens con la tabla de precios y se concilia con el
  export de facturación. Iterum ya tiene ese export desde el 8 de octubre.
- **Trazas:** Cloud Trace vía OpenTelemetry (`--otel_to_cloud`).
- **Evals:** `adk eval` con trayectoria, rúbricas, `hallucinations_v1`, `token_usage_v1` e
  `invocation_duration_v1`.

**Antes de la fase A:** verificar el precio de Claude en la página de precios de Agent Platform y
confirmar que el export de facturación separa el SKU por modelo. Hoy eso no está confirmado.

## Medición en las tres apps

**Contrato común:**
- `llamada_modelo`: lo emite el plugin.
- `resultado_entregado`: lo emite la app.
- `usuario_interno`: va en todo evento.
- Destino: un dataset de BigQuery por proyecto, con las mismas vistas. Looker Studio para Alex
  combina las tres fuentes cuando se necesite.

**Iterum:**
- Plugin en el Concierge y en los especialistas, más la vista de costo.
- `resultado_entregado` con la definición que ya existe.
- Topes de costo.
- Issues relacionados: #70, #77, #82, #83.

**Vocatio:**
- Sink del `Evento` actual hacia BigQuery desde la fase A, porque M0 dura semanas.
- `usuario_interno` (#19); el reporte de #20 se calcula sobre BigQuery; alertas (#26); cuota (#27).

**Domi:**
- Resultado = **visita agendada**. La regla "Nada sale de la app" impide que la app agende, así que
  la visita es un evento que el usuario marca con un botón ("Agendé visita") sobre un inmueble
  guardado. Las métricas son costo por visita agendada y tiempo de primer uso a primera visita.
- Hoy Domi tiene 0 issues: crear su backlog.
- Corregir: el tope global no cubre `inmueble_actualizado`, `TOPE_LLAMADAS_DIA` no se aplica en
  ningún lado, y Speculator puede rebasar el tope global.

## Design system único, basado en MiniMax

**Base:** MiniMax. Es la base que ya declara el `tokens.css` de Iterum, así que Iterum es la
referencia y la que menos cambia. Se archivan "Vocatio Design System" y el "Design System" por
defecto. EPA Digital DS se queda aparte, porque es otro negocio.

**Capas:**
1. Primitivos MiniMax: escala tipográfica, espaciado, radios, sombras, foco y objetivos de 44 px.
2. Semánticos `--fu-*`, en claro y `[data-theme="dark"]`.
3. Tema por app (`[data-app]`): paleta, familia tipográfica y personalidad de radio.
4. Extensiones de dominio en cada app: categorías de viaje, firmas de agente, chips de score.

**Fidelidad al handoff manda, así que el diseño va primero:**
1. En Claude Design se rehacen los temas de Vocatio y Domi sobre la base MiniMax.
2. Se regenera el handoff de cada uno.
3. Hasta entonces se toca el código.

Las reglas "tokens.css es copia literal del handoff" siguen vigentes: el handoff nuevo sale del DS
único.

**Stack:** CSS Modules. Tailwind y shadcn se descartan por ahora, porque la fidelidad al handoff pesa
más que la velocidad de generación y las tres `CLAUDE.md` ya lo justifican.

**Migración:** con alias temporales (`--vo-ink: var(--fu-ink)`) para no tocar todas las pantallas de
golpe. Nunca antes del RC de Iterum.

## Fases

| Fase | Cuándo | Entregable verificable |
|---|---|---|
| A · Medir | Semanas 1–2, antes de la ronda 0 | Repo, `fundamentum_modelos` con Gemini y Claude, y plugin de costo. Iterum lo adopta y Vocatio tiene su sink. Costo por mensaje y por viaje visible en BigQuery |
| B · Domi sobre el chasis | Semanas 3–5 | `fundamentum_eventos`, backlog de Domi y evento "visita agendada". F2.2 Iudex con costo y traza desde la primera llamada |
| C · Vocatio a ADK | Al cerrar M0 | Memoria y Scriba como `LlmAgent`. Las evals de F3.2 quedan iguales o mejores. Primera evaluación de Claude contra Gemini en Scriba |
| D · Guardrails y evals compartidos | Después del RC de Iterum | Plugins de guardrails y gate de costo y latencia en el CI de las tres apps |
| E · Design system único | Diseño en paralelo con B; código después del RC | DS MiniMax con tres temas en Claude Design y handoffs regenerados. `@fundamentum/tokens` con alias. La tarjeta de propuesta sale del chasis en dos apps |
| F · Paquete para Alex | Al cerrar la ronda 1 de Iterum y la beta de Vocatio | Looker Studio con costo por resultado (viaje, aplicación, visita agendada), aceptación y retención |

## Verificación

- **Chasis:** pasan `uv run ruff check . && uv run pytest -q` y `npm run typecheck && npm test`.
  Una versión de prueba publicada en Artifact Registry se instala desde Iterum.
- **Medición:** una conversación real del Concierge aparece en BigQuery con los tokens del Concierge y
  de cada especialista. El costo de la vista concilia ±10 % con el export de facturación del día.
- **Multiproveedor:** la misma tarea corre con Gemini y con Claude solo cambiando el registro, y su
  eval decide cuál queda.
- **Domi:**
  - una prueba del Despachador que corta al llegar al tope global con `inmueble_actualizado`;
  - el evento "visita agendada" aparece en BigQuery.
- **Design system:**
  - cada app renderiza con su tema y funciona `[data-theme="dark"]`;
  - axe sin errores;
  - comparación a 1280 px contra el handoff regenerado.
- **Cada app:** su verificación de `CLAUDE.md` sigue en verde después de adoptar el chasis.

## Primer paso al aprobar

1. Crear el repo `fundamentum` con el esqueleto de la fase A.
2. Abrir los issues de la fase A en los tres repos.
3. Crear el backlog inicial de Domi, empezando por "visita agendada".

En Iterum no se toca nada que bloquee el canario del 16 de octubre.
