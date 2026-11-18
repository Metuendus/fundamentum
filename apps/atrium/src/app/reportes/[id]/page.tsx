import Link from "next/link";
import { notFound } from "next/navigation";
import { APPS } from "@/lib/acceso";
import { administrador, SinAcceso } from "@/lib/identidad";
import { reportes } from "@/lib/reportes";
import s from "../../page.module.css";

export const dynamic = "force-dynamic";

const fecha = new Intl.DateTimeFormat("es-MX", { dateStyle: "long", timeStyle: "short", timeZone: "America/Mexico_City" });

/** Destino del enlace «Ver captura en Atrium» de cada issue. */
export default async function Reporte({ params }: { params: Promise<{ id: string }> }) {
  try {
    await administrador();
  } catch (e) {
    if (e instanceof SinAcceso) return <p className={s.pagina}>Esta cuenta no administra Atrium.</p>;
    throw e;
  }
  const { id } = await params;
  const r = await reportes().uno(id);
  if (!r) notFound();
  const app = APPS.find((a) => a.id === r.app)?.nombre ?? r.app;

  return (
    <main className={s.pagina}>
      <header className={s.cabecera}>
        <div>
          <h1 className={s.titulo}>{r.titulo}</h1>
          <p className={s.sub}>
            {app} · {fecha.format(new Date(r.creado))} · {r.correo || "sin correo"}
          </p>
        </div>
        <p className={s.sub}>
          <Link href="/reportes">Todos los reportes</Link>
        </p>
      </header>

      <section aria-labelledby="t-detalle" className={s.seccion}>
        <h2 id="t-detalle">Detalle</h2>
        <ul>
          <li>
            Issue: <a href={r.issueUrl}>{r.repo}#{r.issue}</a>
          </li>
          <li>Página: {r.pagina || "—"}</li>
          <li>Avisar por correo: {r.avisar ? "Sí" : "No"}</li>
        </ul>
      </section>

      <section aria-labelledby="t-captura" className={s.seccion}>
        <h2 id="t-captura">Captura</h2>
        {r.captura ? (
          // eslint-disable-next-line @next/next/no-img-element -- imagen privada servida por la ruta protegida
          <img src={`/reportes/${r.id}/captura`} alt={`Captura de pantalla del reporte de ${app}`} style={{ maxWidth: "100%", height: "auto", border: "1px solid var(--at-line)", borderRadius: 8 }} />
        ) : (
          <p className={s.ayuda}>Este reporte no trae captura.</p>
        )}
      </section>
    </main>
  );
}
