# Atrium

Panel privado de las apps: quién entra a Iterum, Domi y Vocatio mientras están en beta privada, y
más adelante cuánto se usa cada una. Escribe la lista que lee el portero de `fundamentum-acceso`.

## Qué hace

- **Apps:** el modo de cada una, `beta` (solo la lista) o `abierta` (cualquiera crea cuenta).
  Cambiarlo no requiere desplegar nada.
- **Solicitudes:** las que llegan desde la pantalla de beta privada de cada app. Aprobar da el
  permiso con origen `solicitud`.
- **Lista de acceso:** correos con su permiso por app (origen, alta, nota, vencimiento). Quitar un
  permiso también revoca los refresh tokens de esa persona en esa app; su token actual dura hasta
  una hora.
- **Cuentas por app:** las cuentas de Firebase Auth de cada proyecto, con último acceso y si están
  dentro o fuera de la lista.
- Cada cambio deja una fila en `bitacora` con quién lo hizo.

## Datos

Firestore de `josecarloscorona-web`, con los nombres de `fundamentum_acceso.modelos`:
`acceso/{correo}`, `apps/{app}`, `solicitudes/{id}` y `bitacora/{id}`. El modelo de TypeScript está
en `src/lib/acceso.ts`; si cambia uno, cambia el otro.

## Acceso

Cloud Run detrás de IAP, sin acceso público. La app además verifica la firma del encabezado
`x-goog-iap-jwt-assertion` contra `ATRIUM_IAP_AUDIENCE` y exige que el correo esté en
`ATRIUM_ADMINS`. Falla cerrado si falta cualquiera.

Permisos de la cuenta `atrium@josecarloscorona-web`:

| Dónde | Rol | Para qué |
| --- | --- | --- |
| josecarloscorona-web | `roles/datastore.user` | Leer y escribir la lista |
| travel-planner-509322, domi-mx, vocatio-mx | `roles/firebaseauth.admin` | Listar cuentas y revocar sesiones |

## Desarrollo

Fuera de Cloud Run corre en demostración, con datos en memoria y sin credenciales.

```bash
npm install
npm run dev                  # http://localhost:3000
npm run typecheck && npm run lint && npm test && npm run build
```

Despliegue: `apps/atrium/cloudbuild.yaml`. Se despliega desde `main`, aparte de las releases de los
paquetes.
