import "server-only";

/** En Cloud Run existe K_SERVICE. Fuera de la nube, Atrium corre en demostración con datos en memoria. */
export function enNube(): boolean {
  return Boolean(process.env.K_SERVICE);
}

export const PROYECTO_CENTRAL = process.env.ATRIUM_PROYECTO_CENTRAL ?? "josecarloscorona-web";

export function listaCorreos(valor: string | undefined): string[] {
  return (valor ?? "")
    .split(",")
    .map((c) => c.trim().toLowerCase())
    .filter(Boolean);
}
