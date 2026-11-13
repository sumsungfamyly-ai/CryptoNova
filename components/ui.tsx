"use client";
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Area, AreaChart, ResponsiveContainer, Tooltip, YAxis } from "recharts";
import { X } from "lucide-react";

export const NovaLogo = ({ size = 28 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 32 32" aria-label="CryptoNOVA">
    <defs><linearGradient id="ng" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#8B7BFF" /><stop offset="1" stopColor="#5B47E8" /></linearGradient></defs>
    <rect width="32" height="32" rx="9" fill="url(#ng)" />
    <path d="M16 6l2.2 6.8L25 15l-6.8 2.2L16 26l-2.2-8.8L7 15l6.8-2.2z" fill="#fff" />
  </svg>
);
const HUES: Record<string, [string, string]> = { NUSD: ["#20B982", "#0E8F63"], NBTC: ["#F7A23B", "#E0771B"], NETH: ["#7C8CF8", "#4B5BD8"], NOVA: ["#8B7BFF", "#5B47E8"], NGOLD: ["#F3C94A", "#C99A12"] };
export const AssetIcon = ({ symbol, size = 40 }: { symbol: string; size?: number }) => {
  const [a, b] = HUES[symbol] || ["#9AA0B4", "#6B7185"];
  const [broken, setBroken] = useState(false);
  if (!broken && HUES[symbol]) return <img src={`/icons/${symbol.toLowerCase()}.svg`} width={size} height={size} alt={symbol} className="rounded-full shrink-0" onError={() => setBroken(true)} />;
  return (<div style={{ width: size, height: size, background: `linear-gradient(135deg,${a},${b})`, fontSize: size * 0.34 }}
    className="rounded-full grid place-items-center text-white font-semibold shrink-0">{symbol.replace(/^N/, "").slice(0, 3)}</div>);
};
export const Card = ({ children, className = "", onClick }: any) => (
  <motion.div whileTap={onClick ? { scale: 0.98 } : undefined} onClick={onClick}
    className={`bg-card rounded-card border border-line p-4 ${className}`}>{children}</motion.div>);
export const Skeleton = ({ className = "" }) => <div className={`animate-pulse rounded-xl bg-line ${className}`} />;
export const Empty = ({ title, hint }: { title: string; hint?: string }) => (
  <div className="text-center py-10"><div className="text-3xl mb-2">✦</div><div className="font-medium">{title}</div>{hint && <div className="text-mute text-sm mt-1">{hint}</div>}</div>);
export const ErrorBox = ({ msg, retry }: { msg: string; retry?: () => void }) => (
  <Card className="text-center"><div className="text-bad font-medium">{msg}</div>{retry && <button onClick={retry} className="mt-3 text-brand font-medium">Try again</button>}</Card>);
export const Change = ({ v }: { v?: string | null }) => v == null ? <span className="text-mute text-sm">—</span> :
  <span className={`text-sm font-medium ${Number(v) >= 0 ? "text-ok" : "text-bad"}`}>{Number(v) >= 0 ? "+" : ""}{v}%</span>;
export const DemoTag = () => <span className="text-[10px] font-semibold tracking-wide px-1.5 py-0.5 rounded-md bg-brand/10 text-brand">DEMO</span>;

export function Chart({ data, h = 160 }: { data: { t: string; v: number }[]; h?: number }) {
  if (data.length < 2) return <Empty title="Not enough data yet" hint="The chart fills in as prices are recorded." />;
  const up = data[data.length - 1].v >= data[0].v, c = up ? "#20B982" : "#E65A65";
  return (<div style={{ height: h }}><ResponsiveContainer><AreaChart data={data}>
    <defs><linearGradient id="cg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={c} stopOpacity={0.25} /><stop offset="1" stopColor={c} stopOpacity={0} /></linearGradient></defs>
    <YAxis hide domain={["auto", "auto"]} />
    <Tooltip contentStyle={{ borderRadius: 12, border: "none", fontSize: 12 }} formatter={(v: any) => Number(v).toLocaleString()} labelFormatter={(l) => new Date(l).toLocaleString()} />
    <Area type="monotone" dataKey="v" stroke={c} strokeWidth={2} fill="url(#cg)" dot={false} />
  </AreaChart></ResponsiveContainer></div>);
}
export function Sheet({ open, onClose, title, children }: any) {
  return (<AnimatePresence>{open && (<>
    <motion.div className="fixed inset-0 bg-black/40 z-40" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
    <motion.div className="fixed inset-x-0 bottom-0 z-50 bg-bg rounded-t-[28px] max-h-[92vh] overflow-y-auto p-5 pb-10 max-w-xl mx-auto"
      initial={{ y: "100%" }} animate={{ y: 0 }} exit={{ y: "100%" }} transition={{ type: "spring", damping: 30, stiffness: 320 }}>
      <div className="flex items-center justify-between mb-4"><div className="text-lg font-semibold">{title}</div>
        <button onClick={onClose} className="p-2 rounded-full bg-card border border-line"><X size={16} /></button></div>
      {children}
    </motion.div></>)}</AnimatePresence>);
}
export const RANGES = ["1H", "24H", "7D", "30D", "90D", "ALL"];
export const RangeTabs = ({ v, on }: { v: string; on: (r: string) => void }) => (
  <div className="flex gap-1 bg-line/60 rounded-xl p-1 mt-3">{RANGES.map((r) => (
    <button key={r} onClick={() => on(r)} className={`flex-1 text-xs py-1.5 rounded-lg font-medium ${v === r ? "bg-card shadow-sm" : "text-mute"}`}>{r}</button>))}</div>);
