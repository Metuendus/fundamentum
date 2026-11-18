import "server-only";
import { getFirestore } from "firebase-admin/firestore";
import { enNube, PROYECTO_CENTRAL } from "./config";
import { appDe } from "./firebase";

/** Fila de `reportes/{id}` que escribe Relatio (`apps/relatio/src/almacen.ts`). Mismo modelo en ambos. */
export type Reporte = {
  id: string;
  app: string;
  uid: string;
  correo: string;
  titulo: string;
  pagina: string;
  avisar: boolean;
  repo: string;
  issue: number;
  issueUrl: string;
  captura: string | null;
  creado: string;
};

export interface Reportes {
  recientes(limite: number): Promise<Reporte[]>;
  uno(id: string): Promise<Reporte | null>;
  captura(ruta: string): Promise<{ datos: Buffer; tipo: string } | null>;
}

const BUCKET = process.env.ATRIUM_BUCKET_RELATIO ?? `${PROYECTO_CENTRAL}-relatio`;
const RUTA_VALIDA = /^[a-z]+\/\d{4}-\d{2}\/[\w-]+\.(png|jpg|webp)$/;

class ReportesNube implements Reportes {
  private db = getFirestore(appDe(PROYECTO_CENTRAL));

  async recientes(limite: number) {
    const snap = await this.db.collection("reportes").orderBy("creado", "desc").limit(limite).get();
    return snap.docs.map((d) => d.data() as Reporte);
  }

  async uno(id: string) {
    const d = await this.db.collection("reportes").doc(id).get();
    return d.exists ? (d.data() as Reporte) : null;
  }

  async captura(ruta: string) {
    if (!RUTA_VALIDA.test(ruta)) return null;
    const { Storage } = await import("@google-cloud/storage");
    const archivo = new Storage().bucket(BUCKET).file(ruta);
    const [existe] = await archivo.exists();
    if (!existe) return null;
    const [[datos], [meta]] = await Promise.all([archivo.download(), archivo.getMetadata()]);
    return { datos, tipo: String(meta.contentType ?? "image/png") };
  }
}

/** Demostración: un reporte de ejemplo con una captura de 1×1. */
class ReportesMemoria implements Reportes {
  private lista: Reporte[] = [
    {
      id: "demo-1",
      app: "domi",
      uid: "u-demo",
      correo: "ana@ejemplo.com",
      titulo: "[Reporte] El mapa no carga en la Roma",
      pagina: "https://domi.josecarloscorona.dev/hoy",
      avisar: true,
      repo: "Metuendus/domi",
      issue: 1,
      issueUrl: "https://github.com/Metuendus/domi/issues/1",
      captura: "domi/2026-11/demo-1.png",
      creado: "2026-11-18T18:00:00.000Z",
    },
  ];

  async recientes(limite: number) {
    return this.lista.slice(0, limite);
  }
  async uno(id: string) {
    return this.lista.find((r) => r.id === id) ?? null;
  }
  async captura(ruta: string) {
    if (!this.lista.some((r) => r.captura === ruta)) return null;
    const png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=";
    return { datos: Buffer.from(png, "base64"), tipo: "image/png" };
  }
}

const global_ = globalThis as unknown as { reportesAtrium?: Reportes };

export function reportes(): Reportes {
  global_.reportesAtrium ??= enNube() ? new ReportesNube() : new ReportesMemoria();
  return global_.reportesAtrium;
}
