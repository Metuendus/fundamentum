import "server-only";
import { applicationDefault, getApp, getApps, initializeApp, type App } from "firebase-admin/app";

/** Una app de firebase-admin por proyecto: el central (lista) y el de cada app (cuentas). */
export function appDe(proyecto: string): App {
  if (getApps().some((a) => a.name === proyecto)) return getApp(proyecto);
  return initializeApp({ projectId: proyecto, credential: applicationDefault() }, proyecto);
}
