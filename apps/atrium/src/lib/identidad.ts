import "server-only";
import { OAuth2Client } from "google-auth-library";
import { headers } from "next/headers";
import { normalizarCorreo } from "./acceso";
import { enNube, listaCorreos } from "./config";

export class SinAcceso extends Error {}

const cliente = new OAuth2Client();

/**
 * Quién administra. En la nube, Atrium va detrás de IAP: se verifica la firma del encabezado
 * `x-goog-iap-jwt-assertion` contra la audiencia del servicio y el correo debe estar en
 * `ATRIUM_ADMINS`. Falla cerrado si falta cualquiera de las dos variables.
 */
export async function administrador(): Promise<string> {
  if (!enNube()) return "demo@atrium.local";
  const audiencia = process.env.ATRIUM_IAP_AUDIENCE;
  const admins = listaCorreos(process.env.ATRIUM_ADMINS);
  const jwt = (await headers()).get("x-goog-iap-jwt-assertion");
  if (!audiencia || admins.length === 0 || !jwt) throw new SinAcceso();
  try {
    const { pubkeys } = await cliente.getIapPublicKeys();
    const ticket = await cliente.verifySignedJwtWithCertsAsync(jwt, pubkeys, audiencia, [
      "https://cloud.google.com/iap",
    ]);
    const correo = normalizarCorreo(ticket.getPayload()?.email ?? "");
    if (admins.includes(correo)) return correo;
  } catch (e) {
    console.warn("IAP: encabezado inválido", e instanceof Error ? e.message : e);
  }
  throw new SinAcceso();
}
