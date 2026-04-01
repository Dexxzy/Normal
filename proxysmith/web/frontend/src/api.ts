import type {
  ValidateResponse,
  GenerateResponse,
  ConfigSummaryResponse,
  Target,
} from "./types";

const BASE = "/api";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  validate: (toml: string) =>
    post<ValidateResponse>("/validate", { toml }),

  generate: (toml: string, targets: Target[]) =>
    post<GenerateResponse>("/generate", { toml, targets }),

  summary: (toml: string) =>
    post<ConfigSummaryResponse>("/summary", { toml }),

  downloadUrl: () => `${BASE}/generate/download`,
};
