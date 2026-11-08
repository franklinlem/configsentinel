export type Row = Record<string, any>;
export type Listing = { items: Row[]; next_cursor?: string };
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
export function getCsrf(): string {
  try {
    return localStorage.getItem("cs_csrf") || sessionStorage.getItem("cs_csrf") || "";
  } catch {
    return "";
  }
}

export function setCsrf(token: string): void {
  try { localStorage.setItem("cs_csrf", token); } catch {}
  try { sessionStorage.setItem("cs_csrf", token); } catch {}
}

export function clearCsrf(): void {
  try { localStorage.removeItem("cs_csrf"); } catch {}
  try { sessionStorage.removeItem("cs_csrf"); } catch {}
}

export async function api<T = Row>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const res = await fetch("/api/v1" + path, {
    method,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": getCsrf(),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok)
    throw new ApiError(
      res.status,
      data.detail || "Não foi possível concluir a operação",
    );
  return data;
}
export const date = (v: string | null | undefined) =>
  v
    ? new Date(v).toLocaleString("pt-BR", {
        dateStyle: "short",
        timeStyle: "medium",
      })
    : "Aguardando coleta";
export const labels: Record<string, string> = {
  baseline: "Baseline inicial",
  missing_initial: "Ausente na primeira coleta",
  created: "Arquivo criado",
  modified: "Conteúdo alterado",
  deleted: "Arquivo removido",
  unreadable: "Falha de leitura",
  restored: "Arquivo restaurado",
  recovered: "Leitura recuperada",
  metadata_changed: "Metadados alterados",
  unstable: "Arquivo instável",
  agent_offline: "Agente offline",
  collection_delayed: "Coleta atrasada",
  queue_high: "Fila próxima do limite",
  clock_skew: "Relógio divergente",
  online: "Online",
  offline: "Offline",
  delayed: "Coleta atrasada",
  not_installed: "Sem agente",
};
