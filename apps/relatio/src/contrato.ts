// Contrato con el widget (`web/relatio/src/contrato.ts`). Si cambia un límite o un campo, cambia en los dos.

export const LIMITES = {
  titulo: 120,
  que: 4000,
  cuando: 500,
  adicional: 4000,
  pagina: 500,
  captura: 5 * 1024 * 1024,
  corto: 300,
} as const;

export const TIPOS_CAPTURA = ["image/png", "image/jpeg", "image/webp"] as const;
export type TipoCaptura = (typeof TIPOS_CAPTURA)[number];

export type Reporte = {
  app: string;
  titulo?: string;
  que: string;
  cuando: string;
  adicional?: string;
  avisar: boolean;
  pagina: string;
  contexto: { navegador: string; pantalla: string; tema: "claro" | "oscuro"; idioma: string; version?: string };
  captura?: { tipo: TipoCaptura; datos: string };
};

export type Validacion = { ok: true; reporte: Reporte } | { ok: false; error: string };

const texto = (v: unknown, max: number, requerido: boolean): string | undefined | null => {
  if (v === undefined || v === null || v === "") return requerido ? null : undefined;
  if (typeof v !== "string") return null;
  const limpio = v.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "").trim();
  if (requerido && !limpio) return null;
  return limpio.length > max ? null : limpio;
};

export function bytesDeBase64(datos: string): number {
  const relleno = datos.endsWith("==") ? 2 : datos.endsWith("=") ? 1 : 0;
  return Math.floor((datos.length * 3) / 4) - relleno;
}

/** Valida el cuerpo tal como llega. Nada del navegador se usa sin pasar por aquí. */
export function validarReporte(c: unknown): Validacion {
  if (!c || typeof c !== "object") return { ok: false, error: "El reporte llegó vacío." };
  const o = c as Record<string, unknown>;
  const ctx = (o.contexto ?? {}) as Record<string, unknown>;
  const app = texto(o.app, 40, true);
  const titulo = texto(o.titulo, LIMITES.titulo, false);
  const que = texto(o.que, LIMITES.que, true);
  const cuando = texto(o.cuando, LIMITES.cuando, true);
  const adicional = texto(o.adicional, LIMITES.adicional, false);
  const pagina = texto(o.pagina, LIMITES.pagina, false) ?? "";
  if (!app) return { ok: false, error: "Falta la app." };
  if (!que) return { ok: false, error: "Cuéntanos qué está pasando." };
  if (!cuando) return { ok: false, error: "Dinos cuándo ocurre." };
  if (titulo === null || adicional === null) return { ok: false, error: "Algún campo es demasiado largo." };
  if (pagina && !/^https?:\/\//.test(pagina)) return { ok: false, error: "La página no es válida." };

  let captura: Reporte["captura"];
  if (o.captura !== undefined && o.captura !== null) {
    const cap = o.captura as Record<string, unknown>;
    const tipo = cap.tipo as TipoCaptura;
    const datos = typeof cap.datos === "string" ? cap.datos : "";
    if (!TIPOS_CAPTURA.includes(tipo)) return { ok: false, error: "La captura debe ser PNG, JPG o WebP." };
    if (!datos || !/^[A-Za-z0-9+/]+={0,2}$/.test(datos)) return { ok: false, error: "La captura no es válida." };
    if (bytesDeBase64(datos) > LIMITES.captura) return { ok: false, error: "La captura pesa más de 5 MB." };
    captura = { tipo, datos };
  }

  return {
    ok: true,
    reporte: {
      app,
      ...(titulo ? { titulo } : {}),
      que,
      cuando,
      ...(adicional ? { adicional } : {}),
      avisar: o.avisar === true,
      pagina: pagina ? pagina.replace(/[?#].*$/, "") : "",
      contexto: {
        navegador: texto(ctx.navegador, LIMITES.corto, false) ?? "",
        pantalla: texto(ctx.pantalla, 40, false) ?? "",
        tema: ctx.tema === "oscuro" ? "oscuro" : "claro",
        idioma: texto(ctx.idioma, 20, false) ?? "",
        ...(typeof ctx.version === "string" && ctx.version ? { version: ctx.version.slice(0, 40) } : {}),
      },
      ...(captura ? { captura } : {}),
    },
  };
}
