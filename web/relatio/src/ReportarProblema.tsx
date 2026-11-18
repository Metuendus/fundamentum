"use client";

import { useId, useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { aCaptura, tomarCaptura, type Captura } from "./captura.ts";
import { LIMITES, limpiarUrl, validarCampos, type Campos, type Errores, type Reporte } from "./contrato.ts";
import { enviarReporte } from "./enviar.ts";

export type ReportarProblemaProps = {
  /** Id de la app en Relatio: `iterum`, `domi`, `vocatio`, `expensum`. */
  app: string;
  /** URL pública de Relatio, p. ej. `https://relatio-….run.app`. */
  relatioUrl: string;
  /** ID token de Firebase de la sesión actual, o `null` si ya no hay sesión. */
  obtenerToken: () => Promise<string | null>;
  /** Correo de la sesión, para el aviso «se incluirá tu correo». */
  correo?: string | null;
  /** Versión de la build (p. ej. el SHA corto), para el issue. */
  version?: string;
  /** Oculta el botón, p. ej. en `/demo` o sin sesión. */
  oculto?: boolean;
};

type Estado =
  | { fase: "editando"; mensaje?: string }
  | { fase: "enviando" }
  | { fase: "enviado"; duplicado: boolean };

const VACIO: Campos = { titulo: "", que: "", cuando: "", adicional: "" };

function contexto(version?: string): Reporte["contexto"] {
  const oscuro =
    document.documentElement.dataset.theme === "dark" ||
    (!document.documentElement.dataset.theme && window.matchMedia?.("(prefers-color-scheme: dark)").matches);
  return {
    navegador: navigator.userAgent.slice(0, 300),
    pantalla: `${window.innerWidth}x${window.innerHeight}@${window.devicePixelRatio || 1}`,
    tema: oscuro ? "oscuro" : "claro",
    idioma: navigator.language,
    ...(version ? { version } : {}),
  };
}

/** Botón flotante y formulario «Reportar un problema». Estilos en `@fundamentum/relatio/estilos.css`. */
export function ReportarProblema({ app, relatioUrl, obtenerToken, correo, version, oculto }: ReportarProblemaProps) {
  const dialogo = useRef<HTMLDialogElement>(null);
  const archivo = useRef<HTMLInputElement>(null);
  const id = useId();
  const [campos, setCampos] = useState<Campos>(VACIO);
  const [errores, setErrores] = useState<Errores>({});
  const [avisar, setAvisar] = useState(false);
  const [captura, setCaptura] = useState<Captura | null>(null);
  const [capturando, setCapturando] = useState(false);
  const [errorCaptura, setErrorCaptura] = useState("");
  const [estado, setEstado] = useState<Estado>({ fase: "editando" });

  if (oculto) return null;

  const abrir = () => {
    setEstado({ fase: "editando" });
    dialogo.current?.showModal();
  };

  const cerrar = () => {
    dialogo.current?.close();
    if (estado.fase === "enviado") {
      setCampos(VACIO);
      setAvisar(false);
      setCaptura(null);
      setErrores({});
      setEstado({ fase: "editando" });
    }
  };

  const cambiar = (campo: keyof Campos) => (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setCampos((c) => ({ ...c, [campo]: e.target.value }));
    if (errores[campo]) setErrores((er) => ({ ...er, [campo]: undefined }));
  };

  const usarImagen = async (obtener: () => Promise<Blob>) => {
    setErrorCaptura("");
    setCapturando(true);
    try {
      const c = await aCaptura(await obtener());
      if (c.bytes > LIMITES.captura) throw new Error("La imagen pesa más de 5 MB. Adjunta una más ligera.");
      setCaptura(c);
    } catch (e) {
      setErrorCaptura(e instanceof Error ? e.message : "No pudimos tomar la captura. Adjunta un archivo.");
    } finally {
      setCapturando(false);
    }
  };

  const adjuntar = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (f) void usarImagen(async () => f);
  };

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    const er = validarCampos(campos);
    setErrores(er);
    if (Object.keys(er).length > 0) {
      dialogo.current?.querySelector<HTMLElement>("[aria-invalid='true']")?.focus();
      return;
    }
    setEstado({ fase: "enviando" });
    const token = await obtenerToken();
    if (!token) {
      setEstado({ fase: "editando", mensaje: "Tu sesión expiró. Vuelve a entrar e intenta de nuevo." });
      return;
    }
    const r = await enviarReporte(relatioUrl, token, {
      app,
      ...(campos.titulo.trim() ? { titulo: campos.titulo.trim() } : {}),
      que: campos.que.trim(),
      cuando: campos.cuando.trim(),
      ...(campos.adicional.trim() ? { adicional: campos.adicional.trim() } : {}),
      avisar,
      pagina: limpiarUrl(window.location.href),
      contexto: contexto(version),
      ...(captura ? { captura: { tipo: captura.tipo, datos: captura.datos } } : {}),
    });
    setEstado(r.ok ? { fase: "enviado", duplicado: r.duplicado } : { fase: "editando", mensaje: r.mensaje });
  };

  const campo = (nombre: keyof Campos) => ({
    id: `${id}-${nombre}`,
    value: campos[nombre],
    onChange: cambiar(nombre),
    "aria-invalid": errores[nombre] ? true : undefined,
    "aria-describedby": errores[nombre] ? `${id}-${nombre}-error` : undefined,
  });

  const error = (nombre: keyof Campos) =>
    errores[nombre] ? (
      <p id={`${id}-${nombre}-error`} className="fr-error">
        {errores[nombre]}
      </p>
    ) : null;

  const enviando = estado.fase === "enviando";

  return (
    <div className="fr-raiz" data-fr-reporte="">
      <button type="button" className="fr-flotante" onClick={abrir} aria-label="Reportar un problema" title="Reportar un problema">
        <IconoBicho />
      </button>

      <dialog ref={dialogo} className="fr-dialogo" aria-labelledby={`${id}-titulo`} onClose={cerrar}>
        <div className="fr-encabezado">
          <h2 id={`${id}-titulo`} className="fr-h2">
            Reportar un problema
          </h2>
          <button type="button" className="fr-cerrar" onClick={cerrar} aria-label="Cerrar">
            <IconoCerrar />
          </button>
        </div>

        {estado.fase === "enviado" ? (
          <div className="fr-enviado" role="status">
            <p className="fr-p">
              {estado.duplicado
                ? "Ya teníamos este reporte; agregamos tus detalles al que estaba abierto."
                : "Gracias. Recibimos tu reporte y lo vamos a revisar."}
            </p>
            {avisar ? <p className="fr-nota">Te escribiremos cuando quede resuelto.</p> : null}
            <div className="fr-acciones">
              <button type="button" className="fr-primario" onClick={cerrar} autoFocus>
                Cerrar
              </button>
            </div>
          </div>
        ) : (
          <form className="fr-form" onSubmit={enviar} noValidate>
            <p className="fr-p fr-suave">Cuéntanos qué encontraste. Lo convertimos en un ticket para el equipo automáticamente.</p>

            <label className="fr-etiqueta" htmlFor={`${id}-titulo-campo`}>
              Título (opcional)
            </label>
            <input
              {...campo("titulo")}
              id={`${id}-titulo-campo`}
              className="fr-campo"
              placeholder="Ej: El botón de guardar no responde"
              maxLength={LIMITES.titulo}
              autoFocus
            />
            {error("titulo")}

            <label className="fr-etiqueta" htmlFor={`${id}-que`}>
              ¿Qué está pasando?
            </label>
            <textarea {...campo("que")} className="fr-campo" rows={3} required placeholder="Describe el problema con el mayor detalle posible" />
            {error("que")}

            <label className="fr-etiqueta" htmlFor={`${id}-cuando`}>
              ¿Cuándo ocurre?
            </label>
            <input {...campo("cuando")} className="fr-campo" required placeholder="Ej: siempre, solo al guardar, la primera vez que inicio sesión" />
            {error("cuando")}

            <label className="fr-etiqueta" htmlFor={`${id}-adicional`}>
              Información adicional (opcional)
            </label>
            <textarea {...campo("adicional")} className="fr-campo" rows={3} placeholder="Pasos para reproducirlo, navegador o cualquier otro detalle" />
            {error("adicional")}

            <fieldset className="fr-grupo">
              <legend className="fr-etiqueta">Captura de pantalla (opcional)</legend>
              {captura ? (
                <div className="fr-vista">
                  {/* eslint-disable-next-line @next/next/no-img-element -- data URL local, sin optimizar */}
                  <img src={captura.vista} alt="Vista previa de la captura" className="fr-miniatura" />
                  <button type="button" className="fr-secundario" onClick={() => setCaptura(null)}>
                    Quitar captura
                  </button>
                </div>
              ) : (
                <div className="fr-fila">
                  <button type="button" className="fr-secundario" onClick={() => void usarImagen(tomarCaptura)} disabled={capturando}>
                    <IconoCamara /> {capturando ? "Tomando captura…" : "Tomar captura de pantalla"}
                  </button>
                  <button type="button" className="fr-secundario fr-punteado" onClick={() => archivo.current?.click()} disabled={capturando}>
                    <IconoImagen /> Adjuntar archivo
                  </button>
                  <input ref={archivo} type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={adjuntar} />
                </div>
              )}
              {errorCaptura ? (
                <p className="fr-error" role="alert">
                  {errorCaptura}
                </p>
              ) : null}
            </fieldset>

            <label className="fr-casilla">
              <input type="checkbox" checked={avisar} onChange={(e) => setAvisar(e.target.checked)} />
              <span>¿Quieres que te avisemos por correo cuando resolvamos este problema?</span>
            </label>

            <p className="fr-nota">
              Se incluirá automáticamente {correo ? <>tu correo ({correo})</> : "tu correo"} y la página donde estás para ayudar a
              diagnosticar el problema.
            </p>

            {estado.fase === "editando" && estado.mensaje ? (
              <p className="fr-error" role="alert">
                {estado.mensaje}
              </p>
            ) : null}

            <div className="fr-acciones">
              <button type="button" className="fr-secundario" onClick={cerrar}>
                Cancelar
              </button>
              <button type="submit" className="fr-primario" disabled={enviando} aria-busy={enviando || undefined}>
                {enviando ? "Enviando…" : "Enviar reporte"}
              </button>
            </div>
          </form>
        )}
      </dialog>
    </div>
  );
}

const svg = { width: 20, height: 20, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true } as const;

function IconoBicho() {
  return (
    <svg {...svg} width={24} height={24}>
      <path d="m8 2 1.88 1.88M14.12 3.88 16 2M9 7.13v-1a3 3 0 1 1 6 0v1" />
      <path d="M12 20c-3.3 0-6-2.7-6-6v-3a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v3c0 3.3-2.7 6-6 6M12 20v-9" />
      <path d="M6.53 9C4.6 8.8 3 7.1 3 5M6 13H2M3 21c0-2.1 1.7-3.9 3.8-4M20.97 5c0 2.1-1.6 3.8-3.5 4M22 13h-4M17.2 17c2.1.1 3.8 1.9 3.8 4" />
    </svg>
  );
}

function IconoCerrar() {
  return (
    <svg {...svg}>
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  );
}

function IconoCamara() {
  return (
    <svg {...svg} width={18} height={18}>
      <path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3z" />
      <circle cx="12" cy="13" r="3" />
    </svg>
  );
}

function IconoImagen() {
  return (
    <svg {...svg} width={18} height={18}>
      <rect width="18" height="18" x="3" y="3" rx="2" />
      <circle cx="9" cy="9" r="2" />
      <path d="m21 15-3.09-3.09a2 2 0 0 0-2.82 0L6 21" />
    </svg>
  );
}
