"use client";
import { useEffect } from "react";
import { initLang } from "../lib/i18n";

/** Applies the saved (or browser) language once the page is hydrated. */
export default function I18nBoot() {
  useEffect(() => { initLang(); }, []);
  return null;
}
