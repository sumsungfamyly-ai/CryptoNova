"use client";
import { useCallback, useEffect, useState } from "react";
import { Home as HomeIcon, LineChart, User as UserIcon, Wallet as WalletIcon, Activity as ActIcon } from "lucide-react";
import { api, login, tg } from "../lib/api";
import { Activity, AssetSheet, Home, Markets, Profile, ReceiveSheet, SendSheet, SwapSheet, WalletScreen, useLoad } from "./screens";
import { ErrorBox, NovaLogo, Skeleton } from "./ui";

const TABS: [string, string, any][] = [["home", "Home", HomeIcon], ["markets", "Markets", LineChart], ["wallet", "Wallet", WalletIcon], ["activity", "Activity", ActIcon], ["profile", "Profile", UserIcon]];

export default function App() {
  const [ready, setReady] = useState(false); const [fatal, setFatal] = useState(""); const [tab, setTab] = useState("home");
  const [sheet, setSheet] = useState<any>(null); const [theme, setTheme] = useState<"light" | "dark">("light"); const [me, setMe] = useState<any>(null);
  const [pf, setPf] = useState<any>(null); const [txs, setTxs] = useState<any[] | null>(null); const [assets, setAssets] = useState<any[] | null>(null);
  useEffect(() => { document.documentElement.dataset.theme = theme; tg()?.setHeaderColor?.(theme === "dark" ? "#111318" : "#F7F8FA"); }, [theme]);
  const reload = useCallback(async () => {
    const [p, t, a, m] = await Promise.all([api("/portfolio"), api("/transactions?limit=20"), api("/assets"), api("/users/me")]);
    setPf(p); setTxs(t); setAssets(a); setMe(m); }, []);
  useEffect(() => { (async () => {
    try { tg()?.ready(); tg()?.expand(); setTheme(tg()?.colorScheme === "dark" ? "dark" : "light"); await login(); await reload(); setReady(true); }
    catch (e: any) { setFatal(e.message === "not_in_telegram" ? "Please open CryptoNOVA from Telegram." : "Could not sign in. Please reopen the app."); } })(); }, [reload]);

  if (fatal) return <div className="min-h-screen grid place-items-center p-6"><div className="text-center"><NovaLogo size={56} /><div className="mt-4"><ErrorBox msg={fatal} /></div></div></div>;
  if (!ready) return <div className="p-5 space-y-4"><Skeleton className="h-10 w-40" /><Skeleton className="h-56" /><Skeleton className="h-40" /></div>;
  const open = (s: any) => setSheet(s);
  return (<div className="max-w-xl mx-auto px-4 pt-4 safe-b">
    {tab === "home" && <Home me={me} pf={pf} assets={assets} txs={txs} go={setTab} open={open} reload={reload} />}
    {tab === "markets" && <Markets open={open} />}
    {tab === "wallet" && <WalletScreen pf={pf} txs={txs} />}
    {tab === "activity" && <Activity />}
    {tab === "profile" && <Profile me={me} theme={theme} setTheme={setTheme} reload={reload} />}
    <nav className="fixed bottom-0 inset-x-0 bg-card/90 backdrop-blur border-t border-line" style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}>
      <div className="max-w-xl mx-auto grid grid-cols-5">{TABS.map(([k, l, I]) => (
        <button key={k} onClick={() => setTab(k)} className={`py-2.5 flex flex-col items-center gap-0.5 text-[11px] ${tab === k ? "text-brand" : "text-mute"}`}><I size={21} />{l}</button>))}</div></nav>
    <SendSheet show={sheet === "send"} onClose={() => setSheet(null)} pf={pf} onDone={reload} />
    <SwapSheet show={sheet === "swap" || !!sheet?.swap} preset={sheet?.swap} onClose={() => setSheet(null)} pf={pf} assets={assets} onDone={reload} />
    <ReceiveSheet show={sheet === "receive"} onClose={() => setSheet(null)} me={me} pf={pf} />
    <AssetSheet symbol={sheet?.asset} pf={pf} onClose={() => setSheet(null)} open={open} />
  </div>);
}
