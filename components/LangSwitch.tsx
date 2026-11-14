"use client";
import { useEffect, useState } from "react";
import { getLang, setLang, subscribe, type Lang } from "../lib/i18n";

export default function LangSwitch({ onChange, className = "" }: { onChange?: (l: Lang) => void; className?: string }) {
  const [l, setL] = useState<Lang>("en");
  useEffect(() => { setL(getLang()); return subscribe(setL); }, []);
  const pick = (x: Lang) => { setLang(x); if (onChange) onChange(x); };
  return (
    <div className={`inline-flex rounded-xl border border-line bg-card p-0.5 text-xs font-medium ${className}`}>
      {(["ru", "en"] as Lang[]).map((x) => (
        <button key={x} onClick={() => pick(x)} className={`px-2.5 py-1 rounded-lg ${l === x ? "bg-brand text-white" : "text-mute"}`}>{x.toUpperCase()}</button>
      ))}
    </div>
  );
}
