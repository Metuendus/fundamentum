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
 * que no ayudan a diagnosticar y no deben quedar en un issue.
 */
export function limpiarUrl(url: string): string {
  try {
    const u = new URL(url);
    return `${u.origin}${u.pathname}`.slice(0, LIMITES.pagina);
  } catch {
    return "";
  }
}

/** Tamaño en bytes de un base64 ya decodificado, sin decodificarlo. */
export function bytesDeBase64(datos: string): number {
  const relleno = datos.endsWith("==") ? 2 : datos.endsWith("=") ? 1 : 0;
  return Math.floor((datos.length * 3) / 4) - relleno;
}
