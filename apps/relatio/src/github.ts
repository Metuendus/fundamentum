import { createSign } from "node:crypto";

export type IssueCreado = { numero: number; url: string };

/** Lo único que Relatio hace en GitHub. La implementación real usa la GitHub App «Relatio». */
export interface GitHub {
  crearIssue(repo: string, issue: { title: string; body: string; labels: string[] }): Promise<IssueCreado>;
  comentar(repo: string, numero: number, cuerpo: string): Promise<void>;
}

const API = "https://api.github.com";
const b64url = (b: Buffer | string) => Buffer.from(b).toString("base64url");

/** JWT de la App (RS256, 9 min de vida, 60 s antes por desfase de reloj). */
export function jwtDeApp(appId: string, llavePem: string, ahora = Date.now()): string {
  const iat = Math.floor(ahora / 1000) - 60;
  const cabecera = b64url(JSON.stringify({ alg: "RS256", typ: "JWT" }));
  const cuerpo = b64url(JSON.stringify({ iat, exp: iat + 540, iss: appId }));
  const firma = createSign("RSA-SHA256").update(`${cabecera}.${cuerpo}`).sign(llavePem);
  return `${cabecera}.${cuerpo}.${b64url(firma)}`;
}

export class ErrorGitHub extends Error {
  readonly estado: number;
  constructor(estado: number, mensaje: string) {
    super(mensaje);
    this.estado = estado;
  }
}

/**
 * Cliente de la GitHub App: pide un token de instalación por repo (dura 1 h, se reusa hasta 5 min
 * antes de vencer) y solo toca issues. La llave privada llega por Secret Manager, nunca al log.
 */
export class GitHubApp implements GitHub {
  private tokens = new Map<string, { token: string; vence: number }>();
  private readonly appId: string;
  private readonly llave: string;
  private readonly pedir: typeof fetch;

  constructor(appId: string, llave: string, pedir: typeof fetch = fetch) {
    this.appId = appId;
    this.llave = llave;
    this.pedir = pedir;
  }

  private async llamar(ruta: string, auth: string, init: { method?: string; body?: unknown } = {}): Promise<unknown> {
    const r = await this.pedir(`${API}${ruta}`, {
      method: init.method ?? "GET",
      headers: {
        accept: "application/vnd.github+json",
        authorization: auth,
        "x-github-api-version": "2022-11-28",
        "user-agent": "relatio",
        ...(init.body ? { "content-type": "application/json" } : {}),
      },
      body: init.body ? JSON.stringify(init.body) : undefined,
    });
    if (!r.ok) throw new ErrorGitHub(r.status, `GitHub ${init.method ?? "GET"} ${ruta}: ${r.status}`);
    return r.status === 204 ? null : r.json();
  }

  private async token(repo: string): Promise<string> {
    const guardado = this.tokens.get(repo);
    if (guardado && guardado.vence - 5 * 60_000 > Date.now()) return guardado.token;
    const jwt = `Bearer ${jwtDeApp(this.appId, this.llave)}`;
    const inst = (await this.llamar(`/repos/${repo}/installation`, jwt)) as { id: number };
    const t = (await this.llamar(`/app/installations/${inst.id}/access_tokens`, jwt, {
      method: "POST",
      body: { repositories: [repo.split("/")[1]], permissions: { issues: "write" } },
    })) as { token: string; expires_at: string };
    this.tokens.set(repo, { token: t.token, vence: Date.parse(t.expires_at) });
    return t.token;
  }

  async crearIssue(repo: string, issue: { title: string; body: string; labels: string[] }): Promise<IssueCreado> {
    const r = (await this.llamar(`/repos/${repo}/issues`, `token ${await this.token(repo)}`, {
      method: "POST",
      body: issue,
    })) as { number: number; html_url: string };
    return { numero: r.number, url: r.html_url };
  }

  async comentar(repo: string, numero: number, cuerpo: string): Promise<void> {
    await this.llamar(`/repos/${repo}/issues/${numero}/comments`, `token ${await this.token(repo)}`, {
      method: "POST",
      body: { body: cuerpo },
    });
  }
}

/** Fuera de la nube: no toca GitHub, solo registra lo que habría creado. */
export class GitHubEnMemoria implements GitHub {
  creados: { repo: string; title: string; body: string; labels: string[] }[] = [];
  comentarios: { repo: string; numero: number; cuerpo: string }[] = [];

  async crearIssue(repo: string, issue: { title: string; body: string; labels: string[] }): Promise<IssueCreado> {
    this.creados.push({ repo, ...issue });
    const numero = this.creados.length;
    return { numero, url: `https://github.com/${repo}/issues/${numero}` };
  }

  async comentar(repo: string, numero: number, cuerpo: string): Promise<void> {
    this.comentarios.push({ repo, numero, cuerpo });
  }
}
