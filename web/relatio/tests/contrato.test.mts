import assert from "node:assert/strict";
import { test } from "node:test";
import { bytesDeBase64, LIMITES, limpiarUrl, validarCampos } from "../src/contrato.ts";

const base = { titulo: "", que: "No guarda", cuando: "Siempre", adicional: "" };

test("pide qué pasa y cuándo; el título y lo adicional son opcionales", () => {
  assert.deepEqual(validarCampos(base), {});
  const e = validarCampos({ ...base, que: "  ", cuando: "" });
  assert.ok(e.que && e.cuando);
  assert.equal(e.titulo, undefined);
});

test("respeta los límites de longitud", () => {
  const e = validarCampos({ ...base, titulo: "x".repeat(LIMITES.titulo + 1), adicional: "x".repeat(LIMITES.adicional + 1) });
  assert.ok(e.titulo && e.adicional);
});

test("la página no lleva query ni fragmento (tokens de invitación, códigos)", () => {
  assert.equal(limpiarUrl("https://iterum.josecarloscorona.dev/invitar/abc?t=SECRETO#x"), "https://iterum.josecarloscorona.dev/invitar/abc");
  assert.equal(limpiarUrl("no es url"), "");
});

test("tapa los segmentos secretos de las rutas privadas", () => {
  const rutas = ["/invitar/:viaje/:token", "/v/:enlace"];
  assert.equal(limpiarUrl("https://i.dev/invitar/v1/AbC_123?x=1", rutas), "https://i.dev/invitar/[viaje]/[token]");
  assert.equal(limpiarUrl("https://i.dev/v/xyz", rutas), "https://i.dev/v/[enlace]");
  assert.equal(limpiarUrl("https://i.dev/viaje/v1", rutas), "https://i.dev/viaje/v1");
});

test("calcula los bytes de un base64 sin decodificarlo", () => {
  assert.equal(bytesDeBase64(Buffer.from("hola").toString("base64")), 4);
  assert.equal(bytesDeBase64(Buffer.from("hola!").toString("base64")), 5);
  assert.equal(bytesDeBase64(Buffer.from("hola!!").toString("base64")), 6);
});
