"use client";
import { useEffect, useMemo, useState } from "react";
import { ArrowDownLeft, ArrowUpRight, Activity as Act, Copy, Layers, Repeat, Search, Share2, Star } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { api, fmt, tg, usd } from "../lib/api";
import { AssetIcon, Card, Change, Chart, DemoTag, Empty, ErrorBox, NovaLogo, RangeTabs, Sheet, Skeleton } from "./ui";

export function useLoad<T>(path: string, deps: any[] = []) {
  const [d, setD] = useState<T | null>(null); const [err, setErr] = useState(""); const [n, setN] = useState(0);
  useEffect(() => { setErr(""); api<T>(path).then(setD).catch((e) => setErr(e.message)); }, [path, n, ...deps]);
  return { d, err, reload: () => setN((x) => x + 1) };
}
const TX_LABEL: Record<string, string> = { swap_in: "Swap (received)", swap_out: "Swap (paid)", sent: "Sent", received: "Received", admin_credit: "Admin credit", admin_debit: "Admin debit", issuance: "Token issuance", initial_grant: "Starting balance" };

export function TxRow({ t }: any) {
  const plus = t.direction === "received" || t.type === "initial_grant";
  return (<div className="flex items-center gap-3 py-3 border-b border-line last:border-0">
    <div className={`w-10 h-10 rounded-full grid place-items-center ${plus ? "bg-ok/10 text-ok" : "bg-bad/10 text-bad"}`}>{plus ? <ArrowDownLeft size={18} /> : <ArrowUpRight size={18} />}</div>
    <div className="flex-1 min-w-0"><div className="font-medium">{TX_LABEL[t.type] || t.type}</div>
      <div className="text-xs text-mute truncate">{t.from ? `@${t.from}` : "System"} → {t.to ? `@${t.to}` : "System"} · {new Date(t.created_at).toLocaleString()}</div>
      <div className="text-[10px] text-mute font-mono">{t.id.slice(0, 8)} · {t.status}</div></div>
    <div className={`font-semibold ${plus ? "text-ok" : ""}`}>{plus ? "+" : "−"}{fmt(t.amount, 6)} {t.symbol}</div></div>);
}

export function Home({ me, pf, assets, txs, go, open, reload }: any) {
  const [range, setRange] = useState("24H");
  const hist = useLoad<any[]>(`/portfolio/history?range=${range}`, [pf?.total_value]);
  const chg = useMemo(() => { if (!pf || !assets) return null; let now = 0, prev = 0;
    pf.assets.forEach((a: any) => { const m = assets.find((x: any) => x.symbol === a.symbol); const v = Number(a.value); now += v; prev += m?.change_24h == null ? v : v / (1 + Number(m.change_24h) / 100); });
    return prev ? (((now - prev) / prev) * 100).toFixed(2) : "0.00"; }, [pf, assets]);
  return (<div className="space-y-4">
    <div className="flex items-center justify-between"><div className="flex items-center gap-2"><NovaLogo /><span className="font-semibold">CryptoNOVA</span><DemoTag /></div>
      {me?.photo_url ? <img src={me.photo_url} className="w-9 h-9 rounded-full" alt="" /> : <div className="w-9 h-9 rounded-full bg-brand text-white grid place-items-center font-semibold">{(me?.first_name || "?")[0]}</div>}</div>
    <div><div className="text-mute text-sm">Hello, {me?.first_name || "there"} 👋</div></div>
    <Card className="!p-5">
      <div className="text-mute text-sm">Total virtual balance</div>
      {pf ? <div className="text-4xl font-semibold tracking-tight mt-1">{usd(pf.total_value)}</div> : <Skeleton className="h-10 w-48 mt-2" />}
      <div className="mt-1 flex items-center gap-2"><Change v={chg} /><span className="text-xs text-mute">24h · current holdings</span></div>
      <Chart data={(hist.d || []).map((p) => ({ t: p.t, v: Number(p.v) }))} />
      <RangeTabs v={range} on={setRange} />
    </Card>
    <div className="grid grid-cols-5 gap-2">{[["Send", ArrowUpRight, () => open("send")], ["Receive", ArrowDownLeft, () => open("receive")], ["Swap", Repeat, () => open("swap")], ["Assets", Layers, () => go("markets")], ["Activity", Act, () => go("activity")]].map(([l, I, f]: any) => (
      <button key={l} onClick={f} className="flex flex-col items-center gap-2"><div className="w-12 h-12 rounded-2xl bg-card border border-line grid place-items-center text-brand"><I size={22} /></div><span className="text-xs font-medium">{l}</span></button>))}</div>
    <div className="font-semibold pt-2">Your assets</div>
    <Card className="!py-1">{!pf ? <Skeleton className="h-32 my-3" /> : pf.assets.map((a: any) => (
      <div key={a.symbol} onClick={() => open({ asset: a.symbol })} className="flex items-center gap-3 py-3 border-b border-line last:border-0">
        <AssetIcon symbol={a.symbol} /><div className="flex-1"><div className="font-medium">{a.name}</div><div className="text-xs text-mute">{fmt(a.amount, 6)} {a.symbol}</div></div>
        <div className="text-right font-medium">{usd(a.value)}</div></div>))}</Card>
    <div className="font-semibold pt-2">Recent activity</div>
    <Card className="!py-1">{!txs ? <Skeleton className="h-24 my-3" /> : txs.length ? txs.slice(0, 4).map((t: any) => <TxRow key={t.id} t={t} />) : <Empty title="No activity yet" hint="Send or receive tokens to see it here." />}</Card></div>);
}

const CATS = [["all", "All Assets"], ["watchlist", "★ Watchlist"], ["popular", "Popular"], ["stable", "Stable Assets"], ["nova", "Nova Ecosystem"]];
export function Markets({ open }: any) {
  const [cat, setCat] = useState("all"); const [q, setQ] = useState("");
  const { d, err, reload } = useLoad<any[]>(`/assets?category=${cat}&q=${encodeURIComponent(q)}`);
  const toggle = async (e: any, a: any) => { e.stopPropagation(); await api(`/watchlist/${a.symbol}`, { method: "PUT", body: JSON.stringify({ watched: !a.watched }) }); reload(); };
  return (<div className="space-y-4"><div className="text-2xl font-semibold">Markets <DemoTag /></div>
    <div className="text-xs text-mute -mt-2">Demonstration prices of virtual assets — not real quotes.</div>
    <div className="relative"><Search size={16} className="absolute left-3 top-3.5 text-mute" /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search assets" className="w-full pl-9 pr-3 py-3 rounded-2xl bg-card border border-line outline-none focus:border-brand" /></div>
    <div className="flex gap-2 overflow-x-auto no-scrollbar">{CATS.map(([k, l]) => <button key={k} onClick={() => setCat(k)} className={`px-3 py-1.5 rounded-full text-sm whitespace-nowrap border ${cat === k ? "bg-brand text-white border-brand" : "bg-card border-line"}`}>{l}</button>)}</div>
    {err ? <ErrorBox msg={err} retry={reload} /> : !d ? <Skeleton className="h-48" /> : d.length === 0 ? <Empty title={cat === "watchlist" ? "Your watchlist is empty" : "No assets found"} hint={cat === "watchlist" ? "Tap the star on an asset to follow it." : undefined} /> :
      <Card className="!py-1">{d.map((a) => (<div key={a.symbol} onClick={() => open({ asset: a.symbol })} className="flex items-center gap-3 py-3 border-b border-line last:border-0">
        <AssetIcon symbol={a.symbol} /><div className="flex-1"><div className="font-medium">{a.name}</div><div className="text-xs text-mute">{a.symbol} · cap {usd(a.market_cap)}</div></div>
        <div className="text-right"><div className="font-medium">{usd(a.price)}</div><Change v={a.change_24h} /></div>
        <button onClick={(e) => toggle(e, a)} aria-label="watchlist" className="p-1"><Star size={18} className={a.watched ? "text-[#F7A23B]" : "text-mute"} fill={a.watched ? "#F7A23B" : "none"} /></button></div>))}</Card>}</div>);
}

export function WalletScreen({ pf, txs }: any) {
  return (<div className="space-y-4"><div className="text-2xl font-semibold">Wallet</div>
    <Card className="!p-5"><div className="text-mute text-sm">Total virtual value</div>
      <div className="text-3xl font-semibold mt-1">{pf ? usd(pf.total_value) : "…"}</div>
      <div className="text-xs text-mute mt-1 font-mono">ID {pf?.wallet_id} · {pf?.wallet_status}</div></Card>
    {pf?.wallet_status === "frozen" && <ErrorBox msg="This wallet is frozen. Transfers are unavailable." />}
    <Card className="!py-1">{pf?.assets.map((a: any) => (<div key={a.symbol} className="flex items-center gap-3 py-3 border-b border-line last:border-0">
      <AssetIcon symbol={a.symbol} /><div className="flex-1"><div className="font-medium">{a.symbol}</div><div className="text-xs text-mute">Available {fmt(a.amount, 8)}</div></div><div className="font-medium">{usd(a.value)}</div></div>))}</Card>
    <div className="font-semibold">History</div><Card className="!py-1">{txs?.length ? txs.map((t: any) => <TxRow key={t.id} t={t} />) : <Empty title="No operations yet" />}</Card></div>);
}

const FILTERS = [["", "All"], ["received", "Received"], ["sent", "Sent"], ["swap", "Swaps"], ["admin_credit", "Admin Adjustment"], ["issuance", "Token Issuance"]];
export function Activity() {
  const [f, setF] = useState(""); const [q, setQ] = useState(""); const [order, setOrder] = useState("desc");
  const { d, err, reload } = useLoad<any[]>(`/transactions?type=${f}&q=${encodeURIComponent(q)}&order=${order}`);
  return (<div className="space-y-4"><div className="text-2xl font-semibold">Activity</div>
    <div className="flex gap-2"><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by asset or ID" className="flex-1 px-3 py-3 rounded-2xl bg-card border border-line outline-none focus:border-brand" />
      <button onClick={() => setOrder(order === "desc" ? "asc" : "desc")} className="px-3 rounded-2xl bg-card border border-line text-sm">{order === "desc" ? "Newest" : "Oldest"}</button></div>
    <div className="flex gap-2 overflow-x-auto">{FILTERS.map(([k, l]) => <button key={k} onClick={() => setF(k)} className={`px-3 py-1.5 rounded-full text-sm whitespace-nowrap border ${f === k ? "bg-brand text-white border-brand" : "bg-card border-line"}`}>{l}</button>)}</div>
    {err ? <ErrorBox msg={err} retry={reload} /> : !d ? <Skeleton className="h-48" /> : <Card className="!py-1">{d.length ? d.map((t) => <TxRow key={t.id} t={t} />) : <Empty title="Nothing here" hint="Try another filter." />}</Card>}</div>);
}

export function Profile({ me, theme, setTheme, reload }: any) {
  const [prefs, setPrefs] = useState({ transfers: true, announcements: true }); const [msg, setMsg] = useState(""); const [sent, setSent] = useState(false);
  const save = (p: any) => { setPrefs(p); api("/notifications/preferences", { method: "PUT", body: JSON.stringify(p) }).catch(() => {}); };
  const Row = ({ l, v }: any) => <div className="flex justify-between py-2.5 border-b border-line last:border-0 text-sm"><span className="text-mute">{l}</span><span className="font-medium text-right break-all ml-4">{v}</span></div>;
  const Tog = ({ on, f }: any) => <button onClick={f} className={`w-11 h-6 rounded-full p-0.5 transition ${on ? "bg-brand" : "bg-line"}`}><div className={`w-5 h-5 rounded-full bg-white transition ${on ? "translate-x-5" : ""}`} /></button>;
  return (<div className="space-y-4"><div className="text-2xl font-semibold">Profile</div>
    <Card><Row l="Username" v={me?.username ? "@" + me.username : "—"} /><Row l="Telegram ID" v={me?.telegram_id} /><Row l="Internal ID" v={me?.id} />
      <Row l="Registered" v={me && new Date(me.registered_at).toLocaleDateString()} /><Row l="Operations" v={me?.transactions} /></Card>
    <Card><div className="font-medium mb-2">Settings</div>
      <div className="flex justify-between items-center py-2"><span>Dark theme</span><Tog on={theme === "dark"} f={() => setTheme(theme === "dark" ? "light" : "dark")} /></div>
      <div className="flex justify-between items-center py-2"><span>Transfer notifications</span><Tog on={prefs.transfers} f={() => save({ ...prefs, transfers: !prefs.transfers })} /></div>
      <div className="flex justify-between items-center py-2"><span>Announcements</span><Tog on={prefs.announcements} f={() => save({ ...prefs, announcements: !prefs.announcements })} /></div>
      <div className="text-xs text-mute mt-1">Critical system notices are always delivered.</div></Card>
    <Card><div className="font-medium mb-2">Support</div>
      <textarea value={msg} onChange={(e) => setMsg(e.target.value)} placeholder="Describe your issue" className="w-full p-3 rounded-xl bg-bg border border-line outline-none" rows={3} />
      <button disabled={!msg.trim() || sent} onClick={() => api("/support", { method: "POST", body: JSON.stringify({ subject: "Mini App ticket", message: msg }) }).then(() => { setSent(true); setMsg(""); })}
        className="mt-2 w-full py-3 rounded-2xl bg-brand text-white font-medium disabled:opacity-50">{sent ? "Sent ✓" : "Send to support"}</button></Card>
    <div className="text-center text-xs text-mute">CryptoNOVA is an educational simulator. All assets are virtual.</div></div>);
}

export function AssetSheet({ symbol, pf, onClose, open }: any) {
  const [range, setRange] = useState("24H");
  const a = useLoad<any>(symbol ? `/assets/${symbol}` : "/config"); const h = useLoad<any[]>(symbol ? `/assets/${symbol}/history?range=${range}` : "/config");
  const txs = useLoad<any[]>(symbol ? `/transactions?q=${symbol}` : "/config");
  const bal = pf?.assets.find((x: any) => x.symbol === symbol);
  return (<Sheet open={!!symbol} onClose={onClose} title={symbol ? `${symbol}` : ""}>
    {a.d && symbol && (<div className="space-y-4"><div className="flex items-center gap-3"><AssetIcon symbol={symbol} size={52} /><div className="flex-1"><div className="text-lg font-semibold">{a.d.name}</div><DemoTag /></div>
      <div className="text-right"><div className="text-xl font-semibold">{usd(a.d.price)}</div><Change v={a.d.change_24h} /></div></div>
      <Card><Chart data={Array.isArray(h.d) ? h.d.map((p: any) => ({ t: p.t, v: Number(p.p) })) : []} /><RangeTabs v={range} on={setRange} /></Card>
      <Card><div className="text-sm text-mute">Your balance</div><div className="text-xl font-semibold">{fmt(bal?.amount || 0, 8)} {symbol}</div><div className="text-sm text-mute mt-3">{a.d.description}</div></Card>
      <Card className="!py-1">{Array.isArray(txs.d) && txs.d.length ? txs.d.map((t: any) => <TxRow key={t.id} t={t} />) : <Empty title={`No ${symbol} operations`} />}</Card>
      <div className="grid grid-cols-2 gap-3"><button onClick={() => { onClose(); open("send"); }} className="py-3.5 rounded-2xl bg-brand text-white font-medium">Send {symbol}</button>
        <button onClick={() => { onClose(); open({ swap: symbol }); }} className="py-3.5 rounded-2xl bg-card border border-line font-medium">Swap</button></div></div>)}
  </Sheet>);
}

export function ReceiveSheet({ show, onClose, me, pf }: any) {
  const bot = process.env.NEXT_PUBLIC_BOT_LINK; const link = bot ? `${bot}?startapp=${pf?.wallet_id}` : `cryptonova:${pf?.wallet_id}`;
  const copy = (v: string) => { navigator.clipboard?.writeText(v); tg()?.HapticFeedback?.notificationOccurred("success"); };
  const share = () => tg()?.openTelegramLink ? tg().openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent("Send me virtual tokens on CryptoNOVA")}`) : navigator.share?.({ url: link });
  const Row = ({ l, v }: any) => <div className="flex justify-between items-center py-2 text-sm"><span className="text-mute">{l}</span><button onClick={() => copy(v)} className="font-mono flex items-center gap-1">{v}<Copy size={12} /></button></div>;
  return (<Sheet open={show} onClose={onClose} title="Receive"><div className="space-y-4">
    <Card className="grid place-items-center !py-6"><div className="bg-white p-3 rounded-2xl"><QRCodeSVG value={link} size={176} fgColor="#17181C" /></div><div className="text-xs text-mute mt-3">Internal CryptoNOVA link — not a blockchain address</div></Card>
    <Card className="!py-2"><Row l="Username" v={me?.username ? "@" + me.username : "—"} /><Row l="User ID" v={me?.id} /><Row l="Wallet ID" v={pf?.wallet_id} /></Card>
    <div className="grid grid-cols-2 gap-3"><button onClick={() => copy(pf?.wallet_id)} className="py-3 rounded-2xl bg-card border border-line font-medium">Copy ID</button>
      <button onClick={share} className="py-3 rounded-2xl bg-brand text-white font-medium flex items-center justify-center gap-2"><Share2 size={16} />Share</button></div></div></Sheet>);
}

export function SendSheet({ show, onClose, pf, onDone }: any) {
  const [to, setTo] = useState(""); const [rec, setRec] = useState<any>(null); const [sym, setSym] = useState("NUSD"); const [amt, setAmt] = useState("");
  const [step, setStep] = useState(0); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false); const [key, setKey] = useState("");
  const cfg = useLoad<any>(show ? "/config" : "/portfolio"); const recents = useLoad<any[]>(show ? "/transactions/recipients" : "/config"); const bal = Number(pf?.assets.find((a: any) => a.symbol === sym)?.amount || 0);
  useEffect(() => { if (show) { setStep(0); setTo(""); setRec(null); setAmt(""); setErr(""); setKey(crypto.randomUUID()); } }, [show]);
  const fee = cfg.d?.fee_enabled ? (Number(amt || 0) * Number(cfg.d.fee_percent)) / 100 : 0;
  const next = async () => { setErr(""); setBusy(true);
    try { if (step === 0) { setRec(await api(`/users/lookup?q=${encodeURIComponent(to)}`)); setStep(1); }
      else if (step === 1) { if (!(Number(amt) > 0)) throw new Error("Enter an amount"); if (Number(amt) + fee > bal) throw new Error("Insufficient balance"); setStep(2); }
      else { await api("/transfers", { method: "POST", body: JSON.stringify({ recipient: rec.id, symbol: sym, amount: amt, idempotency_key: key }) }); tg()?.HapticFeedback?.notificationOccurred("success"); setStep(3); onDone(); } }
    catch (e: any) { setErr(e.message === "recipient not found" ? "Recipient not found" : e.message); } finally { setBusy(false); } };
  return (<Sheet open={show} onClose={onClose} title="Send"><div className="space-y-4">
    {step === 0 && <><input autoFocus value={to} onChange={(e) => setTo(e.target.value)} placeholder="@username or internal ID" className="w-full p-4 rounded-2xl bg-card border border-line outline-none focus:border-brand" />
      {Array.isArray(recents.d) && recents.d.length > 0 && <div><div className="text-xs text-mute mb-2">Recent</div><div className="flex gap-2 flex-wrap">{recents.d.map((r: any) => <button key={r.username} onClick={() => setTo("@" + r.username)} className="px-3 py-1.5 rounded-full bg-card border border-line text-sm">@{r.username}</button>)}</div></div>}</>}
    {step === 1 && <><Card className="flex items-center gap-3"><div className="w-10 h-10 rounded-full bg-brand text-white grid place-items-center">{(rec.username || "?")[0]}</div><div>@{rec.username || rec.id.slice(0, 8)}</div></Card>
      <div className="flex gap-2 overflow-x-auto">{pf?.assets.map((a: any) => <button key={a.symbol} onClick={() => setSym(a.symbol)} className={`px-3 py-2 rounded-2xl border flex items-center gap-2 ${sym === a.symbol ? "border-brand bg-brand/10" : "bg-card border-line"}`}><AssetIcon symbol={a.symbol} size={22} />{a.symbol}</button>)}</div>
      <input inputMode="decimal" value={amt} onChange={(e) => setAmt(e.target.value.replace(",", "."))} placeholder="0.00" className="w-full text-3xl font-semibold p-4 rounded-2xl bg-card border border-line outline-none focus:border-brand" />
      <div className="flex justify-between text-sm text-mute"><span>Available {fmt(bal, 8)} {sym}</span><button className="text-brand" onClick={() => setAmt(String(bal))}>Max</button></div></>}
    {step === 2 && <Card><div className="text-sm text-mute">You send</div><div className="text-3xl font-semibold">{amt} {sym}</div>
      <div className="mt-3 space-y-1 text-sm"><div className="flex justify-between"><span className="text-mute">To</span><span>@{rec.username || rec.id.slice(0, 8)}</span></div>
        <div className="flex justify-between"><span className="text-mute">Fee</span><span>{fee ? `${fee} ${sym}` : "None"}</span></div>
        <div className="flex justify-between"><span className="text-mute">Total</span><span className="font-medium">{Number(amt) + fee} {sym}</span></div></div>
      <div className="text-xs text-mute mt-3">Virtual transfer inside CryptoNOVA (DEMO). No real assets move.</div></Card>}
    {step === 3 && <div className="text-center py-8"><div className="text-5xl mb-3">✓</div><div className="text-xl font-semibold">Sent</div><div className="text-mute text-sm mt-1">{amt} {sym} → @{rec.username}</div></div>}
    {err && <div className="text-bad text-sm text-center">{err}</div>}
    <button disabled={busy || (step === 0 && !to.trim())} onClick={step === 3 ? onClose : next} className="w-full py-3.5 rounded-2xl bg-brand text-white font-medium disabled:opacity-50">{busy ? "…" : ["Continue", "Review", "Confirm transfer", "Done"][step]}</button></div></Sheet>);
}

export function SwapSheet({ show, onClose, pf, assets, preset, onDone }: any) {
  const [from, setFrom] = useState("NUSD"); const [to, setTo] = useState("NBTC"); const [amt, setAmt] = useState(""); const [quote, setQuote] = useState<any>(null);
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false); const [done, setDone] = useState<any>(null); const [key, setKey] = useState("");
  const syms: string[] = (assets || []).map((a: any) => a.symbol);
  const bal = Number(pf?.assets.find((a: any) => a.symbol === from)?.amount || 0);
  useEffect(() => { if (show) { setAmt(""); setQuote(null); setErr(""); setDone(null); setKey(crypto.randomUUID());
    if (preset) { setFrom(preset); setTo(preset === "NUSD" ? "NBTC" : "NUSD"); } } }, [show, preset]);
  useEffect(() => { setQuote(null); setErr("");
    if (!show || !(Number(amt) > 0) || from === to) return;
    const t = setTimeout(() => api(`/swap/quote?from_symbol=${from}&to_symbol=${to}&amount=${amt}`).then(setQuote).catch((e) => setErr(e.message)), 300);
    return () => clearTimeout(t); }, [amt, from, to, show]);
  const flip = () => { setFrom(to); setTo(from); };
  const confirm = async () => { setBusy(true); setErr("");
    try { const minRecv = (Number(quote.amount_out) * 0.99).toFixed(8);   // 1% slippage tolerance
      setDone(await api("/swap", { method: "POST", body: JSON.stringify({ from_symbol: from, to_symbol: to, amount: amt, min_receive: minRecv, idempotency_key: key }) }));
      tg()?.HapticFeedback?.notificationOccurred("success"); onDone(); }
    catch (e: any) { setErr(e.message); if (e.code === "price_changed") setQuote(null); } finally { setBusy(false); } };
  const Sel = ({ v, on }: any) => <select value={v} onChange={(e) => on(e.target.value)} className="bg-bg border border-line rounded-xl px-3 py-2 font-medium">{syms.map((s) => <option key={s}>{s}</option>)}</select>;
  return (<Sheet open={show} onClose={onClose} title="Swap"><div className="space-y-4">
    {done ? <div className="text-center py-8"><div className="text-5xl mb-3">✓</div><div className="text-xl font-semibold">Swapped</div>
        <div className="text-mute text-sm mt-1">{done.amount_in} {from} → {done.amount_out} {to}</div></div> : <>
      <Card className="space-y-3"><div className="flex items-center justify-between"><span className="text-sm text-mute">You pay</span><Sel v={from} on={setFrom} /></div>
        <input inputMode="decimal" value={amt} onChange={(e) => setAmt(e.target.value.replace(",", "."))} placeholder="0.00" className="w-full text-3xl font-semibold bg-transparent outline-none" />
        <div className="flex justify-between text-sm text-mute"><span>Available {fmt(bal, 8)} {from}</span><button className="text-brand" onClick={() => setAmt(String(bal))}>Max</button></div></Card>
      <div className="grid place-items-center -my-2"><button onClick={flip} className="w-10 h-10 rounded-full bg-card border border-line grid place-items-center text-brand"><Repeat size={18} /></button></div>
      <Card className="space-y-2"><div className="flex items-center justify-between"><span className="text-sm text-mute">You receive (estimate)</span><Sel v={to} on={setTo} /></div>
        <div className="text-3xl font-semibold">{quote ? fmt(quote.amount_out, 8) : "—"}</div>
        {quote && <div className="text-xs text-mute">1 {from} ≈ {fmt(quote.rate, 8)} {to} · fee {quote.fee_percent}% ({fmt(quote.fee, 8)} {to}) · DEMO prices</div>}</Card>
      {err && <div className="text-bad text-sm text-center">{err}</div>}
      <button disabled={busy || !quote || Number(amt) > bal} onClick={confirm} className="w-full py-3.5 rounded-2xl bg-brand text-white font-medium disabled:opacity-50">{Number(amt) > bal ? "Insufficient balance" : busy ? "…" : "Confirm swap"}</button>
      <div className="text-xs text-mute text-center">Virtual exchange at demo prices. Min. received is protected (1% tolerance).</div></>}
    {done && <button onClick={onClose} className="w-full py-3.5 rounded-2xl bg-brand text-white font-medium">Done</button>}</div></Sheet>);
}
