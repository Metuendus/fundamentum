import Link from "next/link";
import { APPS } from "@/lib/acceso";
import { enNube } from "@/lib/config";
import { administrador, SinAcceso } from "@/lib/identidad";
import { reportes } from "@/lib/reportes";
import s from "../page.module.css";

export const dynamic = "force-dynamic";

const fecha = new Intl.DateTimeFormat("es-MX", { dateStyle: "medium", timeStyle: "short", timeZone: "America/Mexico_City" });
const nombre = (app: string) => APPS.find((a) => a.id === app)?.nombre ?? app;

export default async function Reportes() {
  let admin: string;
  try {
    admin = await administrador();
  } catch (e) {
    if (e instanceof SinAcceso) return <p className={s.pagina}>Esta cuenta no administra Atrium.</p>;
    throw e;
  }
  const lista = await reportes().recientes(100);

  return (
    <main className={s.pagina}>
      <header className={s.cabecera}>
        <div>
          <h1 className={s.titulo}>Reportes</h1>
          <p className={s.sub}>Lo que llega del botón «Reportar un problema» de las apps, vía Relatio.</p>
        </div>
        <p className={s.sub}>
          <Link href="/">Volver a Atrium</Link> · {enNube() ? admin : "Demostración"}
        </p>
      </header>

      <section aria-labelledby="t-reportes" className={s.seccion}>
        <h2 id="t-reportes">Últimos 100</h2>
        {lista.length === 0 ? (
          <p className={s.ayuda}>Todavía no hay reportes.</p>
        ) : (
          <div className={s.tabla} tabIndex={0} role="region" aria-label="Tabla de reportes">
            <table>
              <thead>
                <tr>
                  <th scope="col">Reporte</th>
                  <th scope="col">App</th>
                  <th scope="col">Quién</th>
                  <th scope="col">Fecha</th>
                  <th scope="col">Issue</th>
                  <th scope="col">Captura</th>
                </tr>
              </thead>
              <tbody>
                {lista.map((r) => (
                  <tr key={r.id}>
                    <th scope="row">
                      <Link href={`/reportes/${r.id}`}>{r.titulo}</Link>
                    </th>
                    <td>{nombre(r.app)}</td>
                    <td>{r.correo || "—"}</td>
                    <td>{fecha.format(new Date(r.creado))}</td>
                    <td>
                      <a href={r.issueUrl}>#{r.issue}</a>
                    </td>
                    <td>{r.captura ? "Sí" : "No"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
