// Server metadata (demo mode, "today", sample applicants), fetched once. Phase 0 owns this file.
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../api/client";
import type { Meta } from "../api/types";

const fallback: Meta = { demo_mode: false, today: "2026-07-15", sample_applicants: [], version: "" };
const MetaContext = createContext<Meta>(fallback);

export function MetaProvider({ children }: { children: ReactNode }) {
  const [meta, setMeta] = useState<Meta>(fallback);
  useEffect(() => {
    api.meta().then(setMeta).catch(() => setMeta(fallback));
  }, []);
  return <MetaContext.Provider value={meta}>{children}</MetaContext.Provider>;
}

/** useMeta().demo_mode gates demo-only controls (sample applicants, "advance order"). */
export function useMeta(): Meta {
  return useContext(MetaContext);
}
