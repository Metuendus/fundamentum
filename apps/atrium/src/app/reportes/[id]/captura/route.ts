import { administrador, SinAcceso } from "@/lib/identidad";
import { reportes } from "@/lib/reportes";

export const dynamic = "force-dynamic";

/** La captura de un reporte, solo para administradores (además de IAP). Nunca sale del bucket privado de otra forma. */
export async function GET(_: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    await administrador();
  } catch (e) {
    if (e instanceof SinAcceso) return new Response("Sin acceso", { status: 403 });
    throw e;
  }
  const { id } = await params;
  const r = await reportes().uno(id);
  const img = r?.captura ? await reportes().captura(r.captura) : null;
  if (!img) return new Response("Sin captura", { status: 404 });
  return new Response(new Uint8Array(img.datos), {
    headers: {
      "content-type": img.tipo,
      "cache-control": "private, no-store",
      "x-content-type-options": "nosniff",
      "content-security-policy": "default-src 'none'",
    },
  });
}
