import assert from "node:assert/strict";
import { test } from "node:test";
import { correoValido, esApp, esModo, normalizarCorreo, ordenarPases, vigente } from "../src/lib/acceso.ts";

test("normaliza y valida correos", () => {
  assert.equal(normalizarCorreo("  Ana@X.com "), "ana@x.com");
  assert.ok(correoValido("ana@x.com"));
  assert.ok(!correoValido("ana@x"));
  assert.ok(!correoValido("a b@x.com"));
});

test("solo acepta apps y modos conocidos", () => {
  assert.ok(esApp("domi") && !esApp("otra"));
  assert.ok(esModo("abierta") && !esModo("cerrada"));
});

test("un permiso vencido ya no deja entrar, como en el portero", () => {
  const ahora = new Date("2026-10-29T12:00:00Z");
  const base = { origen: "invitacion" as const, alta: "2026-10-01T00:00:00Z", nota: "" };
  assert.ok(vigente({ ...base, vence: null }, ahora));
  assert.ok(vigente({ ...base, vence: "2026-10-30T00:00:00Z" }, ahora));
  assert.ok(!vigente({ ...base, vence: "2026-10-28T00:00:00Z" }, ahora));
  assert.ok(!vigente(undefined, ahora));
});

test("ordena la lista por correo", () => {
  const pases = ordenarPases([{ correo: "b@x.com", apps: {} }, { correo: "a@x.com", apps: {} }]);
  assert.deepEqual(pases.map((p) => p.correo), ["a@x.com", "b@x.com"]);
});
