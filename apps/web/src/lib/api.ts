/**
 * Browser → API calls through the same-origin /api proxy (httpOnly cookies stay first-party).
 * Adds the CSRF client header, and on a 401 refreshes the session once and retries.
 */

export type ApiErrorBody = {
  code: string;
  message: { ar: string; en: string };
  details?: { fields?: string[] } & Record<string, unknown>;
};

export type ApiResult<T> =
  { ok: true; status: number; data: T } | { ok: false; status: number; error: ApiErrorBody | null };

export type User = {
  id: string;
  email: string;
  full_name: string;
  role: "parent" | "school_admin" | "admin";
  locale: "ar" | "en";
  organization_id: string | null;
  has_password: boolean;
  created_at: string;
};

const NO_REFRESH = new Set(["/api/auth/login", "/api/auth/register", "/api/auth/refresh", "/api/auth/logout"]);
let refreshing: Promise<boolean> | null = null;

function refreshOnce(): Promise<boolean> {
  // single-flight: parallel 401s share one refresh (rotation would otherwise race)
  refreshing ??= fetch("/api/auth/refresh", { method: "POST", headers: { "X-Qamra-Client": "web" } })
    .then((r) => r.ok)
    .catch(() => false)
    .finally(() => {
      setTimeout(() => (refreshing = null), 0);
    });
  return refreshing;
}

export async function api<T>(path: string, init: { method?: string; json?: unknown } = {}): Promise<ApiResult<T>> {
  const doFetch = () =>
    fetch(path, {
      method: init.method ?? (init.json === undefined ? "GET" : "POST"),
      credentials: "same-origin",
      headers: {
        "X-Qamra-Client": "web",
        ...(init.json === undefined ? {} : { "Content-Type": "application/json" }),
      },
      body: init.json === undefined ? undefined : JSON.stringify(init.json),
    });

  let res: Response;
  try {
    res = await doFetch();
    if (res.status === 401 && !NO_REFRESH.has(path) && (await refreshOnce())) {
      res = await doFetch();
    }
  } catch {
    return { ok: false, status: 0, error: null }; // network
  }
  if (res.status === 204) return { ok: true, status: 204, data: undefined as T };
  const body = await res.json().catch(() => null);
  if (res.ok) return { ok: true, status: res.status, data: body as T };
  return { ok: false, status: res.status, error: (body?.error as ApiErrorBody) ?? null };
}

export function errorText(error: ApiErrorBody | null, locale: string, fallback: string): string {
  if (!error) return fallback;
  return locale === "ar" ? error.message.ar : error.message.en;
}

/** Only same-site relative paths: never redirect to another origin. */
export function safeNext(value: string | null | undefined, fallback: string): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\")) return fallback;
  return value;
}
