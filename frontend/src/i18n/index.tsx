// i18n: a tiny `t()` over per-feature dictionaries. Phase 0 owns this file.
// Each workstream owns one dictionary file (advisor.ts, quote.ts, kyc.ts, track.ts, backoffice.ts) and prefixes its
// keys with its feature name, e.g. "quote.title". Missing Hindi falls back to English, then to the key itself.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { Language, LocalText } from "../api/types";
import common from "./common";
import advisor from "./advisor";
import quote from "./quote";
import kyc from "./kyc";
import track from "./track";
import backoffice from "./backoffice";

export type Dict = Record<string, string>;
export interface FeatureDict { en: Dict; hi: Dict }

const dictionaries: FeatureDict[] = [common, advisor, quote, kyc, track, backoffice];
const merged: Record<Language, Dict> = {
  en: Object.assign({}, ...dictionaries.map((d) => d.en)),
  hi: Object.assign({}, ...dictionaries.map((d) => d.hi)),
};

const STORAGE_KEY = "udyam.lang";

function initialLang(): Language {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "en" || saved === "hi") return saved;
  } catch { /* storage blocked: use default */ }
  return navigator.language?.toLowerCase().startsWith("hi") ? "hi" : "en";
}

interface LangCtx { lang: Language; setLang: (l: Language) => void }
const LangContext = createContext<LangCtx>({ lang: "en", setLang: () => {} });

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Language>(initialLang);
  const setLang = useCallback((l: Language) => {
    setLangState(l);
    try { localStorage.setItem(STORAGE_KEY, l); } catch { /* ignore */ }
  }, []);
  useEffect(() => { document.documentElement.lang = lang; }, [lang]);
  const value = useMemo(() => ({ lang, setLang }), [lang, setLang]);
  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

export function useLang(): LangCtx {
  return useContext(LangContext);
}

/** t("quote.total", { amount: "₹5,392" }) replaces {amount} placeholders. */
export function translate(lang: Language, key: string, vars?: Record<string, string | number>): string {
  let s = merged[lang][key] ?? merged.en[key] ?? key;
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, String(v));
  return s;
}

export function useT() {
  const { lang } = useLang();
  const t = useCallback((key: string, vars?: Record<string, string | number>) => translate(lang, key, vars), [lang]);
  /** Pick the current language from a server LocalText. */
  const lt = useCallback((text: LocalText | null | undefined) => (text ? (lang === "hi" ? text.hi || text.en : text.en) : ""), [lang]);
  return { t, lt, lang };
}
