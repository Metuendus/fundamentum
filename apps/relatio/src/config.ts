/**
 * Apps que pueden reportar: su proyecto de Firebase (contra el que se verifica el ID token) y el
 * repo donde cae el issue. Una app nueva solo se agrega aquí (y a la GitHub App Relatio).
 */
export const APPS = {
  iterum: { nombre: "Iterum", proyecto: "travel-planner-509322", repo: "Metuendus/iterum" },
  domi: { nombre: "Domi", proyecto: "domi-mx", repo: "Metuendus/domi" },
  vocatio: { nombre: "Vocatio", proyecto: "vocatio-mx", repo: "Metuendus/vocatio" },
  expensum: { nombre: "Expensum", proyecto: "expensum-mx", repo: "Metuendus/expensum" },
} as const;

export type AppId = keyof typeof APPS;

export function esApp(v: string): v is AppId {
  return Object.hasOwn(APPS, v);
}

export const ETIQUETAS = ["origen:usuario", "tipo:bug", "requiere-triage"] as const;
export const ETIQUETA_AVISAR = "avisar";

export const TOPES = {
  /** Reportes nuevos por persona al día (los duplicados no cuentan). */
  porUsuario: 5,
  /** Reportes nuevos al día entre todas las apps: la red si algo se sale de control. */
  global: 30,
  /** Ventana en la que el mismo texto en la misma página se suma al issue anterior. */
  duplicadoMs: 10 * 60 * 1000,
} as const;

export function enNube(): boolean {
  return Boolean(process.env.K_SERVICE);
}

export function lista(valor: string | undefined): string[] {
  return (valor ?? "")
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);
}

export const config = () => ({
  puerto: Number(process.env.PORT ?? 8080),
  proyectoCentral: process.env.RELATIO_PROYECTO_CENTRAL ?? "josecarloscorona-web",
  bucket: process.env.RELATIO_BUCKET ?? "",
  origenes: lista(process.env.RELATIO_ORIGENES),
  atriumUrl: (process.env.RELATIO_ATRIUM_URL ?? "").replace(/\/+$/, ""),
  githubAppId: process.env.RELATIO_GITHUB_APP_ID ?? "",
  githubLlave: process.env.RELATIO_GITHUB_APP_KEY ?? "",
});
