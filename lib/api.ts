const BASE = ""; // same-origin; proxied by next.config.mjs
let token = "";
export const tg = () => (typeof window !== "undefined" ? (window as any).Telegram?.WebApp : undefined);

export async function login(): Promise<any> {
  const initData = tg()?.initData;
  if (!initData) throw new Error("not_in_telegram");
  const r = await fetch(`${BASE}/api/v1/auth/telegram`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ init_data: initData }) });
  if (!r.ok) throw new Error("auth_failed");
  const d = await r.json(); token = d.token; return d;
}

export async function api<T = any>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const r = await fetch(`${BASE}/api/v1${path}`, { ...init, headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...(init.headers || {}) } });
  if (r.status === 401 && retry) { await login(); return api<T>(path, init, false); }
  if (!r.ok) { const e = await r.json().catch(() => ({})); throw Object.assign(new Error(e?.detail?.message || e?.detail || "request_failed"), { code: e?.detail?.code }); }
  return r.json();
}
export const fmt = (v: string | number, d = 2) => Number(v).toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: 0 });
export const usd = (v: string | number) => "$" + Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
