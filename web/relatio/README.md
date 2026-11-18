# @fundamentum/relatio

Botón flotante «Reportar un problema» para las apps. Arma el reporte (título opcional, qué pasa,
cuándo, información adicional, captura y aviso por correo) y lo envía a [Relatio](../../apps/relatio),
que crea el issue en el repo de la app.

## Instalar

Se fija por la release, como los paquetes de Python:

```json
"@fundamentum/relatio": "https://github.com/Metuendus/fundamentum/releases/download/v1.6.0/fundamentum-relatio-1.6.0.tgz"
```

## Usar

```tsx
"use client";
import { ReportarProblema } from "@fundamentum/relatio";
import "@fundamentum/relatio/estilos.css";

<ReportarProblema
  app="iterum"
  relatioUrl={process.env.NEXT_PUBLIC_RELATIO_URL!}
  obtenerToken={() => auth.currentUser?.getIdToken() ?? Promise.resolve(null)}
  correo={usuario?.email}
  version={process.env.NEXT_PUBLIC_VERSION}
  oculto={!usuario || enDemo}
/>
```

- Sin sesión o en `/demo`, pasa `oculto`: Relatio rechaza reportes sin ID token.
- La página se envía sin query ni fragmento (ahí viajan tokens de invitación).
- «Tomar captura» dibuja la pantalla desde el DOM, sin pedir permiso. Los iframes de otros orígenes
  (mapas) pueden salir en blanco; para eso está «Adjuntar archivo». Máximo 5 MB.

## Estilos

Cada app mapea las variables en el bloque de extensiones de su `tokens.css`:

| Variable | Para qué |
| --- | --- |
| `--fr-fondo`, `--fr-texto`, `--fr-texto-suave`, `--fr-borde` | Superficie del diálogo y campos |
| `--fr-acento`, `--fr-sobre-acento` | Botón flotante y botón principal |
| `--fr-error`, `--fr-foco`, `--fr-velo` | Errores, anillo de foco y fondo del modal |
| `--fr-radio`, `--fr-radio-control`, `--fr-fuente` | Forma y tipografía |
| `--fr-abajo`, `--fr-derecha`, `--fr-z` | Posición del botón (p. ej. sobre una barra inferior) |

Sin mapeo usa `Canvas`/`CanvasText`, que siguen el modo oscuro del sistema.

## Desarrollo

```bash
npm install && npm run typecheck && npm test && npm pack --dry-run
```
