let csrf = "";
export const setCsrf = (c: string) => { csrf = c; };
export async function api<T = any>(path: string, method = "GET", body?: any): Promise<T> {
  const r = await fetch(`/api/v1/admin${path}`, { method, credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(method !== "GET" ? { "X-CSRF-Token": csrf } : {}) }, body: body ? JSON.stringify(body) : undefined });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(typeof d.detail === "string" ? d.detail : "Request failed"), { status: r.status });
  return d;
}
export const money = (v: any, d = 2) => Number(v).toLocaleString("en-US", { maximumFractionDigits: d });
