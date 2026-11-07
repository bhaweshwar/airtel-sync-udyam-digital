// Order lookup + tracker. WS4 owns this folder.
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../../api/client";
import type { InstallSlot, Order, OrderStatus } from "../../api/types";
import { useT } from "../../i18n";
import { useJourney } from "../../state/journey";
import { useMeta } from "../../state/meta";
import { Banner, Button, buttonClass, Card, Chip, Money, PageTitle, Pill, Spinner, Timeline, cx, type Tone } from "../../ui";

const POLL_MS = 10_000;

const STATUS_TONE: Record<OrderStatus, Tone> = {
  QUOTE_ACCEPTED: "info", KYC_PENDING: "info", KYC_ACTION_REQUIRED: "warn", KYC_REVIEW: "info", KYC_VERIFIED: "ok",
  INSTALL_SCHEDULED: "ok", INSTALLING: "info", ACTIVE: "ok", REJECTED: "bad",
};

function useFormatDate() {
  const { lang } = useT();
  return useCallback((iso: string | null | undefined) => {
    if (!iso) return "";
    const d = new Date(iso.length === 10 ? iso + "T00:00:00" : iso);
    return new Intl.DateTimeFormat(lang === "hi" ? "hi-IN" : "en-IN", { weekday: "short", day: "numeric", month: "short" }).format(d);
  }, [lang]);
}

// Errors are kept as the error itself and translated when shown, so switching language re-translates them.
function errorText(e: unknown, t: (k: string) => string): string {
  if (e instanceof ApiError && e.status === 404) return t("track.lookup.notFound");
  // Only the server's PIN lock means "too many tries". Any other 429/5xx is the host being busy (for example a
  // single small instance reading KYC photos), which is temporary.
  if (e instanceof ApiError && e.code === "TOO_MANY_TRIES") return t("track.lookup.tooMany");
  if (e instanceof ApiError && (e.status === 429 || e.status >= 500)) return t("track.busy");
  return e instanceof Error ? e.message : t("common.error");
}

// ---------------------------------------------------------------- /track

export function TrackLookupPage() {
  const { t } = useT();
  const { journey, update } = useJourney();
  const navigate = useNavigate();
  const [orderId, setOrderId] = useState(journey.orderId ?? "");
  const [pin, setPin] = useState(journey.pin ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const id = orderId.trim().toUpperCase();
    setBusy(true);
    setError(null);
    try {
      await api.getOrder(id, pin.trim());
      update({ orderId: id, pin: pin.trim() });
      navigate(`/track/${encodeURIComponent(id)}`);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const input = "mt-1 w-full rounded-md border border-border bg-card px-3 py-2.5 text-base focus:border-foreground/40 focus:outline-none";
  return (
    <div>
      <PageTitle title={t("track.title")} subtitle={t("track.lookup.subtitle")} />
      <Card>
        <form onSubmit={submit} className="space-y-4">
          <label className="block">
            <span className="text-sm font-medium">{t("track.lookup.orderId")}</span>
            <input className={cx(input, "uppercase")} value={orderId} onChange={(e) => setOrderId(e.target.value)}
              placeholder={t("track.lookup.orderIdHint")} autoComplete="off" required />
          </label>
          <label className="block">
            <span className="text-sm font-medium">{t("track.lookup.pin")}</span>
            <input className={cx(input, "tabular tracking-[0.4em]")} value={pin} inputMode="numeric" pattern="[0-9]{4}" maxLength={4}
              onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))} autoComplete="off" required />
          </label>
          {error !== null && <Banner tone="bad">{errorText(error, t)}</Banner>}
          <Button type="submit" full disabled={busy || !orderId.trim() || pin.length !== 4}>
            {busy ? <Spinner label={t("common.loading")} /> : t("track.lookup.submit")}
          </Button>
        </form>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------- /track/:orderId

export function TrackOrderPage() {
  const { t, lt, lang } = useT();
  const fmt = useFormatDate();
  const meta = useMeta();
  const { orderId = "" } = useParams();
  const { journey } = useJourney();
  const pin = journey.orderId === orderId ? journey.pin : undefined;

  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<unknown>(null);
  const orderRef = useRef<Order | null>(null);
  useEffect(() => { orderRef.current = order; }, [order]);
  const [slots, setSlots] = useState<InstallSlot[]>([]);
  const [picked, setPicked] = useState<InstallSlot | null>(null);
  const [changing, setChanging] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!pin) return;
    try {
      setOrder(await api.getOrder(orderId, pin));
      setError(null);
    } catch (e) {
      // A failed background refresh keeps showing the last good copy and retries on the next tick; only the first
      // load, a wrong PIN or a lock is worth a banner.
      const quiet = orderRef.current !== null && !(e instanceof ApiError && (e.status === 404 || e.code === "TOO_MANY_TRIES"));
      if (!quiet) setError(e);
    }
  }, [orderId, pin]);

  useEffect(() => {
    load();
    const timer = setInterval(load, POLL_MS);
    return () => clearInterval(timer);
  }, [load]);

  const wantsSlots = order && (order.status === "KYC_VERIFIED" || (order.status === "INSTALL_SCHEDULED" && changing));
  useEffect(() => {
    if (!wantsSlots || !pin) return;
    api.getSlots(orderId, pin).then((r) => setSlots(r.slots)).catch(() => setSlots([]));
  }, [wantsSlots, orderId, pin]);

  if (!pin) return <Navigate to="/track" replace />;

  async function act(fn: () => Promise<Order>) {
    setBusy(true);
    try {
      setOrder(await fn());
      setError(null);
      setPicked(null);
      setChanging(false);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  if (!order) {
    return (
      <div>
        <PageTitle title={t("track.title")} subtitle={t("track.order.subtitle", { id: orderId })} />
        {error !== null ? <Banner tone="bad">{errorText(error, t)}</Banner> : <Spinner label={t("common.loading")} />}
      </div>
    );
  }

  const statusLabel = t(`track.status.${order.status}`);
  const shareText = order.eta_activation_date
    ? t("track.shareText", { id: order.order_id, status: statusLabel, date: fmt(order.eta_activation_date) })
    : t("track.shareTextNoDate", { id: order.order_id, status: statusLabel });
  const windowLabel = (w: string) => t(`track.slots.window.${w}`);
  const needsDocs = order.status === "KYC_PENDING" || order.status === "KYC_ACTION_REQUIRED";

  return (
    <div className="space-y-4">
      <PageTitle title={t("track.title")} subtitle={t("track.order.subtitle", { id: order.order_id })} />
      <div className="flex flex-wrap items-center gap-2">
        <Pill tone={STATUS_TONE[order.status]}>{statusLabel}</Pill>
        <span className="text-xs text-muted-foreground">{t("track.refreshing")}</span>
      </div>
      {error !== null && <Banner tone="bad">{errorText(error, t)}</Banner>}

      {order.next_action && (
        <Card className={cx(order.status === "KYC_ACTION_REQUIRED" && "border-warning/40")}>
          <p className="text-sm font-medium text-muted-foreground">{t("track.next.title")}</p>
          <p className="mt-1 text-lg font-semibold">{lt(order.next_action)}</p>
          {needsDocs && (
            <Link to={`/kyc/${encodeURIComponent(order.order_id)}`}
              className={cx(buttonClass("primary", "sm"), "mt-3")}>
              {t("track.next.uploadDocs")}
            </Link>
          )}
        </Card>
      )}

      {order.status === "INSTALL_SCHEDULED" && order.install_slot && !changing && (
        <Banner tone="ok">
          <span className="flex flex-wrap items-center justify-between gap-2">
            {t("track.slots.booked", { date: fmt(order.install_slot.date), window: windowLabel(order.install_slot.window) })}
            <Button size="sm" variant="secondary" onClick={() => setChanging(true)}>{t("track.slots.change")}</Button>
          </span>
        </Banner>
      )}

      {wantsSlots && (
        <Card>
          <h2 className="font-semibold">{t("track.slots.title")}</h2>
          <p className="text-sm text-muted-foreground">{t("track.slots.subtitle")}</p>
          <div className="mt-3 space-y-3">
            {[...new Set(slots.map((s) => s.date))].map((d) => (
              <div key={d}>
                <p className="text-sm font-medium">{fmt(d)}</p>
                <div className="mt-1 flex flex-wrap gap-2">
                  {slots.filter((s) => s.date === d).map((s) => (
                    <Chip key={s.window} selected={picked?.date === s.date && picked.window === s.window} onClick={() => setPicked(s)}>
                      {windowLabel(s.window)}
                    </Chip>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <Button className="mt-4" full disabled={!picked || busy}
            onClick={() => picked && act(() => api.bookSlot(order.order_id, { pin, date: picked.date, window: picked.window }))}>
            {t("track.slots.book")}
          </Button>
        </Card>
      )}

      <Card>
        <h2 className="mb-3 font-semibold">{t("track.timeline.title")}</h2>
        <Timeline steps={order.timeline.map((s) => ({
          key: s.key, label: lt(s.label), state: s.state,
          detail: s.date ? t("track.timeline.on", { date: fmt(s.date) }) : s.eta ? t("track.timeline.eta", { date: fmt(s.eta) }) : undefined,
        }))} />
      </Card>

      <Card>
        <h2 className="font-semibold">{t("track.eta.title")}</h2>
        {order.status === "ACTIVE" ? (
          <p className="mt-1 text-sm text-muted-foreground">{t("track.eta.live")}</p>
        ) : order.eta_activation_date ? (
          <>
            <p className="mt-1 text-sm text-muted-foreground">{t("track.eta.activation", { date: fmt(order.eta_activation_date) })}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {order.item_etas.map((e) => (
                <span key={e.product_id} className="rounded-md border border-border bg-secondary px-2.5 py-1 text-sm">
                  <span className="font-medium">{e.name}</span>
                  {e.eta && <span className="text-muted-foreground"> · {t("common.estimated")} {fmt(e.eta)}</span>}
                </span>
              ))}
            </div>
          </>
        ) : <p className="mt-1 text-sm text-muted-foreground">{t("track.eta.none")}</p>}
      </Card>

      <Card>
        <h2 className="font-semibold">{t("track.items.title")}</h2>
        <ul className="mt-2 divide-y divide-border">
          {order.items.map((i) => (
            <li key={i.product_id} className="flex justify-between gap-3 py-2 text-sm">
              <span>{i.name}{i.quantity > 1 && <span className="text-muted-foreground"> × {i.quantity}</span>}</span>
              <Money amount={i.monthly_inr} suffix={t("common.perMonth")} />
            </li>
          ))}
        </ul>
        <p className="mt-2 flex justify-between font-semibold">
          <span>{t("common.plusGst")}</span>
          <Money amount={order.totals.monthly_with_gst_inr} suffix={t("common.perMonth")} />
        </p>
      </Card>

      <Card>
        <h2 className="mb-2 font-semibold">{t("track.events.title")}</h2>
        <ol className="space-y-2">
          {[...order.events].reverse().map((ev, i) => (
            <li key={i} className="text-sm">
              <span className="text-muted-foreground tabular">{new Intl.DateTimeFormat(lang === "hi" ? "hi-IN" : "en-IN", { hour: "numeric", minute: "2-digit", day: "numeric", month: "short", timeZone: "Asia/Kolkata" }).format(new Date(ev.ts))}</span>
              {" · "}{lt(ev.text)}
            </li>
          ))}
        </ol>
      </Card>

      <a href={`https://wa.me/?text=${encodeURIComponent(shareText)}`} target="_blank" rel="noreferrer"
        className={cx(buttonClass("secondary"), "w-full")}>
        {t("track.share")}
      </a>

      {meta.demo_mode && order.status !== "ACTIVE" && order.status !== "REJECTED" && (
        <div className="rounded-md border border-dashed border-border p-3">
          <Button variant="secondary" full disabled={busy} onClick={() => act(() => api.advanceOrder(order.order_id, { pin }))}>
            {t("track.demo.advance")}
          </Button>
          <p className="mt-1 text-center text-xs text-muted-foreground">{t("track.demo.note")}</p>
        </div>
      )}
    </div>
  );
}
