import assert from "node:assert/strict";
import { generateKeyPairSync, createVerify } from "node:crypto";
import { test } from "node:test";
import { AlmacenEnMemoria, capturasDe } from "../src/almacen.ts";
import { TOPES } from "../src/config.ts";
import { validarReporte } from "../src/contrato.ts";
import { GitHubEnMemoria, jwtDeApp } from "../src/github.ts";
import { armarIssue, escapar, tituloDe } from "../src/issue.ts";
import { recibir, type Dependencias } from "../src/recibir.ts";
import { origenPermitido } from "../src/servidor.ts";

const base = {
  app: "domi",
  que: "El mapa no carga @alguien",
  cuando: "Siempre",
  avisar: true,
  pagina: "https://domi.josecarloscorona.dev/hoy?token=SECRETO",
  contexto: { navegador: "Firefox", pantalla: "1280x720@2", tema: "oscuro", idioma: "es-MX" },
};

function deps(extra: Partial<Dependencias> = {}) {
  const m = new AlmacenEnMemoria();
  const gh = new GitHubEnMemoria();
  let n = 0;
  const d: Dependencias = {
    verificar: async (token, proyecto) => (token === "bueno" && proyecto === "domi-mx" ? { uid: "u1", correo: "ana@x.com" } : null),
    almacen: m,
    capturas: capturasDe(m),
    github: gh,
    atriumUrl: "https://atrium.example",
    ahora: () => new Date("2026-11-18T12:00:00Z"),
    nuevoId: () => `r${++n}`,
    ...extra,
  };
  return { d, m, gh };
}

test("valida lo obligatorio y limpia la página", () => {
  assert.equal(validarReporte({ ...base, que: " " }).ok, false);
  assert.equal(validarReporte({ ...base, cuando: undefined }).ok, false);
  assert.equal(validarReporte({ ...base, captura: { tipo: "image/gif", datos: "AAAA" } }).ok, false);
  const v = validarReporte(base);
  assert.ok(v.ok);
  if (v.ok) assert.equal(v.reporte.pagina, "https://domi.josecarloscorona.dev/hoy");
});

test("el texto de la persona no menciona ni inyecta HTML", () => {
  assert.equal(escapar("<b>@ana</b> closes #12 ana@x.com"), "&lt;b&gt;@\u200bana&lt;/b&gt; closes #\u200b12 ana@x.com");
  const v = validarReporte(base);
  assert.ok(v.ok);
  if (!v.ok) return;
  const i = armarIssue("domi", v.reporte, { id: "r1", correo: "ana@x.com", atriumUrl: "https://atrium.example", conCaptura: true });
  assert.ok(!i.body.includes("@alguien"));
  assert.ok(i.body.includes("https://atrium.example/reportes/r1"));
  assert.deepEqual(i.labels, ["origen:usuario", "tipo:bug", "requiere-triage", "avisar"]);
  assert.equal(tituloDe({ ...v.reporte, titulo: "Mapa" }), "[Reporte] Mapa");
});

test("crea el issue en el repo de la app verificada y guarda la captura en privado", async () => {
  const { d, m, gh } = deps();
  const datos = Buffer.from("png falso").toString("base64");
  const s = await recibir("bueno", { ...base, captura: { tipo: "image/png", datos } }, d);
  assert.equal(s.estado, 201);
  assert.equal(gh.creados[0].repo, "Metuendus/domi");
  assert.ok(gh.creados[0].body.includes("ana@x.com"));
  assert.ok(!gh.creados[0].body.includes(datos), "la imagen no va en el issue");
  assert.equal(m.registros[0].captura, "domi/2026-11/r1.png");
  assert.ok(m.archivos.has("domi/2026-11/r1.png"));
});

test("sin sesión válida o con otra app, no crea nada", async () => {
  const { d, gh } = deps();
  assert.equal((await recibir(null, base, d)).estado, 401);
  assert.equal((await recibir("malo", base, d)).estado, 401);
  assert.equal((await recibir("bueno", { ...base, app: "vocatio" }, d)).estado, 401);
  assert.equal((await recibir("bueno", { ...base, app: "otra" }, d)).estado, 400);
  assert.equal(gh.creados.length, 0);
});

test("el mismo reporte en 10 minutos se suma como comentario", async () => {
  const { d, gh } = deps();
  await recibir("bueno", base, d);
  const s = await recibir("bueno", { ...base, cuando: "Al abrir la app" }, d);
  assert.equal(s.estado, 200);
  assert.equal(s.cuerpo.duplicado, true);
  assert.equal(gh.creados.length, 1);
  assert.equal(gh.comentarios[0].numero, 1);
  const tarde = deps();
  await recibir("bueno", base, tarde.d);
  tarde.d.ahora = () => new Date(Date.parse("2026-11-18T12:00:00Z") + TOPES.duplicadoMs + 1000);
  assert.equal((await recibir("bueno", base, tarde.d)).estado, 201);
});

test("tope diario por persona", async () => {
  const { d } = deps();
  for (let i = 0; i < TOPES.porUsuario; i++) assert.equal((await recibir("bueno", { ...base, que: `Falla ${i}` }, d)).estado, 201);
  assert.equal((await recibir("bueno", { ...base, que: "Otra" }, d)).estado, 429);
});

test("el JWT de la App va firmado con RS256", () => {
  const { privateKey, publicKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
  const jwt = jwtDeApp("123", privateKey.export({ type: "pkcs8", format: "pem" }).toString(), Date.parse("2026-11-18T12:00:00Z"));
  const [c, b, f] = jwt.split(".");
  assert.ok(createVerify("RSA-SHA256").update(`${c}.${b}`).verify(publicKey, Buffer.from(f, "base64url")));
  const cuerpo = JSON.parse(Buffer.from(b, "base64url").toString());
  assert.equal(cuerpo.iss, "123");
  assert.equal(cuerpo.exp - cuerpo.iat, 540);
});

test("CORS solo para los orígenes de las apps", () => {
  assert.equal(origenPermitido("https://domi.josecarloscorona.dev", ["https://domi.josecarloscorona.dev"]), "https://domi.josecarloscorona.dev");
  assert.equal(origenPermitido("https://malo.com", ["https://domi.josecarloscorona.dev"]), null);
});
