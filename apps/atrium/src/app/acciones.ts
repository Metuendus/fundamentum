"use server";

import { revalidatePath } from "next/cache";
import { correoValido, esApp, esModo, normalizarCorreo } from "@/lib/acceso";
import { almacen } from "@/lib/almacen";
import { cerrarSesiones } from "@/lib/cuentas";
import { administrador } from "@/lib/identidad";

export async function darAcceso(datos: FormData) {
  const por = await administrador();
  const correo = normalizarCorreo(String(datos.get("correo") ?? ""));
  const nota = String(datos.get("nota") ?? "").slice(0, 200);
  const apps = datos.getAll("app").filter(esApp);
  if (!correoValido(correo) || apps.length === 0) return;
  for (const app of apps) await almacen().darPermiso(correo, app, "lista", nota, por);
  revalidatePath("/");
}

export async function quitarAcceso(datos: FormData) {
  const por = await administrador();
  const correo = normalizarCorreo(String(datos.get("correo") ?? ""));
  const app = datos.get("app");
  if (!esApp(app)) return;
  await almacen().quitarPermiso(correo, app, por);
  await cerrarSesiones(correo, app);
  revalidatePath("/");
}

export async function cambiarModo(datos: FormData) {
  const por = await administrador();
  const app = datos.get("app");
  const modo = datos.get("modo");
  if (!esApp(app) || !esModo(modo)) return;
  await almacen().cambiarModo(app, modo, por);
  revalidatePath("/");
}

export async function resolverSolicitud(datos: FormData) {
  const por = await administrador();
  const id = String(datos.get("id") ?? "");
  const aprobada = datos.get("decision") === "aprobar";
  const s = await almacen().resolverSolicitud(id, aprobada, por);
  if (s && aprobada) await almacen().darPermiso(s.correo, s.app, "solicitud", s.motivo.slice(0, 200), por);
  revalidatePath("/");
}
