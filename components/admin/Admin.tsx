"use client";
import { useEffect, useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { BarChart3, Bell, Coins, FileText, Gem, LogOut, Settings as Cog, Shield, Users as UsersIcon, Wallet as WalletIcon, ArrowLeftRight } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { api, money, setCsrf } from "../../lib/adminApi";

const COLORS = ["#705CF6", "#20B982", "#F7A23B", "#4B5BD8", "#E65A65", "#8A8D98"];
const Card = ({ children, className = "" }: any) => <div className={`bg-white border border-line rounded-2xl p-5 ${className}`}>{children}</div>;
const Btn = ({ children, kind = "p", ...p }: any) => <button {...p} className={`px-3.5 py-2 rounded-xl text-sm font-medium disabled:opacity-50 ${kind === "p" ? "bg-brand text-white" : kind === "d" ? "bg-bad text-white" : "bg-white border border-line"}`}>{children}</button>;
const Input = (p: any) => <input {...p} className={`px-3 py-2 rounded-xl border border-line bg-white outline-none focus:border-brand text-sm ${p.className || ""}`} />;
const Badge = ({ v }: { v: string }) => <span className={`text-xs px-2 py-0.5 rounded-full ${["active", "completed", "sent"].includes(v) ? "bg-ok/10 text-ok" : ["blocked", "frozen", "failed", "disabled"].includes(v) ? "bg-bad/10 text-bad" : "bg-line text-mute"}`}>{v}</span>;

function useGet<T = any>(path: string, deps: any[] = []) {
  const [d, setD] = useState<T | null>(null); const [err, setErr] = useState(""); const [n, setN] = useState(0);
  useEffect(() => { setErr(""); api<T>(path).then(setD).catch((e) => setErr(e.message)); }, [path, n, ...deps]);
  return { d, err, reload: () => setN((x) => x + 1) };
}
function Table({ cols, rows, onRow }: { cols: [string, (r: any) => any][]; rows: any[] | null; onRow?: (r: any) => void }) {
  if (!rows) return <div className="animate-pulse h-40 bg-line rounded-xl" />;
  if (!rows.length) return <div className="text-center text-mute py-10">No data</div>;
  return (<div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="text-left text-mute">{cols.map(([h]) => <th key={h} className="py-2 pr-4 font-medium">{h}</th>)}</tr></thead>
    <tbody>{rows.map((r, i) => <tr key={r.id || i} onClick={() => onRow?.(r)} className={`border-t border-line ${onRow ? "cursor-pointer hover:bg-bg" : ""}`}>{cols.map(([h, f]) => <td key={h} className="py-2.5 pr-4 align-top">{f(r)}</td>)}</tr>)}</tbody></table></div>);
}

/** Every sensitive action: reason + explicit confirmation (required by the backend, recorded in the audit log). */
function Action({ title, fields = [], onSubmit, onClose }: any) {
  const [v, setV] = useState<any>({}); const [reason, setReason] = useState(""); const [ok, setOk] = useState(false); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const go = async () => { setBusy(true); setErr(""); try { await onSubmit({ ...v, reason, confirm: true }); onClose(true); } catch (e: any) { setErr(e.message); } finally { setBusy(false); } };
  return (<div className="fixed inset-0 bg-black/40 grid place-items-center z-50 p-4"><Card className="w-full max-w-md space-y-3">
    <div className="font-semibold text-lg">{title}</div>
    {fields.map((f: any) => f.options ? <select key={f.key} className="w-full px-3 py-2 rounded-xl border border-line" value={v[f.key] ?? f.options[0]} onChange={(e) => setV({ ...v, [f.key]: e.target.value })}>{f.options.map((o: string) => <option key={o}>{o}</option>)}</select>
      : <Input key={f.key} className="w-full" placeholder={f.label} defaultValue={f.value} onChange={(e: any) => setV({ ...v, [f.key]: f.number ? e.target.value : e.target.value })} />)}
    <Input className="w-full" placeholder="Reason (required, saved to audit log)" value={reason} onChange={(e: any) => setReason(e.target.value)} />
    <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={ok} onChange={(e) => setOk(e.target.checked)} />I confirm this action</label>
    {err && <div className="text-bad text-sm">{err}</div>}
    <div className="flex justify-end gap-2"><Btn kind="s" onClick={() => onClose(false)}>Cancel</Btn><Btn disabled={busy || !ok || reason.trim().length < 3} onClick={go}>Confirm</Btn></div></Card></div>);
}

function Dashboard() {
  const [range, setRange] = useState("7d"); const { d, err } = useGet<any>(`/dashboard?range=${range}`, []);
  if (err) return <div className="text-bad">{err}</div>; if (!d) return <div className="animate-pulse h-64 bg-line rounded-2xl" />;
  const stats = [["Total Users", d.total_users], ["Active Users", d.active_users], ["Total Wallets", d.total_wallets], ["Transactions", d.total_transactions],
    ["Virtual Supply (value)", "$" + money(d.total_virtual_supply)], ["Daily Transfers", d.daily_transfers], ["New Registrations", d.new_registrations], ["Transfer Volume", "$" + money(d.transaction_volume)]];
  return (<div className="space-y-5"><div className="flex gap-2">{[["today", "Today"], ["7d", "7 Days"], ["30d", "30 Days"], ["90d", "90 Days"], ["all", "All Time"]].map(([k, l]) => <Btn key={k} kind={range === k ? "p" : "s"} onClick={() => setRange(k)}>{l}</Btn>)}</div>
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">{stats.map(([l, v]) => <Card key={l as string}><div className="text-mute text-sm">{l}</div><div className="text-2xl font-semibold mt-1">{v}</div></Card>)}</div>
    <div className="grid lg:grid-cols-2 gap-4">
      <Card><div className="font-medium mb-3">User Growth</div><div className="h-56"><ResponsiveContainer><AreaChart data={d.user_growth}><CartesianGrid stroke="#ECEDF1" vertical={false} /><XAxis dataKey="d" fontSize={11} /><YAxis fontSize={11} allowDecimals={false} /><Tooltip /><Area dataKey="v" stroke="#705CF6" fill="#705CF620" /></AreaChart></ResponsiveContainer></div></Card>
      <Card><div className="font-medium mb-3">Transaction Activity</div><div className="h-56"><ResponsiveContainer><BarChart data={d.transaction_activity}><CartesianGrid stroke="#ECEDF1" vertical={false} /><XAxis dataKey="d" fontSize={11} /><YAxis fontSize={11} allowDecimals={false} /><Tooltip /><Bar dataKey="count" fill="#705CF6" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div></Card>
      <Card><div className="font-medium mb-3">Asset Distribution (value)</div><div className="h-56"><ResponsiveContainer><PieChart><Pie data={d.asset_distribution.map((a: any) => ({ name: a.symbol, value: Number(a.value) }))} dataKey="value" innerRadius={55} outerRadius={85}>{d.asset_distribution.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % 6]} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer></div></Card>
      <Card><div className="font-medium mb-3">Virtual Supply</div><div className="h-56"><ResponsiveContainer><BarChart data={d.virtual_supply.map((a: any) => ({ s: a.symbol, v: Number(a.value) }))}><CartesianGrid stroke="#ECEDF1" vertical={false} /><XAxis dataKey="s" fontSize={11} /><YAxis fontSize={11} /><Tooltip /><Bar dataKey="v" fill="#20B982" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div></Card></div>
    <div className="text-xs text-mute">All figures are computed from PostgreSQL. Virtual (DEMO) units only.</div></div>);
}

function Users({ can }: any) {
  const [q, setQ] = useState(""); const [status, setStatus] = useState(""); const [sort, setSort] = useState("created_at"); const [sel, setSel] = useState<any>(null); const [act, setAct] = useState<any>(null);
  const { d, reload } = useGet<any[]>(`/users?q=${encodeURIComponent(q)}&status=${status}&sort=${sort}`);
  const det = useGet<any>(sel ? `/users/${sel}` : "/auth/me", [sel]);
  const done = (r: boolean) => { setAct(null); if (r) { reload(); det.reload(); } };
  return (<div className="space-y-4"><div className="flex gap-2 flex-wrap"><Input placeholder="Search username / ID" value={q} onChange={(e: any) => setQ(e.target.value)} />
    <select className="px-3 py-2 rounded-xl border border-line text-sm" value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All statuses</option><option>active</option><option>blocked</option></select>
    <select className="px-3 py-2 rounded-xl border border-line text-sm" value={sort} onChange={(e) => setSort(e.target.value)}><option value="created_at">Newest</option><option value="balance">Balance</option><option value="transactions">Transactions</option><option value="username">Username</option></select></div>
    <Card><Table rows={d} onRow={(r) => setSel(r.id)} cols={[["User", (r) => <div className="flex items-center gap-2">{r.photo_url ? <img src={r.photo_url} className="w-7 h-7 rounded-full" /> : <div className="w-7 h-7 rounded-full bg-brand text-white grid place-items-center text-xs">{(r.username || "?")[0]}</div>}@{r.username}</div>],
      ["Telegram ID", (r) => r.telegram_id], ["Internal ID", (r) => <span className="font-mono text-xs">{r.id.slice(0, 8)}</span>], ["Registered", (r) => r.registered_at.slice(0, 10)],
      ["Balance", (r) => "$" + money(r.total_balance)], ["Tx", (r) => r.transactions], ["Status", (r) => <Badge v={r.status} />]]} /></Card>
    {sel && det.d?.wallet && <Card className="space-y-3"><div className="flex justify-between"><div className="font-semibold text-lg">@{det.d.username} <Badge v={det.d.status} /></div><Btn kind="s" onClick={() => setSel(null)}>Close</Btn></div>
      <div className="text-sm text-mute">Wallet {det.d.wallet.public_id} · <Badge v={det.d.wallet.status} /> · Note: {det.d.note || "—"}</div>
      <div className="flex gap-2 flex-wrap">{det.d.balances.map((b: any) => <span key={b.symbol} className="px-2 py-1 bg-bg rounded-lg text-sm">{b.symbol} {money(b.amount, 8)}</span>)}</div>
      <div className="flex gap-2 flex-wrap">{can("users.block") && (det.d.status === "active" ? <Btn kind="d" onClick={() => setAct({ t: "Block user", f: (b: any) => api(`/users/${sel}/block`, "POST", b) })}>Block</Btn> : <Btn onClick={() => setAct({ t: "Unblock user", f: (b: any) => api(`/users/${sel}/unblock`, "POST", b) })}>Unblock</Btn>)}
        {can("users.note") && <Btn kind="s" onClick={() => setAct({ t: "Edit note", fields: [{ key: "note", label: "Note", value: det.d.note || "" }], f: (b: any) => api(`/users/${sel}/note`, "PUT", { note: b.note ?? "" }) })}>Add note</Btn>}</div>
      <Table rows={det.d.history} cols={[["Type", (r) => r.type], ["Asset", (r) => r.symbol], ["Amount", (r) => r.amount], ["Status", (r) => <Badge v={r.status} />], ["Time", (r) => r.created_at.slice(0, 16)]]} /></Card>}
    {act && <Action title={act.t} fields={act.fields} onSubmit={act.f} onClose={done} />}</div>);
}

function Wallets({ can }: any) {
  const [q, setQ] = useState(""); const { d, reload } = useGet<any[]>(`/wallets?q=${encodeURIComponent(q)}`); const [act, setAct] = useState<any>(null);
  return (<div className="space-y-4"><Input placeholder="Search wallet ID / username" value={q} onChange={(e: any) => setQ(e.target.value)} />
    <Card><Table rows={d} cols={[["Wallet", (r) => <span className="font-mono">{r.public_id}</span>], ["User", (r) => "@" + r.username], ["Total", (r) => "$" + money(r.total_balance)], ["Status", (r) => <Badge v={r.status} />],
      ["Actions", (r) => <div className="flex gap-1.5">
        {can("wallets.adjust") && <Btn kind="s" onClick={() => setAct({ t: "Adjust balance (DEMO)", fields: [{ key: "symbol", label: "Symbol (e.g. NUSD)" }, { key: "amount", label: "Amount" }, { key: "direction", options: ["credit", "debit"] }], f: (b: any) => api(`/wallets/${r.id}/adjust`, "POST", { ...b, direction: b.direction || "credit" }) })}>Adjust</Btn>}
        {can("wallets.freeze") && (r.status === "active" ? <Btn kind="d" onClick={() => setAct({ t: "Freeze wallet", f: (b: any) => api(`/wallets/${r.id}/freeze`, "POST", b) })}>Freeze</Btn> : <Btn onClick={() => setAct({ t: "Unfreeze wallet", f: (b: any) => api(`/wallets/${r.id}/unfreeze`, "POST", b) })}>Unfreeze</Btn>)}</div>]]} /></Card>
    {act && <Action title={act.t} fields={act.fields} onSubmit={act.f} onClose={(r: boolean) => { setAct(null); r && reload(); }} />}</div>);
}

function Assets({ can }: any) {
  const { d, reload } = useGet<any[]>("/assets"); const [act, setAct] = useState<any>(null); const [dist, setDist] = useState<any>(null);
  return (<div className="space-y-4">{can("assets.manage") && <Btn onClick={() => setAct({ t: "Create virtual asset", fields: [{ key: "symbol", label: "Symbol (A-Z0-9)" }, { key: "name", label: "Name" }, { key: "description", label: "Description" }, { key: "virtual_price", label: "Virtual price" }, { key: "max_supply", label: "Max supply (empty = unlimited)" }, { key: "category", options: ["nova", "popular", "stable"] }],
      f: (b: any) => api("/assets", "POST", { ...b, category: b.category || "nova", virtual_price: b.virtual_price || "0", max_supply: b.max_supply || null }) })}>+ New asset</Btn>}
    <Card><Table rows={d} cols={[["Asset", (r) => <b>{r.symbol} <span className="font-normal text-mute">{r.name}</span></b>], ["Price", (r) => r.price], ["Supply", (r) => `${money(r.total_supply, 4)} / ${r.max_supply ? money(r.max_supply, 0) : "∞"}`], ["Status", (r) => <Badge v={r.is_active ? "active" : "disabled"} />],
      ["Actions", (r) => <div className="flex gap-1.5"><Btn kind="s" onClick={async () => setDist({ s: r.symbol, rows: await api(`/assets/${r.symbol}/distribution`) })}>Distribution</Btn>
        {can("assets.manage") && <><Btn kind="s" onClick={() => setAct({ t: `Edit ${r.symbol}`, fields: [{ key: "virtual_price", label: "Price", value: r.price }, { key: "description", label: "Description", value: r.description }, { key: "icon", label: "Icon URL", value: r.icon || "" }, { key: "max_supply", label: "Max supply", value: r.max_supply || "" }],
          f: (b: any) => api(`/assets/${r.symbol}`, "PUT", { reason: b.reason, confirm: true, virtual_price: b.virtual_price || r.price, description: b.description ?? r.description, icon: b.icon || r.icon, max_supply: (b.max_supply ?? r.max_supply) || null }) })}>Edit</Btn>
          <Btn kind={r.is_active ? "d" : "p"} onClick={() => setAct({ t: r.is_active ? `Deactivate ${r.symbol}` : `Activate ${r.symbol}`, f: (b: any) => api(`/assets/${r.symbol}`, "PUT", { ...b, is_active: !r.is_active }) })}>{r.is_active ? "Deactivate" : "Activate"}</Btn></>}</div>]]} /></Card>
    {dist && <Card><div className="flex justify-between mb-2"><b>{dist.s} holders</b><Btn kind="s" onClick={() => setDist(null)}>Close</Btn></div><Table rows={dist.rows} cols={[["User", (r) => "@" + r.username], ["Wallet", (r) => r.wallet], ["Amount", (r) => r.amount]]} /></Card>}
    {act && <Action title={act.t} fields={act.fields} onSubmit={act.f} onClose={(r: boolean) => { setAct(null); r && reload(); }} />}</div>);
}

function Transactions() {
  const [type, setType] = useState(""); const [q, setQ] = useState(""); const { d } = useGet<any[]>(`/transactions?type=${type}&q=${encodeURIComponent(q)}`);
  return (<div className="space-y-4"><div className="flex gap-2"><Input placeholder="Search asset / ID" value={q} onChange={(e: any) => setQ(e.target.value)} />
    <Btn kind="s" onClick={() => window.open(`/api/v1/admin/transactions/export.csv?type=${type}&q=${encodeURIComponent(q)}`, "_blank")}>Export CSV</Btn>
    <select className="px-3 py-2 rounded-xl border border-line text-sm" value={type} onChange={(e) => setType(e.target.value)}>{["", "transfer", "swap_in", "swap_out", "admin_credit", "admin_debit", "issuance", "initial_grant"].map((t) => <option key={t} value={t}>{t || "All types"}</option>)}</select></div>
    <Card><Table rows={d} cols={[["ID", (r) => <span className="font-mono text-xs">{r.id.slice(0, 8)}</span>], ["Type", (r) => r.type], ["Asset", (r) => r.symbol], ["Amount", (r) => r.amount], ["From", (r) => r.from || "—"], ["To", (r) => r.to || "—"], ["Status", (r) => <Badge v={r.status} />], ["Time", (r) => r.created_at.slice(0, 16)]]} /></Card></div>);
}

function Issuance() {
  const { d, reload } = useGet<any[]>("/issuance"); const [act, setAct] = useState(false);
  return (<div className="space-y-4"><Btn onClick={() => setAct(true)}>Issue tokens</Btn>
    <Card><Table rows={d} cols={[["Asset", (r) => r.symbol], ["Amount", (r) => r.amount], ["Admin", (r) => r.admin], ["Reason", (r) => r.reason], ["Time", (r) => r.created_at.slice(0, 16)]]} /></Card>
    {act && <Action title="Issue virtual tokens" fields={[{ key: "symbol", label: "Symbol" }, { key: "wallet", label: "Wallet ID (NW-…)" }, { key: "amount", label: "Amount" }]} onSubmit={(b: any) => api("/issuance", "POST", b)} onClose={(r: boolean) => { setAct(false); r && reload(); }} />}</div>);
}

function Notifications() {
  const { d, reload } = useGet<any>("/notifications"); const [act, setAct] = useState<any>(null); const [msg, setMsg] = useState(""); const [busy, setBusy] = useState(false);
  /** Delivery runs in batches of 25 per request (serverless limit); loop until nothing is pending. */
  const flushAll = async () => { setBusy(true); let total = 0;
    try { for (let i = 0; i < 200; i++) { const r = await api("/notifications/flush", "POST"); total += r.sent; setMsg(`Delivered ${total}, pending ${r.remaining}`); if (!r.remaining || !r.sent) break; } }
    catch (e: any) { setMsg(e.message); } finally { setBusy(false); reload(); } };
  return (<div className="space-y-4"><div className="flex gap-2 flex-wrap"><Btn onClick={() => setAct("announcement")}>Send announcement</Btn><Btn kind="s" onClick={() => setAct("maintenance")}>Maintenance notice (critical)</Btn><Btn kind="s" disabled={busy} onClick={flushAll}>Deliver pending now</Btn></div>
    {msg && <div className="text-sm text-mute">{msg}</div>}
    <Card><div className="font-medium mb-2">Outbox status</div>{d && Object.entries(d.by_status).map(([k, v]: any) => <div key={k} className="flex gap-2 text-sm"><Badge v={k} />{v}</div>)}</Card>
    {act && <Action title={act === "maintenance" ? "Maintenance notice (all users)" : "Announcement (users who enabled announcements)"} fields={[{ key: "text", label: "Message" }]} onSubmit={(b: any) => api("/notifications/announce", "POST", { ...b, kind: act })} onClose={(r: boolean) => { setAct(null); if (r) flushAll(); }} />}</div>);
}

function Admins() {
  const { d, reload } = useGet<any[]>("/admins"); const [act, setAct] = useState<any>(null); const [secret, setSecret] = useState<any>(null);
  return (<div className="space-y-4"><Btn onClick={() => setAct({ t: "Create administrator", fields: [{ key: "email", label: "Email" }, { key: "password", label: "Password (min 12)" }, { key: "role", options: ["SUPER_ADMIN", "ADMIN", "MODERATOR", "SUPPORT"] }],
      f: async (b: any) => setSecret(await api("/admins", "POST", { ...b, role: b.role || "SUPER_ADMIN" })) })}>+ New admin</Btn>
    {secret && <Card><div className="font-medium">Give this TOTP secret to the new admin (shown once)</div><div className="font-mono text-sm break-all mt-1">{secret.otpauth}</div><Btn kind="s" onClick={() => setSecret(null)}>Hide</Btn></Card>}
    <Card><Table rows={d} cols={[["Email", (r) => r.email], ["Role", (r) => r.role], ["MFA", (r) => r.mfa ? "on" : "off"], ["Status", (r) => <Badge v={r.status} />], ["Last login", (r) => r.last_login?.slice(0, 16) || "—"],
      ["Actions", (r) => r.role !== "OWNER" && <div className="flex gap-1.5"><Btn kind="s" onClick={() => setAct({ t: "Change role", fields: [{ key: "role", options: ["SUPER_ADMIN", "ADMIN", "MODERATOR", "SUPPORT"] }], f: (b: any) => api(`/admins/${r.id}`, "PUT", { ...b, role: b.role || "SUPER_ADMIN" }) })}>Role</Btn>
        <Btn kind={r.status === "active" ? "d" : "p"} onClick={() => setAct({ t: "Toggle status", f: (b: any) => api(`/admins/${r.id}`, "PUT", { ...b, status: r.status === "active" ? "disabled" : "active" }) })}>{r.status === "active" ? "Disable" : "Enable"}</Btn></div>]]} /></Card>
    {act && <Action title={act.t} fields={act.fields} onSubmit={act.f} onClose={(r: boolean) => { setAct(null); r && reload(); }} />}</div>);
}

function Logs() {
  const [a, setA] = useState(""); const { d } = useGet<any[]>(`/logs?action=${a}`);
  return (<div className="space-y-4"><Input placeholder="Filter by action (e.g. wallet_credit)" value={a} onChange={(e: any) => setA(e.target.value)} />
    <Card><Table rows={d} cols={[["Time", (r) => r.at.slice(0, 19).replace("T", " ")], ["Admin", (r) => r.admin || "—"], ["Action", (r) => <b>{r.action}</b>], ["Target", (r) => <span className="font-mono text-xs">{r.target}</span>],
      ["Previous", (r) => <code className="text-xs">{r.previous ? JSON.stringify(r.previous) : "—"}</code>], ["New", (r) => <code className="text-xs">{r.new ? JSON.stringify(r.new) : "—"}</code>], ["Reason", (r) => r.reason || "—"]]} /></Card>
    <div className="text-xs text-mute">The audit log is append-only; the database rejects edits and deletes.</div></div>);
}

function Settings() {
  const { d, reload } = useGet<any>("/settings"); const [act, setAct] = useState<any>(null);
  return (<div className="space-y-4"><Card>{d && Object.entries(d).map(([k, v]: any) => <div key={k} className="flex justify-between items-center py-2 border-b border-line last:border-0"><div><div className="font-medium">{k}</div><code className="text-xs text-mute">{JSON.stringify(v)}</code></div>
    {["transfer_fee", "transfer_max_amount", "daily_limit", "swap_fee", "simulator_mode"].includes(k) && <Btn kind="s" onClick={() => setAct({ k, v })}>Edit</Btn>}</div>)}</Card>
    {act && <Action title={`Edit ${act.k}`} fields={[{ key: "json", label: "JSON value", value: JSON.stringify(act.v) }]} onSubmit={(b: any) => api("/settings", "PUT", { key: act.k, value: JSON.parse(b.json ?? JSON.stringify(act.v)), reason: b.reason, confirm: true })} onClose={(r: boolean) => { setAct(null); r && reload(); }} />}</div>);
}

const NAV: [string, string, any, string, any][] = [["Dashboard", "dashboard.view", BarChart3, "d", Dashboard], ["Users", "users.view", UsersIcon, "u", Users], ["Wallets", "wallets.view", WalletIcon, "w", Wallets],
  ["Assets", "assets.view", Coins, "a", Assets], ["Transactions", "transactions.view", ArrowLeftRight, "t", Transactions], ["Token Management", "assets.manage", Gem, "m", Assets],
  ["Issuance", "issuance.manage", Gem, "i", Issuance], ["Notifications", "notifications.send", Bell, "n", Notifications], ["Administrators", "admins.manage", Shield, "x", Admins],
  ["Audit Logs", "logs.view", FileText, "l", Logs], ["Settings", "settings.manage", Cog, "s", Settings]];

function Login({ onOk }: any) {
  const [f, setF] = useState({ email: "", password: "", totp: "" }); const [err, setErr] = useState("");
  const go = async () => { try { const r = await api("/auth/login", "POST", f); setCsrf(r.csrf); onOk(); } catch (e: any) { setErr(e.message); } };
  return (<div className="min-h-screen grid place-items-center p-4"><Card className="w-full max-w-sm space-y-3"><div className="text-xl font-semibold">CryptoNOVA <span className="text-brand">Admin</span></div>
    <Input className="w-full" placeholder="Email" onChange={(e: any) => setF({ ...f, email: e.target.value })} /><Input className="w-full" type="password" placeholder="Password" onChange={(e: any) => setF({ ...f, password: e.target.value })} />
    <Input className="w-full" placeholder="6-digit MFA code" inputMode="numeric" onChange={(e: any) => setF({ ...f, totp: e.target.value })} onKeyDown={(e: any) => e.key === "Enter" && go()} />
    {err && <div className="text-bad text-sm">{err}</div>}<Btn onClick={go}>Sign in</Btn></Card></div>);
}

/** First launch only: creates the OWNER in the browser. Proof of ownership = BOT_TOKEN; MFA is confirmed with a real code. */
function Setup({ onDone }: any) {
  const [f, setF] = useState({ bot_token: "", email: "", password: "" }); const [step, setStep] = useState(0); const [data, setData] = useState<any>(null);
  const [code, setCode] = useState(""); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const start = async () => { setErr("");
    if (!f.email.includes("@")) return setErr("Enter a valid email");
    if (f.password.length < 12) return setErr("Password must be at least 12 characters");
    setBusy(true); try { setData(await api("/setup/start", "POST", f)); setStep(1); } catch (e: any) { setErr(e.message === "wrong bot token" ? "Wrong bot token" : e.message); } finally { setBusy(false); } };
  const finish = async () => { setErr(""); setBusy(true);
    try { await api("/setup/finish", "POST", { ticket: data.ticket, code }); setStep(2); } catch (e: any) { setErr(e.message); } finally { setBusy(false); } };
  return (<div className="min-h-screen grid place-items-center p-4"><Card className="w-full max-w-md space-y-3">
    <div className="text-xl font-semibold">CryptoNOVA <span className="text-brand">Setup</span></div>
    {step === 0 && <><div className="text-sm text-mute">First launch: create the owner account. Paste the bot token from @BotFather to confirm you are the owner of this deployment.</div>
      <Input className="w-full" type="password" placeholder="Bot token (from @BotFather)" onChange={(e: any) => setF({ ...f, bot_token: e.target.value })} />
      <Input className="w-full" placeholder="Your email" onChange={(e: any) => setF({ ...f, email: e.target.value })} />
      <Input className="w-full" type="password" placeholder="Password (12+ characters)" onChange={(e: any) => setF({ ...f, password: e.target.value })} />
      {err && <div className="text-bad text-sm">{err}</div>}<Btn disabled={busy} onClick={start}>Continue</Btn></>}
    {step === 1 && <><div className="text-sm text-mute">Scan this QR code in Google Authenticator / Authy (or enter the key manually), then type the 6-digit code.</div>
      <div className="grid place-items-center bg-white rounded-xl p-3"><QRCodeSVG value={data.otpauth} size={170} /></div>
      <div className="font-mono text-xs break-all text-center">{data.secret}</div>
      <Input className="w-full" inputMode="numeric" placeholder="6-digit code" value={code} onChange={(e: any) => setCode(e.target.value)} onKeyDown={(e: any) => e.key === "Enter" && finish()} />
      {err && <div className="text-bad text-sm">{err}</div>}<Btn disabled={busy || code.length < 6} onClick={finish}>Create owner</Btn></>}
    {step === 2 && <><div className="text-center text-4xl">✓</div><div className="text-center font-medium">Owner created</div><Btn onClick={onDone}>Go to sign in</Btn></>}
  </Card></div>);
}

export default function Admin() {
  const [me, setMe] = useState<any>(null); const [loaded, setLoaded] = useState(false); const [tab, setTab] = useState("Dashboard"); const [needSetup, setNeedSetup] = useState(false);
  const load = () => api("/auth/me").then((m) => { setCsrf(m.csrf); setMe(m); })
    .catch(() => { setMe(null); return api("/setup/status").then((r) => setNeedSetup(!!r.needed)).catch(() => {}); }).finally(() => setLoaded(true));
  useEffect(() => { load(); }, []);
  if (!loaded) return null; if (!me) return needSetup ? <Setup onDone={() => setNeedSetup(false)} /> : <Login onOk={load} />;
  const can = (p: string) => me.permissions.includes(p); const items = NAV.filter(([, p]) => can(p)); const cur = items.find(([n]) => n === tab) || items[0]; const View = cur[4];
  return (<div className="min-h-screen flex"><aside className="w-60 shrink-0 bg-graphite text-white p-4 hidden md:flex flex-col"><div className="text-lg font-semibold mb-6">CryptoNOVA <span className="text-brand">Admin</span></div>
    <nav className="space-y-1 flex-1">{items.map(([n, , I]) => <button key={n} onClick={() => setTab(n)} className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm ${cur[0] === n ? "bg-brand" : "hover:bg-white/10 text-white/80"}`}><I size={17} />{n}</button>)}</nav>
    <div className="text-xs text-white/60 mb-2">{me.email}<br />{me.role}</div>
    <button onClick={async () => { await api("/auth/logout", "POST"); setMe(null); }} className="flex items-center gap-2 text-sm text-white/80"><LogOut size={16} />Sign out</button></aside>
    <main className="flex-1 p-6 max-w-[1400px]"><div className="md:hidden mb-3"><select className="w-full px-3 py-2 rounded-xl border border-line" value={cur[0]} onChange={(e) => setTab(e.target.value)}>{items.map(([n]) => <option key={n}>{n}</option>)}</select></div>
      <div className="text-2xl font-semibold mb-5">{cur[0]}</div><View key={cur[0]} can={can} /></main></div>);
}
