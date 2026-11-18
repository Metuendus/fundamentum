import { randomUUID } from "node:crypto";
import type { Almacen, Capturas } from "./almacen.ts";
import { APPS, esApp } from "./config.ts";
import { validarReporte } from "./contrato.ts";
import type { GitHub } from "./github.ts";
import { armarIssue, comentarioDuplicado, huella } from "./issue.ts";


export type Usuario = { uid: string; correo: string };

export type Dependencias = {
  /** Verifica el ID token contra el proyecto de Firebase de la app. `null` si no es válido. */
  verificar(token: string, proyecto: string): Promise<Usuario | null>;
  almacen: Almacen;
  capturas: Capturas;
  github: GitHub;
  atriumUrl: string;
  ahora?: () => Date;
  nuevoId?: () => string;
};

export type Salida = { estado: number; cuerpo: Record<string, unknown> };

const EXT = { "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp" } as const;

/**
 * Recibe un reporte: valida, verifica la sesión contra la app que dice ser (el repo sale de la
 * app verificada, nunca del navegador), suma duplicados, aplica cupos, guarda la captura en privado
 * y crea el issue. El correo sale del token, no del cuerpo.
 */
export async function recibir(token: string | null, cuerpo: unknown, d: Dependencias): Promise<Salida> {
  const v = validarReporte(cuerpo);
  if (!v.ok) return { estado: 400, cuerpo: { error: v.error } };
  const r = v.reporte;
  if (!esApp(r.app)) return { estado: 400, cuerpo: { error: "App desconocida." } };
  const app = APPS[r.app];

  if (!token) return { estado: 401, cuerpo: { error: "Falta la sesión." } };
  const usuario = await d.verificar(token, app.proyecto);
  if (!usuario) return { estado: 401, cuerpo: { error: "La sesión no es válida." } };

  const ahora = (d.ahora ?? (() => new Date()))();
  const h = huella(r.app, usuario.uid, r);
  const previo = await d.almacen.previo(h, ahora.getTime());
  const id = (d.nuevoId ?? randomUUID)();
  if (previo) {
    await d.github.comentar(previo.repo, previo.issue, comentarioDuplicado(r, id));
    return { estado: 200, cuerpo: { id: previo.id, duplicado: true } };
  }

  if (!(await d.almacen.reservarCupo(usuario.uid, ahora.toISOString().slice(0, 10)))) {
    return { estado: 429, cuerpo: { error: "Llegaste al límite de reportes de hoy. Intenta mañana." } };
  }

  let captura: string | null = null;
  if (r.captura) {
    captura = `${r.app}/${ahora.toISOString().slice(0, 7)}/${id}.${EXT[r.captura.tipo]}`;
    await d.capturas.guardar(captura, Buffer.from(r.captura.datos, "base64"), r.captura.tipo);
  }

  const issue = armarIssue(r.app, r, { id, correo: usuario.correo, atriumUrl: d.atriumUrl, conCaptura: Boolean(captura) });
  const creado = await d.github.crearIssue(app.repo, issue);
  await d.almacen.guardar({
    id,
    app: r.app,
    uid: usuario.uid,
    correo: usuario.correo,
    titulo: issue.title,
    pagina: r.pagina,
    avisar: r.avisar,
    huella: h,
    repo: app.repo,
    issue: creado.numero,
    issueUrl: creado.url,
    captura,
    creado: ahora.toISOString(),
  });
  return { estado: 201, cuerpo: { id, duplicado: false } };
}
