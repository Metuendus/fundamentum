# Cambios

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
