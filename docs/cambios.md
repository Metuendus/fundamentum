# Cambios

## 1.1.0 · 2026-10-26 · tope por intento a Gemini

- `modelo_adk` devuelve `GeminiConEspera`: cada intento lleva un tope de `ESPERA_MS` (90 s), también
  en el servidor por `X-Server-Timeout`, y un corte antes de la primera respuesta se reintenta hasta
  `INTENTOS_ESPERA` (3) veces. google-genai no reintenta el corte de aiohttp por su cuenta.
- Por qué: en Iterum una llamada a `gemini-3.8-flash` tardó 7,6 min y el turno se perdió (iterum#127).
- Una petición que ya trae su propio `http_options.timeout` lo conserva.
- Los cuatro paquetes van en 1.1.0, porque la etiqueta y las versiones deben coincidir para publicar.

## 1.0.0 · 2026-10-10 · backend completo

Con esta versión se reanudan las apps: cada una adopta el chasis completo antes de cualquier
rebanada nueva.

- **Guardrails como Plugins** (`fundamentum-adk`, fase D):
  - `PluginAlcance`: antes de cada herramienta exige la identidad en la sesión, bloquea argumentos
    que nombren otro recurso y pregunta a la app por la pertenencia (iterum#75).
  - `PluginPresupuesto`: corta antes del modelo, con un mensaje claro, si la persona o el recurso
    agotó su tope.
  - `como_dato`: delimita el texto externo y neutraliza cierres falsos.
  - `redactar`, `FiltroDatosPersonales` e `instalar_filtro`: nada de datos personales en los logs
    (iterum#78).
- **`fundamentum-evals`:** corre `adk eval` y aplica un gate que falla si `token_usage_v1`,
  `inference_call_count_v1` o `invocation_duration_v1` pasan del doble de la línea base del repo.
  Plantilla en `plantillas/cloudbuild-evals.yaml`.
- `infra/modulos/medicion`: las vistas `resultados` y `costo_por_resultado` se activan aparte, con
  `crear_vistas_resultados = true`, porque el sink crea su tabla hasta el primer
  `resultado_entregado` y BigQuery rechaza una vista sobre un comodín sin tablas (lo encontró el primer
  `apply` de Iterum).
- Los cuatro paquetes van en 1.0.0. Las versiones 0.3 y 0.4 quedan como historia y no se etiquetan.

## 0.4.0 · 2026-10-10

- **`fundamentum-eventos` (fase B):**
  - Esquemas base que cada app extiende en su `packages/schemas`: `EventoBusBase`, `EventoBase`
    (con `UsoModelo` y `de_llamada`), `PropuestaBase`, `ClasePropuesta` y `EstadoPropuesta`.
  - `Despachador`, que une los de Vocatio y Domi: idempotencia por `evento_id + componente`,
    presupuesto por usuario y tope global para eventos de sistema. Falla en voz alta si hay tipos
    con tope global y el registro no lo implementa.
  - `RegistroFirestore` (extra `firestore`): reclamación atómica, presupuestos, bitácora y
    propuestas. Las colecciones se pueden configurar.
  - `con_reintentos` para servicios. Los modelos los reintenta ADK.
- `fundamentum-adk` y `fundamentum-modelos` suben a 0.4.0, sin cambios de API.

## 0.3.0 · 2026-10-10

- `fundamentum-adk`:
  - `agente_unico`, `llamar` y `llamar_sync`: llamadas de una sola vuelta por ADK, sin herramientas
    ni historial, con salida por esquema. Comparten los plugins de la app sin cerrarlos y devuelven
    texto, uso por respuesta y costo.
  - `analitica(app)`: el plugin oficial de BigQuery con la configuración privada.
  - `modelo_adk` acepta `proyecto` y `credenciales` para Gemini.
  - **Se borra `PluginMedicion`**, como se anunció en 0.2.0.
  - Depende de `google-adk[bigquery-analytics]`.
- `fundamentum-modelos`: `Uso` se puede sumar.
- Python 3.11 o 3.12 (Iterum corre en 3.11).
- Adopción por git y etiqueta, sin Artifact Registry: el repo es público. Los paquetes se siguen
  publicando al etiquetar.

## 0.2.0 · 2026-10-10

- **Medición nativa de ADK.** `infra/modulos/medicion` ya no lleva sink de `llamada_modelo`: crea el
  dataset `agentes` donde escribe `BigQueryAgentAnalyticsPlugin`, da permiso a las cuentas de
  `escritores` y agrega las vistas `costo_llamadas`, `costo_diario`, `resultados` y
  `costo_por_resultado`. Variable nueva `usuarios_internos` (uids). El sink queda solo para
  `resultado_entregado`. Ver `docs/decisiones.md`, decisión 1.
- `fundamentum-modelos`: `sql.precios_sql()` genera `vistas/precios.sql` desde `PRECIOS`; una prueba
  falla si se desfasan.
- `fundamentum-adk`: `PluginMedicion` queda obsoleto (avisa con `DeprecationWarning`) y se borra en
  0.3. `emitir_resultado` y `modelo_adk` se quedan.
- `infra/modulos/medicion/tests`: las vistas parsean como GoogleSQL (sqlglot) y `costo_llamadas` se
  ejecuta en DuckDB con eventos de ejemplo. `terraform validate` no revisa el SQL.
- Regla nueva: ninguna llamada a un modelo fuera de ADK.

## Sin versión · 2026-10-09

- `infra/proyecto`: proyecto propio del chasis (`bootstrap.sh` + Terraform) con repositorios de
  Artifact Registry para Python y npm, cuenta de servicio de publicación, trigger por etiqueta y
  presupuesto.
- `cloudbuild-publicar.yaml`: publica los paquetes al etiquetar `vX.Y.Z`, después de comprobar que la
  etiqueta coincide con las versiones.
- `fundamentum-adk` acota su dependencia a `fundamentum-modelos>=0.1,<0.2`.

## 0.1.0 · 2026-10-09

- `fundamentum-modelos`: precios de Gemini 3.8 Flash, 3.5 Flash-Lite y Claude Haiku, Sonnet y Opus
  5.5 (Model Garden, endpoint global, consultados el 2026-10-09); `Uso`, `costo_usd` y `Registro`.
- `fundamentum-adk`: `PluginMedicion`, `emitir_resultado` y `modelo_adk` (Gemini y Claude).
- `infra/modulos/medicion`: dataset, sink y vistas de costo por resultado.
