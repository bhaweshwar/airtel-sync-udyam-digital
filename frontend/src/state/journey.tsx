// The owner's journey across screens: advisor session -> profile -> quote -> order + PIN. Phase 0 owns this file.
// Persisted to sessionStorage so a refresh doesn't lose progress (and nothing outlives the browser tab).
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import type { BusinessProfile, Quote } from "../api/types";

export interface JourneyState {
  advisorSessionId?: string;
  profile?: BusinessProfile;
  quote?: Quote;
  orderId?: string;
  pin?: string;
}

interface JourneyCtx {
  journey: JourneyState;
  update: (patch: Partial<JourneyState>) => void;
  reset: () => void;
}

const STORAGE_KEY = "udyam.journey";

function load(): JourneyState {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as JourneyState) : {};
  } catch {
    return {};
  }
}

function save(state: JourneyState) {
  try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch { /* storage blocked: keep in memory */ }
}

const Ctx = createContext<JourneyCtx>({ journey: {}, update: () => {}, reset: () => {} });

export function JourneyProvider({ children }: { children: ReactNode }) {
  const [journey, setJourney] = useState<JourneyState>(load);
  const update = useCallback((patch: Partial<JourneyState>) => {
    setJourney((prev) => {
      const next = { ...prev, ...patch };
      save(next);
      return next;
    });
  }, []);
  const reset = useCallback(() => {
    save({});
    setJourney({});
  }, []);
  const value = useMemo(() => ({ journey, update, reset }), [journey, update, reset]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useJourney(): JourneyCtx {
  return useContext(Ctx);
}
