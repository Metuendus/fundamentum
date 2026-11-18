import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { fileURLToPath } from "node:url";
import { AlmacenEnMemoria, AlmacenFirestore, CapturasGcs, capturasDe } from "./almacen.ts";
import { config, enNube } from "./config.ts";
import { GitHubApp, GitHubEnMemoria } from "./github.ts";
import { recibir, type Dependencias, type Usuario } from "./recibir.ts";

/** Cuerpo máximo: 5 MB de imagen en base64 (~6.7 MB) más el texto. */
const MAX_CUERPO = 7 * 1024 * 1024;

export function origenPermitido(origen: string | undefined, permitidos: string[]): string | null {
  return origen && permitidos.includes(origen) ? origen : null;
}

async function leerJson(req: IncomingMessage): Promise<unknown> {
  const trozos: Buffer[] = [];
  let total = 0;
  for await (const t of req) {
    total += (t as Buffer).length;
    if (total > MAX_CUERPO) throw Object.assign(new Error("demasiado grande"), { estado: 413 });
    trozos.push(t as Buffer);
  }
  try {
    return JSON.parse(Buffer.concat(trozos).toString("utf8"));
  } catch {
    throw Object.assign(new Error("json inválido"), { estado: 400 });
  }
}

function responder(res: ServerResponse, estado: number, cuerpo: unknown, origen: string | null) {
  res.writeHead(estado, {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
    ...(origen ? { "access-control-allow-origin": origen, vary: "Origin" } : {}),
  });
  res.end(JSON.stringify(cuerpo));
}

export async function dependencias(): Promise<Dependencias> {
  const c = config();
  if (!enNube()) {
    const m = new AlmacenEnMemoria();
    console.log("Relatio en demostración: memoria, sin GitHub y cualquier token vale.");
    return {
      verificar: async (token) => ({ uid: `demo-${token.slice(0, 8)}`, correo: "demo@relatio.local" }),
      almacen: m,
      capturas: capturasDe(m),
      github: new GitHubEnMemoria(),
      atriumUrl: c.atriumUrl,
    };
  }
  if (!c.githubAppId || !c.githubLlave || !c.bucket || c.origenes.length === 0) {
    throw new Error("Faltan RELATIO_GITHUB_APP_ID, RELATIO_GITHUB_APP_KEY, RELATIO_BUCKET o RELATIO_ORIGENES.");
  }
  const { applicationDefault, getApp, getApps, initializeApp } = await import("firebase-admin/app");
  const { getAuth } = await import("firebase-admin/auth");
  const { getFirestore } = await import("firebase-admin/firestore");
  const { Storage } = await import("@google-cloud/storage");
  const appDe = (proyecto: string) =>
    getApps().some((a) => a.name === proyecto)
      ? getApp(proyecto)
      : initializeApp({ projectId: proyecto, credential: applicationDefault() }, proyecto);
  return {
    verificar: async (token, proyecto): Promise<Usuario | null> => {
      try {
        const t = await getAuth(appDe(proyecto)).verifyIdToken(token);
        return { uid: t.uid, correo: t.email ?? "" };
      } catch (e) {
        console.warn("token inválido", proyecto, e instanceof Error ? e.message : e);
        return null;
      }
    },
    almacen: new AlmacenFirestore(getFirestore(appDe(c.proyectoCentral))),
    capturas: new CapturasGcs(new Storage().bucket(c.bucket)),
    github: new GitHubApp(c.githubAppId, c.githubLlave),
    atriumUrl: c.atriumUrl,
  };
}

export function manejador(d: Dependencias, origenes: string[]) {
  return async (req: IncomingMessage, res: ServerResponse) => {
    const origen = origenPermitido(req.headers.origin, origenes);
    const ruta = (req.url ?? "/").split("?")[0];
    try {
      if (req.method === "GET" && ruta === "/salud") return responder(res, 200, { ok: true }, null);
      if (ruta !== "/reportes") return responder(res, 404, { error: "No existe." }, origen);
      if (req.method === "OPTIONS") {
        if (!origen) return responder(res, 403, { error: "Origen no permitido." }, null);
        res.writeHead(204, {
          "access-control-allow-origin": origen,
          "access-control-allow-methods": "POST",
          "access-control-allow-headers": "authorization, content-type",
          "access-control-max-age": "600",
          vary: "Origin",
        });
        return res.end();
      }
      if (req.method !== "POST") return responder(res, 405, { error: "Método no permitido." }, origen);
      if (!origen) return responder(res, 403, { error: "Origen no permitido." }, null);
      const auth = req.headers.authorization ?? "";
      const token = auth.startsWith("Bearer ") ? auth.slice(7) : null;
      const s = await recibir(token, await leerJson(req), d);
      return responder(res, s.estado, s.cuerpo, origen);
    } catch (e) {
      const estado = (e as { estado?: number }).estado;
      if (estado === 413) return responder(res, 413, { error: "El reporte pesa demasiado. Usa una captura más ligera." }, origen);
      if (estado === 400) return responder(res, 400, { error: "El reporte no se pudo leer." }, origen);
      console.error("Relatio: error al recibir", e instanceof Error ? e.message : e);
      return responder(res, 502, { error: "No pudimos crear el reporte. Intenta de nuevo en un momento." }, origen);
    }
  };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const c = config();
  const origenes = enNube() ? c.origenes : ["http://localhost:3000", ...c.origenes];
  const servidor = createServer(manejador(await dependencias(), origenes));
  servidor.listen(c.puerto, () => console.log(`Relatio escucha en :${c.puerto}`));
}
