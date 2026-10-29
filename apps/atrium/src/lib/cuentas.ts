import "server-only";
import { getAuth } from "firebase-admin/auth";
import { APPS, type AppId } from "./acceso";
import { enNube } from "./config";
import { appDe } from "./firebase";

export type Cuenta = {
  uid: string;
  correo: string;
  proveedores: string[];
  alta: string;
  ultimoAcceso: string | null;
  deshabilitada: boolean;
};

const proyecto = (app: AppId) => APPS.find((a) => a.id === app)!.proyecto;

const DEMO: Record<AppId, Cuenta[]> = {
  iterum: [
    { uid: "d1", correo: "demo@atrium.local", proveedores: ["google.com"], alta: "2026-09-22T00:00:00Z", ultimoAcceso: "2026-10-29T00:00:00Z", deshabilitada: false },
    { uid: "d2", correo: "alguien@ejemplo.com", proveedores: ["google.com"], alta: "2026-10-01T00:00:00Z", ultimoAcceso: "2026-10-02T00:00:00Z", deshabilitada: false },
  ],
  domi: [],
  vocatio: [],
};

/** Cuentas de Firebase Auth de una app, de la más reciente a la más antigua por último acceso. */
export async function cuentas(app: AppId): Promise<Cuenta[]> {
  if (!enNube()) return DEMO[app];
  const auth = getAuth(appDe(proyecto(app)));
  const todas: Cuenta[] = [];
  let token: string | undefined;
  do {
    const pagina = await auth.listUsers(1000, token);
    for (const u of pagina.users) {
      todas.push({
        uid: u.uid,
        correo: (u.email ?? "").toLowerCase(),
        proveedores: u.providerData.map((p) => p.providerId),
        alta: new Date(u.metadata.creationTime).toISOString(),
        ultimoAcceso: u.metadata.lastSignInTime ? new Date(u.metadata.lastSignInTime).toISOString() : null,
        deshabilitada: u.disabled,
      });
    }
    token = pagina.pageToken;
  } while (token);
  return todas.sort((a, b) => (b.ultimoAcceso ?? "").localeCompare(a.ultimoAcceso ?? ""));
}

/**
 * Cierra las sesiones de una persona en una app. El portero no corre al renovar el token, así que
 * sin esto quien pierde el permiso seguiría dentro. Sin cuenta en esa app no hay nada que cerrar.
 */
export async function cerrarSesiones(correo: string, app: AppId): Promise<boolean> {
  if (!enNube()) return false;
  const auth = getAuth(appDe(proyecto(app)));
  try {
    const u = await auth.getUserByEmail(correo);
    await auth.revokeRefreshTokens(u.uid);
    return true;
  } catch (e) {
    if ((e as { code?: string }).code === "auth/user-not-found") return false;
    throw e;
  }
}
