import type { Firestore } from "firebase-admin/firestore";
import type { Bucket } from "@google-cloud/storage";
import { TOPES } from "./config.ts";

/** Fila de `reportes/{id}` en el Firestore central. Atrium la lee para su vista de reportes. */
export type Registro = {
  id: string;
  app: string;
  uid: string;
  correo: string;
  titulo: string;
  pagina: string;
  avisar: boolean;
  huella: string;
  repo: string;
  issue: number;
  issueUrl: string;
  captura: string | null;
  creado: string;
};

export type Previo = { id: string; repo: string; issue: number };

export interface Almacen {
  /** Reserva un cupo del día para la persona y el global; `false` si ya no hay. */
  reservarCupo(uid: string, dia: string): Promise<boolean>;
  /** Un reporte con la misma huella dentro de la ventana de duplicados. */
  previo(huella: string, ahora: number): Promise<Previo | null>;
  guardar(r: Registro): Promise<void>;
}

export interface Capturas {
  guardar(ruta: string, datos: Buffer, tipo: string): Promise<void>;
}

export class AlmacenFirestore implements Almacen {
  private readonly db: Firestore;
  constructor(db: Firestore) {
    this.db = db;
  }

  async reservarCupo(uid: string, dia: string): Promise<boolean> {
    const persona = this.db.doc(`reportes_cupos/${dia}_${uid}`);
    const global = this.db.doc(`reportes_cupos/${dia}__global`);
    return this.db.runTransaction(async (t) => {
      const [p, g] = await t.getAll(persona, global);
      const usados = Number(p.get("usados") ?? 0);
      const total = Number(g.get("usados") ?? 0);
      if (usados >= TOPES.porUsuario || total >= TOPES.global) return false;
      t.set(persona, { usados: usados + 1, dia }, { merge: true });
      t.set(global, { usados: total + 1, dia }, { merge: true });
      return true;
    });
  }

  async previo(huella: string, ahora: number): Promise<Previo | null> {
    const d = await this.db.doc(`reportes_huellas/${huella}`).get();
    if (!d.exists || Date.parse(String(d.get("creado"))) < ahora - TOPES.duplicadoMs) return null;
    return { id: String(d.get("id")), repo: String(d.get("repo")), issue: Number(d.get("issue")) };
  }

  async guardar(r: Registro): Promise<void> {
    const lote = this.db.batch();
    lote.set(this.db.doc(`reportes/${r.id}`), r);
    lote.set(this.db.doc(`reportes_huellas/${r.huella}`), { id: r.id, repo: r.repo, issue: r.issue, creado: r.creado });
    await lote.commit();
  }
}

export class CapturasGcs implements Capturas {
  private readonly bucket: Bucket;
  constructor(bucket: Bucket) {
    this.bucket = bucket;
  }

  async guardar(ruta: string, datos: Buffer, tipo: string): Promise<void> {
    await this.bucket.file(ruta).save(datos, { contentType: tipo, resumable: false, metadata: { cacheControl: "private, max-age=0" } });
  }
}

export class AlmacenEnMemoria implements Almacen {
  cupos = new Map<string, number>();
  registros: Registro[] = [];
  archivos = new Map<string, { datos: Buffer; tipo: string }>();

  async reservarCupo(uid: string, dia: string): Promise<boolean> {
    const p = this.cupos.get(`${dia}_${uid}`) ?? 0;
    const g = this.cupos.get(`${dia}__global`) ?? 0;
    if (p >= TOPES.porUsuario || g >= TOPES.global) return false;
    this.cupos.set(`${dia}_${uid}`, p + 1);
    this.cupos.set(`${dia}__global`, g + 1);
    return true;
  }

  async previo(huella: string, ahora: number): Promise<Previo | null> {
    const r = [...this.registros].reverse().find((x) => x.huella === huella);
    if (!r || Date.parse(r.creado) < ahora - TOPES.duplicadoMs) return null;
    return { id: r.id, repo: r.repo, issue: r.issue };
  }

  async guardar(r: Registro): Promise<void> {
    this.registros.push(r);
  }

  async guardarCaptura(ruta: string, datos: Buffer, tipo: string): Promise<void> {
    this.archivos.set(ruta, { datos, tipo });
  }
}

/** Adaptador para usar el almacén en memoria como `Capturas`. */
export const capturasDe = (m: AlmacenEnMemoria): Capturas => ({ guardar: (r, d, t) => m.guardarCaptura(r, d, t) });
