import { TIPOS_CAPTURA, type TipoCaptura } from "./contrato.ts";

export type Captura = { tipo: TipoCaptura; datos: string; vista: string; bytes: number };

const esperarCuadro = () => new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));

/**
 * Captura de lo que se ve en pantalla, dibujada desde el DOM (sin pedir permiso de compartir
 * pantalla). El widget se excluye con `data-fr-reporte`. Los iframes de otros orígenes (mapas)
 * pueden salir en blanco: para eso está «Adjuntar archivo».
 */
export async function tomarCaptura(): Promise<Blob> {
  const { domToBlob } = await import("modern-screenshot");
  await esperarCuadro();
  const raiz = document.documentElement;
  const blob = await domToBlob(raiz, {
    type: "image/webp",
    quality: 0.85,
    width: window.innerWidth,
    height: window.innerHeight,
    scale: Math.min(window.devicePixelRatio || 1, 2),
    filter: (n) => !(n instanceof Element && n.hasAttribute("data-fr-reporte")),
    style: { transform: `translate(${-window.scrollX}px, ${-window.scrollY}px)` },
  });
  if (!blob) throw new Error("La captura salió vacía.");
  return blob;
}

export function tipoValido(tipo: string): tipo is TipoCaptura {
  return (TIPOS_CAPTURA as readonly string[]).includes(tipo);
}

export async function aCaptura(blob: Blob): Promise<Captura> {
  const tipo = blob.type || "image/png";
  if (!tipoValido(tipo)) throw new Error("Solo se aceptan imágenes PNG, JPG o WebP.");
  const url = await new Promise<string>((ok, mal) => {
    const lector = new FileReader();
    lector.onload = () => ok(String(lector.result));
    lector.onerror = () => mal(lector.error);
    lector.readAsDataURL(blob);
  });
  return { tipo, datos: url.slice(url.indexOf(",") + 1), vista: url, bytes: blob.size };
}
