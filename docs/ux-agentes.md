# UX de agentes · lista común de Iterum, Domi y Vocatio

Cada app la aplica con sus componentes, sus tokens y su handoff de diseño; el chasis no trae UI. Una
pantalla con agente no se da por terminada hasta cumplir esta lista y pasar axe (WCAG 2.1 AA).

## 1. Una voz y trabajo visible

- Habla un solo agente con el nombre de la app (el Concierge en Iterum, "Domi", "Vocatio"). Los
  especialistas no escriben en el chat: aparecen como **filas de trabajo** dentro de la respuesta
  ("Buscando hoteles…", "Revisando tu Expediente…"), con estado en curso, hecho o error.
- Las filas salen de las llamadas a herramientas (`LlamadaHerramienta` en vivo, `Mensaje.filas` en
  el historial); cada app traduce el nombre técnico a una frase. Nunca se muestran argumentos crudos ni ids.

## 2. Respuesta en flujo y control

- El texto llega en trozos desde la primera palabra; mientras no hay texto, se ve la fila activa o un
  indicador de "pensando" con texto, no solo una animación.
- **Detener** siempre visible mientras responde (botón con texto o etiqueta accesible). Detener
  conserva en pantalla lo ya escrito; en el historial ese turno queda como "sin respuesta".
- El campo de texto no se bloquea mientras responde: se puede escribir el siguiente mensaje.

## 3. Errores y límites

- Un error dice qué pasó en lenguaje llano y ofrece **Reintentar**, sin borrar lo que la persona
  escribió. Nada de códigos HTTP ni trazas en pantalla.
- El límite diario (`PluginPresupuesto`) se dice claro: qué se agotó, que lo guardado sigue ahí y
  cuándo vuelve.
- Si el agente no encontró algo (un lugar, un precio, un dato del Expediente), lo dice; nunca rellena.

## 4. Proponer, no imponer

- Todo cambio es una **Propuesta** con Aceptar · Editar · Rechazar y antes/después legible. Dinero,
  compromisos y envíos requieren aprobación explícita. Las acciones automáticas tienen Deshacer.
- La respuesta enlaza sus propuestas y tarjetas (`Mensaje.enlaces`), así se pueden abrir desde el
  historial días después.

## 5. Procedencia

- Toda cifra o dato externo muestra fuente y fecha de consulta (chip de origen). Los datos que puso
  la persona se marcan como suyos.

## 6. Historial en cualquier dispositivo

- Al abrir el chat se ve la **última conversación** del recurso (viaje, perfil) donde quedó, leída
  de las sesiones de Agent Platform (`Historial`): lo escrito en el celular aparece en la compu al
  abrir o volver a la pestaña.
- **Conversaciones recientes**: lista con título (primer mensaje), fecha relativa y última línea;
  abrir una la continúa con su sesión.
- **Nueva conversación** no borra la anterior: queda en recientes.
- **Borrar conversación** con confirmación; borra la sesión del agente con todos sus mensajes.
- Un turno que no terminó (cerraste la pestaña) se ve como "sin respuesta" con Reintentar.

## 7. Arranque

- El chat vacío ofrece de 2 a 4 **sugerencias** concretas del contexto ("¿Qué falta reservar del
  día 3?") y una línea de qué puede y qué no puede hacer el agente.

## 8. Accesibilidad

- La conversación es `role="log"` con `aria-live="polite"`; las filas de trabajo anuncian su cambio
  de estado una vez, no cada trozo.
- Foco visible en todo; tras enviar, el foco se queda en el campo; Escape detiene o cierra según el
  contexto. Objetivos táctiles de al menos 44 px en móvil.
- Semáforos y estados con ícono de forma distinta y texto, nunca solo color.
- Markdown de la respuesta renderizado con encabezados y listas reales; los enlaces externos dicen
  que abren otro sitio.

## 9. Privacidad y confianza

- El aviso de privacidad dice que las conversaciones se guardan, cuánto tiempo (365 días por
  omisión) y cómo borrarlas. El borrado de cuenta incluye historial y sesiones.
- Nada de datos personales en logs ni en la medición (`analitica` sin contenido).
- El texto externo (correos, vacantes, anuncios) entra al prompt con `como_dato`.

## 10. Trazabilidad

- Cada turno guarda su `trace_id` (en el `Evento` y en `Mensaje.trace_id`). Un error reportado se
  sigue hasta su traza en Cloud Trace (`enlace_traza`) sin pedirle nada a la persona.
