// Contrato entre el widget y Relatio (`apps/relatio`). Relatio valida lo mismo con su copia en
// `apps/relatio/src/contrato.ts`: si cambia un límite o un campo, cambia en los dos.

export const LIMITES = {
  titulo: 120,
  que: 4000,
  cuando: 500,
  adicional: 4000,
  pagina: 500,
  /** Bytes de la imagen ya decodificada. */
  captura: 5 * 1024 * 1024,
} as const;

export const TIPOS_CAPTURA = ["image/png", "image/jpeg", "image/webp"] as const;
export type TipoCaptura = (typeof TIPOS_CAPTURA)[number];

export type Contexto = {
  navegador: string;
  pantalla: string;
  tema: "claro" | "oscuro";
  idioma: string;
  version?: string;
};

export type Reporte = {
  app: string;
  titulo?: string;
  que: string;
  cuando: string;
  adicional?: string;
  avisar: boolean;
  pagina: string;
  contexto: Contexto;
  captura?: { tipo: TipoCaptura; datos: string };
};

export type Campos = { titulo: string; que: string; cuando: string; adicional: string };
export type Errores = Partial<Record<keyof Campos, string>>;

/** Errores de los campos del formulario, con el texto que ve la persona. Vacío = se puede enviar. */
export function validarCampos(c: Campos): Errores {
  const e: Errores = {};
  if (!c.que.trim()) e.que = "Cuéntanos qué está pasando.";
  else if (c.que.length > LIMITES.que) e.que = `Usa máximo ${LIMITES.que} caracteres.`;
  if (!c.cuando.trim()) e.cuando = "Dinos cuándo ocurre.";
  else if (c.cuando.length > LIMITES.cuando) e.cuando = `Usa máximo ${LIMITES.cuando} caracteres.`;
  if (c.titulo.length > LIMITES.titulo) e.titulo = `Usa máximo ${LIMITES.titulo} caracteres.`;
  if (c.adicional.length > LIMITES.adicional) e.adicional = `Usa máximo ${LIMITES.adicional} caracteres.`;
  return e;
}

/**
 * La página sin query ni fragmento: ahí viajan tokens de invitación, códigos de OAuth y filtros
 * que no ayudan a diagnosticar y no deben quedar en un issue. `rutasPrivadas` tapa segmentos
 * secretos de la ruta: con `"/invitar/:viaje/:token"`, `/invitar/abc/XYZ` queda `/invitar/[viaje]/[token]`.
 */
export function limpiarUrl(url: string, rutasPrivadas: readonly string[] = []): string {
  let u: URL;
  try {
    u = new URL(url);
  } catch {
    return "";
  }
  const partes = u.pathname.split("/");
  for (const plantilla of rutasPrivadas) {
    const p = plantilla.split("/");
    if (p.length !== partes.length || !p.every((seg, i) => seg.startsWith(":") || seg === partes[i])) continue;
    u.pathname = p.map((seg, i) => (seg.startsWith(":") ? `[${seg.slice(1)}]` : partes[i])).join("/");
    break;
  }
  return `${u.origin}${u.pathname}`.slice(0, LIMITES.pagina);
}

/** Tamaño en bytes de un base64 ya decodificado, sin decodificarlo. */
export function bytesDeBase64(datos: string): number {
  const relleno = datos.endsWith("==") ? 2 : datos.endsWith("=") ? 1 : 0;
  return Math.floor((datos.length * 3) / 4) - relleno;
}
