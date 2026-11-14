const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
const TOKEN_KEY = "bis_saathi_token";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export const tokenStore = {
  get: (): string | null => (typeof window === "undefined" ? null : window.localStorage.getItem(TOKEN_KEY)),
  set: (token: string) => window.localStorage.setItem(TOKEN_KEY, token),
  clear: () => window.localStorage.removeItem(TOKEN_KEY),
  subscribe: (listener: () => void): (() => void) => {
    const onStorage = (event: StorageEvent) => {
      if (event.key === TOKEN_KEY) listener();
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  },
};

type UnauthorizedHandler = () => void;
let onUnauthorized: UnauthorizedHandler | null = null;
export function setUnauthorizedHandler(handler: UnauthorizedHandler | null) {
  onUnauthorized = handler;
}

async function parseError(res: Response): Promise<ApiError> {
  let message = `Request failed (${res.status})`;
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") message = body.detail;
  } catch {
    /* non-JSON error body */
  }
  if (res.status === 503 && message.startsWith("Request failed")) message = "The service is temporarily unavailable.";
  return new ApiError(message, res.status);
}

async function request(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError("Cannot reach the BIS SAATHI server. Check that the backend is running.", 0);
  }
  if (res.status === 401 && token) onUnauthorized?.();
  if (!res.ok) throw await parseError(res);
  return res;
}

export const api = {
  async get<T>(path: string, params?: Record<string, string | number | boolean | undefined | null>): Promise<T> {
    const qs = params
      ? "?" +
        new URLSearchParams(
          Object.entries(params)
            .filter(([, v]) => v !== undefined && v !== null && v !== "")
            .map(([k, v]) => [k, String(v)]),
        ).toString()
      : "";
    return (await request(path + (qs === "?" ? "" : qs))).json();
  },
  async post<T>(path: string, body?: unknown): Promise<T> {
    const res = await request(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
    return res.status === 204 ? (undefined as T) : res.json();
  },
  async patch<T>(path: string, body?: unknown): Promise<T> {
    return (await request(path, { method: "PATCH", body: JSON.stringify(body ?? {}) })).json();
  },
  async put<T>(path: string, body: unknown): Promise<T> {
    return (await request(path, { method: "PUT", body: JSON.stringify(body) })).json();
  },
  async delete(path: string): Promise<void> {
    await request(path, { method: "DELETE" });
  },
  async upload<T>(path: string, form: FormData): Promise<T> {
    return (await request(path, { method: "POST", body: form })).json();
  },
  async download(path: string, fallbackName: string): Promise<void> {
    const res = await request(path);
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    const match = /filename="?([^"]+)"?/.exec(disposition);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = match?.[1] || fallbackName;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
};
