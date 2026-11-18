import type { Reporte } from "./contrato.ts";

export type Respuesta = { ok: true; id: string; duplicado: boolean } | { ok: false; mensaje: string };

/** Envía el reporte a Relatio con el ID token de Firebase de la app. Nunca lanza: devuelve el error legible. */
export async function enviarReporte(relatioUrl: string, token: string, reporte: Reporte): Promise<Respuesta> {
  try {
    const r = await fetch(`${relatioUrl.replace(/\/+$/, "")}/reportes`, {
      method: "POST",
      headers: { "content-type": "application/json", authorization: `Bearer ${token}` },
      body: JSON.stringify(reporte),
    });
    const cuerpo = (await r.json().catch(() => ({}))) as { id?: string; duplicado?: boolean; error?: string };
    if (r.ok && cuerpo.id) return { ok: true, id: cuerpo.id, duplicado: Boolean(cuerpo.duplicado) };
    if (r.status === 429) return { ok: false, mensaje: cuerpo.error ?? "Llegaste al límite de reportes de hoy. Intenta mañana." };
    if (r.status === 401) return { ok: false, mensaje: "Tu sesión expiró. Vuelve a entrar e intenta de nuevo." };
    return { ok: false, mensaje: cuerpo.error ?? "No pudimos enviar el reporte. Intenta de nuevo en un momento." };
  } catch {
    return { ok: false, mensaje: "No hay conexión con el servidor. Revisa tu internet e intenta de nuevo." };
  }
}
