import { APPS, ORIGEN, ordenarPases, vigente, type AppId } from "@/lib/acceso";
import { almacen } from "@/lib/almacen";
import { enNube } from "@/lib/config";
import { cuentas, type Cuenta } from "@/lib/cuentas";
import { administrador, SinAcceso } from "@/lib/identidad";
import { cambiarModo, darAcceso, quitarAcceso, resolverSolicitud } from "./acciones";
import s from "./page.module.css";

export const dynamic = "force-dynamic";

const fechaCorta = new Intl.DateTimeFormat("es-MX", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "America/Mexico_City",
});
const fmt = (iso: string | null) => (iso ? fechaCorta.format(new Date(iso)) : "—");

export default async function Inicio() {
  let admin: string;
  try {
    admin = await administrador();
  } catch (e) {
    if (e instanceof SinAcceso) return <SinPermiso />;
    throw e;
  }

  const a = almacen();
  const [pases, modos, solicitudes, porApp] = await Promise.all([
    a.pases().then(ordenarPases),
    a.modos(),
    a.solicitudes(),
    Promise.all(APPS.map((app) => cuentas(app.id).then((c) => ({ ok: true as const, c }), () => ({ ok: false as const })))),
  ]);
  const ahora = new Date();
  const cuentasDe = Object.fromEntries(APPS.map((app, i) => [app.id, porApp[i]])) as Record<
    AppId,
    { ok: true; c: Cuenta[] } | { ok: false }
  >;
  const enLista = (correo: string, app: AppId) => vigente(pases.find((p) => p.correo === correo)?.apps[app], ahora);

  return (
    <main className={s.pagina}>
      <header className={s.cabecera}>
        <div>
          <h1 className={s.titulo}>Atrium</h1>
          <p className={s.sub}>Quién entra a Iterum, Domi y Vocatio.</p>
        </div>
        <p className={s.sub}>
          {enNube() ? admin : "Demostración: los cambios viven en memoria"}
        </p>
      </header>

      <section aria-labelledby="t-apps" className={s.seccion}>
        <h2 id="t-apps">Apps</h2>
        <p className={s.ayuda}>En beta solo entra quien está en la lista. Abierta deja crear cuenta a cualquiera.</p>
        <div className={s.tabla} tabIndex={0} role="region" aria-label="Tabla de apps">
          <table>
            <thead>
              <tr>
                <th scope="col">App</th>
                <th scope="col">Modo</th>
                <th scope="col">Cuentas</th>
                <th scope="col">Con acceso</th>
              </tr>
            </thead>
            <tbody>
              {APPS.map((app) => {
                const modo = modos[app.id];
                const c = cuentasDe[app.id];
                return (
                  <tr key={app.id}>
                    <th scope="row">{app.nombre}</th>
                    <td>
                      <form action={cambiarModo} className={s.segmentado} aria-label={`Modo de ${app.nombre}`}>
                        <input type="hidden" name="app" value={app.id} />
                        {(["beta", "abierta"] as const).map((m) => (
                          <button
                            key={m}
                            name="modo"
                            value={m}
                            aria-pressed={modo === m}
                            className={modo === m ? s.activo : undefined}
                          >
                            {m === "beta" ? "Beta privada" : "Abierta"}
                          </button>
                        ))}
                      </form>
                    </td>
                    <td>{c.ok ? c.c.length : "No se pudo leer"}</td>
                    <td>{pases.filter((p) => vigente(p.apps[app.id], ahora)).length}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="t-sol" className={s.seccion}>
        <h2 id="t-sol">Solicitudes pendientes</h2>
        {solicitudes.length === 0 ? (
          <p className={s.ayuda}>No hay solicitudes.</p>
        ) : (
          <ul className={s.lista}>
            {solicitudes.map((sol) => (
              <li key={sol.id} className={s.tarjeta}>
                <div>
                  <strong>{sol.correo}</strong> pide {APPS.find((x) => x.id === sol.app)?.nombre}
                  <span className={s.sub}> · {fmt(sol.creada)}</span>
                  {sol.motivo && <p className={s.motivo}>{sol.motivo}</p>}
                </div>
                <form action={resolverSolicitud} className={s.acciones}>
                  <input type="hidden" name="id" value={sol.id} />
                  <button name="decision" value="aprobar" className={s.primario}>
                    Aprobar
                  </button>
                  <button name="decision" value="rechazar">Rechazar</button>
                </form>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="t-lista" className={s.seccion}>
        <h2 id="t-lista">Lista de acceso</h2>
        <form action={darAcceso} className={s.alta}>
          <label>
            Correo
            <input name="correo" type="email" required autoComplete="off" placeholder="persona@correo.com" />
          </label>
          <fieldset>
            <legend>Apps</legend>
            {APPS.map((app) => (
              <label key={app.id} className={s.casilla}>
                <input type="checkbox" name="app" value={app.id} /> {app.nombre}
              </label>
            ))}
          </fieldset>
          <label>
            Nota
            <input name="nota" maxLength={200} placeholder="Opcional" />
          </label>
          <button className={s.primario}>Dar acceso</button>
        </form>
        <div className={s.tabla} tabIndex={0} role="region" aria-label="Tabla de la lista de acceso">
          <table>
            <thead>
              <tr>
                <th scope="col">Correo</th>
                {APPS.map((app) => (
                  <th key={app.id} scope="col">
                    {app.nombre}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pases.map((p) => (
                <tr key={p.correo}>
                  <th scope="row">{p.correo}</th>
                  {APPS.map((app) => {
                    const permiso = p.apps[app.id];
                    if (!permiso) return <td key={app.id} className={s.vacio}>—</td>;
                    return (
                      <td key={app.id}>
                        <div className={s.permiso}>
                          <span>
                            {ORIGEN[permiso.origen]} · {fmt(permiso.alta)}
                            {permiso.nota && <span className={s.sub}> · {permiso.nota}</span>}
                            {!vigente(permiso, ahora) && <span className={s.alerta}> · Vencido</span>}
                          </span>
                          <form action={quitarAcceso}>
                            <input type="hidden" name="correo" value={p.correo} />
                            <input type="hidden" name="app" value={app.id} />
                            <button aria-label={`Quitar acceso de ${p.correo} a ${app.nombre}`}>Quitar</button>
                          </form>
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className={s.ayuda}>Quitar cierra también sus sesiones en esa app; su token actual dura hasta una hora.</p>
      </section>

      <section aria-labelledby="t-cuentas" className={s.seccion}>
        <h2 id="t-cuentas">Cuentas por app</h2>
        {APPS.map((app) => {
          const c = cuentasDe[app.id];
          return (
            <div key={app.id} className={s.bloque}>
              <h3>{app.nombre}</h3>
              {!c.ok ? (
                <p className={s.alerta} role="status">
                  ⚠ No se pudieron leer las cuentas de {app.nombre}. Revisa el permiso de Atrium en {app.proyecto}.
                </p>
              ) : c.c.length === 0 ? (
                <p className={s.ayuda}>Sin cuentas.</p>
              ) : (
                <div className={s.tabla} tabIndex={0} role="region" aria-label={`Tabla de cuentas de ${app.nombre}`}>
                  <table>
                    <thead>
                      <tr>
                        <th scope="col">Correo</th>
                        <th scope="col">Proveedor</th>
                        <th scope="col">Alta</th>
                        <th scope="col">Último acceso</th>
                        <th scope="col">Acceso</th>
                      </tr>
                    </thead>
                    <tbody>
                      {c.c.map((u) => {
                        const ok = modos[app.id] === "abierta" || enLista(u.correo, app.id);
                        return (
                          <tr key={u.uid}>
                            <th scope="row">{u.correo || "(sin correo)"}</th>
                            <td>{u.proveedores.join(", ") || "—"}</td>
                            <td>{fmt(u.alta)}</td>
                            <td>{fmt(u.ultimoAcceso)}</td>
                            <td>
                              <span className={ok ? s.ok : s.fuera}>
                                <span aria-hidden="true">{ok ? "●" : "▲"}</span>{" "}
                                {u.deshabilitada ? "Deshabilitada" : ok ? "Con acceso" : "Fuera de la lista"}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          );
        })}
      </section>
    </main>
  );
}

function SinPermiso() {
  return (
    <main className={s.pagina}>
      <h1 className={s.titulo}>Atrium</h1>
      <p>Esta cuenta no administra Atrium.</p>
    </main>
  );
}
