# Cambios

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
