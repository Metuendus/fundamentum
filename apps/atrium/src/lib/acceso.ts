// Modelo de la lista de acceso. Es el mismo que `fundamentum_acceso.modelos` (Python): el portero
// de cada app lee lo que Atrium escribe, así que los nombres de campos no cambian sin cambiar ambos.

export const APPS = [
  { id: "iterum", nombre: "Iterum", proyecto: "travel-planner-509322" },
  { id: "domi", nombre: "Domi", proyecto: "domi-mx" },
  { id: "vocatio", nombre: "Vocatio", proyecto: "vocatio-mx" },
] as const;

export type AppId = (typeof APPS)[number]["id"];
export type Modo = "beta" | "abierta";
export type Origen = "lista" | "invitacion" | "solicitud";

export type Permiso = { origen: Origen; alta: string; vence: string | null; nota: string };
export type Pase = { correo: string; apps: Partial<Record<AppId, Permiso>> };
export type Solicitud = { id: string; correo: string; app: AppId; motivo: string; creada: string };

export const ORIGEN: Record<Origen, string> = {
  lista: "Lista",
  invitacion: "Invitación",
  solicitud: "Solicitud",
};

export function normalizarCorreo(correo: string): string {
  return correo.trim().toLowerCase();
}

export function correoValido(correo: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(correo) && correo.length <= 254;
}

export function esApp(valor: unknown): valor is AppId {
  return APPS.some((a) => a.id === valor);
}

export function esModo(valor: unknown): valor is Modo {
  return valor === "beta" || valor === "abierta";
}

/** Igual que `decidir` del portero: un permiso vencido ya no deja entrar. */
export function vigente(permiso: Permiso | undefined, ahora: Date): boolean {
  if (!permiso) return false;
  return permiso.vence === null || new Date(permiso.vence) > ahora;
}

export function ordenarPases(pases: Pase[]): Pase[] {
  return [...pases].sort((a, b) => a.correo.localeCompare(b.correo));
}
