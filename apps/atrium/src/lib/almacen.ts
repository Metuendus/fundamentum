import "server-only";
import { FieldValue, getFirestore, Timestamp } from "firebase-admin/firestore";
import { APPS, type AppId, type Modo, type Origen, type Pase, type Permiso, type Solicitud } from "./acceso";
import { enNube, PROYECTO_CENTRAL } from "./config";
import { appDe } from "./firebase";

/**
 * Lista de acceso en el Firestore central, con las colecciones que lee el portero
 * (`fundamentum_acceso`): `acceso/{correo}`, `apps/{app}` y `solicitudes/{id}`. Cada cambio deja
 * una fila en `bitacora` con quién lo hizo.
 */
export interface Almacen {
  pases(): Promise<Pase[]>;
  modos(): Promise<Record<AppId, Modo>>;
  solicitudes(): Promise<Solicitud[]>;
  darPermiso(correo: string, app: AppId, origen: Origen, nota: string, por: string): Promise<void>;
  quitarPermiso(correo: string, app: AppId, por: string): Promise<void>;
  cambiarModo(app: AppId, modo: Modo, por: string): Promise<void>;
  resolverSolicitud(id: string, aprobada: boolean, por: string): Promise<Solicitud | null>;
}

const fecha = (v: unknown): string =>
  v instanceof Timestamp ? v.toDate().toISOString() : typeof v === "string" ? v : new Date(0).toISOString();

function permisoDe(datos: Record<string, unknown>): Permiso {
  return {
    origen: (datos.origen as Origen) ?? "lista",
    alta: fecha(datos.alta),
    vence: datos.vence ? fecha(datos.vence) : null,
    nota: String(datos.nota ?? ""),
  };
}

class AlmacenFirestore implements Almacen {
  private db = getFirestore(appDe(PROYECTO_CENTRAL));

  private async anotar(accion: string, detalle: Record<string, string>, por: string) {
    await this.db.collection("bitacora").add({ accion, ...detalle, por, en: FieldValue.serverTimestamp() });
  }

  async pases(): Promise<Pase[]> {
    const snap = await this.db.collection("acceso").get();
    return snap.docs.map((d) => {
      const apps = (d.data().apps ?? {}) as Record<string, Record<string, unknown>>;
      return {
        correo: d.id,
        apps: Object.fromEntries(Object.entries(apps).map(([app, p]) => [app, permisoDe(p)])),
      };
    });
  }

  async modos(): Promise<Record<AppId, Modo>> {
    const snap = await this.db.collection("apps").get();
    const leidos = Object.fromEntries(snap.docs.map((d) => [d.id, d.data().modo]));
    return Object.fromEntries(
      APPS.map((a) => [a.id, leidos[a.id] === "abierta" ? "abierta" : "beta"]),
    ) as Record<AppId, Modo>;
  }

  async solicitudes(): Promise<Solicitud[]> {
    const snap = await this.db.collection("solicitudes").where("estado", "==", "pendiente").get();
    return snap.docs
      .map((d) => {
        const s = d.data();
        return { id: d.id, correo: s.correo, app: s.app, motivo: s.motivo ?? "", creada: fecha(s.creada) };
      })
      .sort((a, b) => b.creada.localeCompare(a.creada));
  }

  async darPermiso(correo: string, app: AppId, origen: Origen, nota: string, por: string) {
    await this.db
      .collection("acceso")
      .doc(correo)
      .set({ apps: { [app]: { origen, alta: FieldValue.serverTimestamp(), vence: null, nota } } }, { merge: true });
    await this.anotar("dar_permiso", { correo, app, origen }, por);
  }

  async quitarPermiso(correo: string, app: AppId, por: string) {
    await this.db.collection("acceso").doc(correo).update({ [`apps.${app}`]: FieldValue.delete() });
    await this.anotar("quitar_permiso", { correo, app }, por);
  }

  async cambiarModo(app: AppId, modo: Modo, por: string) {
    await this.db.collection("apps").doc(app).set({ modo }, { merge: true });
    await this.anotar("cambiar_modo", { app, modo }, por);
  }

  async resolverSolicitud(id: string, aprobada: boolean, por: string) {
    const ref = this.db.collection("solicitudes").doc(id);
    const datos = (await ref.get()).data();
    if (!datos || datos.estado !== "pendiente") return null;
    await ref.update({ estado: aprobada ? "aprobada" : "rechazada", resuelta: FieldValue.serverTimestamp(), por });
    await this.anotar(aprobada ? "aprobar_solicitud" : "rechazar_solicitud", { correo: datos.correo, app: datos.app }, por);
    return { id, correo: datos.correo, app: datos.app, motivo: datos.motivo ?? "", creada: fecha(datos.creada) };
  }
}

/** Demostración: datos en memoria, se pierden al reiniciar. */
class AlmacenMemoria implements Almacen {
  private lista = new Map<string, Pase>();
  private modo: Record<AppId, Modo> = { iterum: "beta", domi: "beta", vocatio: "beta" };
  private pendientes: Solicitud[] = [
    { id: "s1", correo: "ana@ejemplo.com", app: "domi", motivo: "Busco depa en la Roma", creada: "2026-10-28T18:00:00.000Z" },
  ];

  constructor() {
    const alta = "2026-10-29T00:00:00.000Z";
    const p = (origen: Origen, nota = ""): Permiso => ({ origen, alta, vence: null, nota });
    this.lista.set("demo@atrium.local", { correo: "demo@atrium.local", apps: { iterum: p("lista"), domi: p("lista"), vocatio: p("lista") } });
    this.lista.set("viajera@ejemplo.com", { correo: "viajera@ejemplo.com", apps: { iterum: p("invitacion", "Viaje a Oaxaca") } });
  }

  async pases() {
    return [...this.lista.values()];
  }
  async modos() {
    return { ...this.modo };
  }
  async solicitudes() {
    return [...this.pendientes];
  }
  async darPermiso(correo: string, app: AppId, origen: Origen, nota: string) {
    const pase = this.lista.get(correo) ?? { correo, apps: {} };
    pase.apps[app] = { origen, alta: new Date().toISOString(), vence: null, nota };
    this.lista.set(correo, pase);
  }
  async quitarPermiso(correo: string, app: AppId) {
    delete this.lista.get(correo)?.apps[app];
  }
  async cambiarModo(app: AppId, modo: Modo) {
    this.modo[app] = modo;
  }
  async resolverSolicitud(id: string) {
    const s = this.pendientes.find((x) => x.id === id) ?? null;
    this.pendientes = this.pendientes.filter((x) => x.id !== id);
    return s;
  }
}

const global_ = globalThis as unknown as { almacenAtrium?: Almacen };

export function almacen(): Almacen {
  global_.almacenAtrium ??= enNube() ? new AlmacenFirestore() : new AlmacenMemoria();
  return global_.almacenAtrium;
}
