// Back office: leads, hand-offs, KYC reviews, orders, model. WS5 owns this folder.
import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from "react";
import { api, ApiError } from "../../api/client";
import type {
  Channel, FunnelReport, HandoffRow, KycReviewRow, LeadBand, LeadsPage, ModelReport, OrderRow, Segment,
} from "../../api/types";
import { useT } from "../../i18n";
import { useMeta } from "../../state/meta";
import { Banner, Button, Card, Chip, PageTitle, Pill, Spinner, cx, formatInr, type Tone } from "../../ui";

const KEY_STORAGE = "udyam.backofficeKey";
const TABS = ["leads", "handoffs", "kyc", "orders", "model"] as const;
type Tab = (typeof TABS)[number];
const CHANNELS: Channel[] = ["FIELD", "PARTNER", "INSIDE_SALES", "SELF_SERVE_LINK"];
const SEGMENTS: Segment[] = ["micro", "prof", "multi", "mfg"];
const PAGE = 25;
const bandTone: Record<LeadBand, Tone> = { HOT: "bad", WARM: "warn", COLD: "neutral" };

function readKey(): string {
  try { return sessionStorage.getItem(KEY_STORAGE) ?? ""; } catch { return ""; }
}
function writeKey(key: string) {
  try { if (key) sessionStorage.setItem(KEY_STORAGE, key); else sessionStorage.removeItem(KEY_STORAGE); } catch { /* storage blocked */ }
}
function when(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

/** Load once per key/deps; a 401 signs the user out. */
function useLoad<T>(load: () => Promise<T>, onAuthFail: () => void, deps: unknown[]) {
  const [state, setState] = useState<{ data?: T; error?: string; loading: boolean }>({ loading: true });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let live = true;
    setState((s) => ({ ...s, loading: true, error: undefined }));
    load().then(
      (data) => live && setState({ data, loading: false }),
      (e: unknown) => {
        if (!live) return;
        if (e instanceof ApiError && e.status === 401) onAuthFail();
        setState({ loading: false, error: e instanceof Error ? e.message : String(e) });
      },
    );
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  return { ...state, reload: () => setTick((n) => n + 1) };
}

export function BackofficePage() {
  const { t } = useT();
  const [key, setKey] = useState(readKey);
  const [tab, setTab] = useState<Tab>("leads");
  const signOut = useCallback(() => { writeKey(""); setKey(""); }, []);

  if (!key) return <Gate onKey={(k) => { writeKey(k); setKey(k); }} />;

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <PageTitle title={t("backoffice.title")} subtitle={t("backoffice.subtitle")} />
        <Button variant="ghost" size="sm" onClick={signOut}>{t("backoffice.signOut")}</Button>
      </div>
      <div role="tablist" className="-mx-4 mb-4 flex gap-1 overflow-x-auto border-b border-line px-4">
        {TABS.map((id) => (
          <button key={id} role="tab" type="button" aria-selected={tab === id} onClick={() => setTab(id)}
            className={cx("whitespace-nowrap border-b-2 px-3 py-2 text-sm font-semibold",
              tab === id ? "border-brand-600 text-brand-700" : "border-transparent text-muted hover:text-ink")}>
            {t(`backoffice.tab.${id}`)}
          </button>
        ))}
      </div>
      {tab === "leads" && <LeadsTab k={key} onAuthFail={signOut} />}
      {tab === "handoffs" && <HandoffsTab k={key} onAuthFail={signOut} />}
      {tab === "kyc" && <KycTab k={key} onAuthFail={signOut} />}
      {tab === "orders" && <OrdersTab k={key} onAuthFail={signOut} />}
      {tab === "model" && <ModelTab k={key} onAuthFail={signOut} />}
    </div>
  );
}

function Gate({ onKey }: { onKey: (k: string) => void }) {
  const { t } = useT();
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!value) return;
    setBusy(true); setError("");
    try {
      await api.backoffice.model(value);
      onKey(value);
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401 ? t("backoffice.gate.wrong") : err instanceof Error ? err.message : t("common.error"));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="mx-auto max-w-sm">
      <PageTitle title={t("backoffice.title")} subtitle={t("backoffice.subtitle")} />
      <Card>
        <form onSubmit={submit} className="space-y-3">
          <label className="block text-sm font-semibold" htmlFor="bo-key">{t("backoffice.gate.label")}</label>
          <input id="bo-key" type="password" autoComplete="current-password" value={value} onChange={(e) => setValue(e.target.value)}
            className="w-full rounded-xl border border-line px-3 py-2.5" />
          {error && <Banner tone="bad">{error}</Banner>}
          <Button type="submit" full disabled={busy || !value}>{t("backoffice.gate.submit")}</Button>
        </form>
      </Card>
    </div>
  );
}

interface TabProps { k: string; onAuthFail: () => void }

function Status({ loading, error, empty, children }: { loading: boolean; error?: string; empty?: boolean; children: ReactNode }) {
  const { t } = useT();
  if (loading) return <Spinner label={t("common.loading")} />;
  if (error) return <Banner tone="bad">{error}</Banner>;
  if (empty) return <Card><p className="text-muted">{t("backoffice.empty")}</p></Card>;
  return <>{children}</>;
}

function FilterRow<T extends string>({ label, values, value, onChange, name }: { label: string; values: T[]; value?: T; onChange: (v?: T) => void; name: (v: T) => string }) {
  const { t } = useT();
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="w-20 text-sm font-semibold text-muted">{label}</span>
      <Chip selected={!value} onClick={() => onChange(undefined)}>{t("backoffice.all")}</Chip>
      {values.map((v) => <Chip key={v} selected={value === v} onClick={() => onChange(v)}>{name(v)}</Chip>)}
    </div>
  );
}

function LeadsTab({ k, onAuthFail }: TabProps) {
  const { t } = useT();
  const [channel, setChannel] = useState<Channel>();
  const [segment, setSegment] = useState<Segment>();
  const [offset, setOffset] = useState(0);
  const { data, loading, error } = useLoad<LeadsPage>(
    () => api.backoffice.leads(k, { limit: PAGE, offset, channel, segment }), onAuthFail, [k, channel, segment, offset]);
  const total = data?.total ?? 0;

  return (
    <div className="space-y-3">
      <Card className="space-y-2">
        <FilterRow label={t("backoffice.filter.channel")} values={CHANNELS} value={channel}
          onChange={(v) => { setChannel(v); setOffset(0); }} name={(c) => t(`backoffice.channel.${c}`)} />
        <FilterRow label={t("backoffice.filter.segment")} values={SEGMENTS} value={segment}
          onChange={(v) => { setSegment(v); setOffset(0); }} name={(s) => t(`backoffice.segment.${s}`)} />
      </Card>
      <Status loading={loading} error={error} empty={!!data && data.items.length === 0}>
        <p className="text-sm text-muted">{t("backoffice.leads.total", { n: total })}</p>
        <ul className="space-y-2">
          {data?.items.map((r) => (
            <li key={r.lead_id}>
              <Card className="grid gap-2 sm:grid-cols-[1fr_auto] sm:items-center">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <Pill tone={bandTone[r.band]}>{t(`backoffice.band.${r.band}`)}</Pill>
                    <span className="font-semibold">{r.business_name}</span>
                    <span className="text-sm text-muted">{r.lead_id} · {r.city} (T{r.city_tier}) · {t(`backoffice.segment.${r.segment}`)} · {r.preferred_language} · {r.source}</span>
                  </div>
                  <p className="mt-1 text-sm"><span className="font-semibold">{t("backoffice.leads.why")}:</span> {r.top_factors.join(", ")}</p>
                  <p className="text-sm text-muted">{t("backoffice.leads.dropped", { reason: r.drop_reason ?? "" })} · {t("backoffice.leads.stage", { stage: r.stage_reached })}</p>
                </div>
                <div className="flex items-center gap-3 sm:flex-col sm:items-end">
                  <span className="text-lg font-bold tabular-nums" title={t("backoffice.leads.score")}>{Math.round(r.score * 100)}</span>
                  <Pill tone="info">{t(`backoffice.channel.${r.suggested_channel}`)}</Pill>
                </div>
              </Card>
            </li>
          ))}
        </ul>
        <div className="flex items-center justify-between">
          <Button variant="secondary" size="sm" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>{t("backoffice.leads.prev")}</Button>
          <span className="text-sm text-muted">{t("backoffice.leads.range", { from: total ? offset + 1 : 0, to: Math.min(offset + PAGE, total), total })}</span>
          <Button variant="secondary" size="sm" disabled={offset + PAGE >= total} onClick={() => setOffset(offset + PAGE)}>{t("backoffice.leads.next")}</Button>
        </div>
      </Status>
    </div>
  );
}

function HandoffsTab({ k, onAuthFail }: TabProps) {
  const { t } = useT();
  const { data, loading, error } = useLoad<HandoffRow[]>(() => api.backoffice.handoffs(k), onAuthFail, [k]);
  return (
    <Status loading={loading} error={error} empty={data?.length === 0}>
      <ul className="space-y-2">
        {data?.map((h) => (
          <li key={h.handoff_id}>
            <Card>
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold">{h.reason}</span>
                <Pill tone={h.status === "open" ? "warn" : "neutral"}>{t("backoffice.handoffs.status", { status: h.status })}</Pill>
              </div>
              {h.profile && (
                <p className="text-sm">{t("backoffice.handoffs.profile", {
                  segment: h.profile.segment ? t(`backoffice.segment.${h.profile.segment}`) : "—",
                  city: h.profile.city ?? "—", employees: h.profile.employees ?? "—",
                })}{h.profile.needs.length ? ` · ${h.profile.needs.join(", ")}` : ""}</p>
              )}
              <p className="text-xs text-muted">{h.handoff_id} · {h.session_id} · {when(h.created_at)}</p>
            </Card>
          </li>
        ))}
      </ul>
    </Status>
  );
}

function KycTab({ k, onAuthFail }: TabProps) {
  const { t, lt } = useT();
  const { data, loading, error } = useLoad<KycReviewRow[]>(() => api.backoffice.kycReviews(k), onAuthFail, [k]);
  return (
    <Status loading={loading} error={error} empty={data?.length === 0}>
      <ul className="space-y-2">
        {data?.map((r) => (
          <li key={r.order_id}>
            <Card>
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold">{r.order_id}</span>
                <Pill tone={r.verdict === "MANUAL_REVIEW" ? "warn" : "info"}>{t(`backoffice.kyc.verdict.${r.verdict}`)}</Pill>
                <span className="text-xs text-muted">{when(r.created_at)}</span>
              </div>
              <ul className="mt-2 space-y-1">
                {r.failing_checks.map((c) => (
                  <li key={c.code + (c.doc_type ?? "")} className="flex flex-wrap items-start gap-2 text-sm">
                    <Pill tone={c.status === "FAIL" ? "bad" : "warn"}>{c.status}</Pill>
                    <span>{lt(c.message)}{c.fix_hint && <span className="text-muted"> — {lt(c.fix_hint)}</span>}</span>
                  </li>
                ))}
              </ul>
            </Card>
          </li>
        ))}
      </ul>
    </Status>
  );
}

function OrdersTab({ k, onAuthFail }: TabProps) {
  const { t } = useT();
  const { demo_mode } = useMeta();
  const { data, loading, error, reload } = useLoad<OrderRow[]>(() => api.backoffice.orders(k), onAuthFail, [k]);
  const [busy, setBusy] = useState("");
  const [note, setNote] = useState<{ tone: Tone; text: string }>();
  const advance = async (id: string) => {
    setBusy(id); setNote(undefined);
    try {
      await api.advanceOrder(id, { backofficeKey: k });
      setNote({ tone: "ok", text: t("backoffice.orders.advanced", { id }) });
      reload();
    } catch (e) {
      setNote({ tone: "bad", text: e instanceof Error ? e.message : t("common.error") });
    } finally {
      setBusy("");
    }
  };
  return (
    <div className="space-y-3">
      {!demo_mode && <Banner tone="neutral">{t("backoffice.orders.demoOnly")}</Banner>}
      {note && <Banner tone={note.tone}>{note.text}</Banner>}
      <Status loading={loading && !data} error={error} empty={data?.length === 0}>
        <ul className="space-y-2">
          {data?.map((o) => (
            <li key={o.order_id}>
              <Card className="flex flex-wrap items-center gap-3">
                <div className="mr-auto min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold">{o.order_id}</span>
                    <Pill tone={o.status === "ACTIVE" ? "ok" : o.status === "REJECTED" ? "bad" : "info"}>{t(`backoffice.model.status.${o.status}`)}</Pill>
                  </div>
                  <p className="text-sm text-muted">{o.contact_name} · {o.phone_masked} · {t("backoffice.orders.monthly", { amount: formatInr(o.monthly_total_inr) })} · {when(o.created_at)}</p>
                </div>
                {demo_mode && (
                  <Button size="sm" variant="secondary" disabled={busy === o.order_id || o.status === "ACTIVE" || o.status === "REJECTED"}
                    onClick={() => advance(o.order_id)}>{t("backoffice.orders.advance")}</Button>
                )}
              </Card>
            </li>
          ))}
        </ul>
      </Status>
    </div>
  );
}

function ModelTab({ k, onAuthFail }: TabProps) {
  const { t, lt } = useT();
  const model = useLoad<ModelReport>(() => api.backoffice.model(k), onAuthFail, [k]);
  const funnel = useLoad<FunnelReport>(() => api.backoffice.funnel(k), onAuthFail, [k]);
  const m = model.data;
  const maxW = Math.max(...(m?.coefficients.map((c) => Math.abs(c.weight)) ?? [1]));
  const top = funnel.data?.baseline[0]?.count || 1;

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Status loading={model.loading} error={model.error}>
        {m && (
          <Card className="space-y-3">
            <h2 className="text-lg font-bold">{t("backoffice.model.headline")}</h2>
            <p>{t("backoffice.model.auc", { pct: Math.round(m.auc_time_split * 100), auc: m.auc_time_split.toFixed(2) })}</p>
            <p>{t("backoffice.model.lift", { lift: m.top_decile_lift.toFixed(1) })}</p>
            <p>{t("backoffice.model.capture", { pct: Math.round(m.top20_capture * 100) })}</p>
            <Banner tone="warn">{lt(m.caveat)}</Banner>
            <p className="text-sm text-muted">{t("backoffice.model.rows", { train: m.train_rows, test: m.test_rows })}</p>
            <h3 className="pt-2 font-semibold">{t("backoffice.model.weights")}</h3>
            <p className="text-xs text-muted">{t("backoffice.model.weightsHint")}</p>
            <ul className="space-y-1">
              {m.coefficients.map((c) => (
                <li key={c.feature} className="grid grid-cols-[minmax(0,11rem)_1fr_3rem] items-center gap-2 text-sm">
                  <span className="truncate" title={c.feature}>{c.feature}</span>
                  <span className="h-2 rounded-full bg-surface">
                    <span className={cx("block h-2 rounded-full", c.weight >= 0 ? "bg-ok" : "bg-bad")} style={{ width: `${(Math.abs(c.weight) / maxW) * 100}%` }} />
                  </span>
                  <span className="text-right tabular-nums">{c.weight > 0 ? "+" : ""}{c.weight.toFixed(2)}</span>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </Status>
      <Status loading={funnel.loading} error={funnel.error}>
        {funnel.data && (
          <Card className="space-y-3">
            <h2 className="text-lg font-bold">{t("backoffice.model.funnel")}</h2>
            <ul className="space-y-1.5">
              {funnel.data.baseline.map((s) => (
                <li key={s.stage} className="grid grid-cols-[8rem_1fr_3.5rem] items-center gap-2 text-sm">
                  <span>{s.stage}</span>
                  <span className="h-3 rounded bg-surface"><span className="block h-3 rounded bg-brand-500" style={{ width: `${(s.count / top) * 100}%` }} /></span>
                  <span className="text-right tabular-nums">{s.count.toLocaleString("en-IN")}</span>
                </li>
              ))}
            </ul>
            <h3 className="pt-2 font-semibold">{t("backoffice.model.live")}</h3>
            {Object.keys(funnel.data.live).length === 0 ? <p className="text-sm text-muted">{t("backoffice.empty")}</p> : (
              <div className="flex flex-wrap gap-2">
                {Object.entries(funnel.data.live).map(([status, n]) => (
                  <Pill key={status} tone="info">{t(`backoffice.model.status.${status}`)}: {n}</Pill>
                ))}
              </div>
            )}
          </Card>
        )}
      </Status>
    </div>
  );
}
