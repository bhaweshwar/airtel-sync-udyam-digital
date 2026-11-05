// Quote + checkout. WS1 owns this folder.
// The quote lives in useJourney(); every change is re-priced by the server (POST /api/quote) and replaces it.
import { useRef, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../../api/client";
import type { LineItem, Quote, SelectedItem } from "../../api/types";
import { useJourney } from "../../state/journey";
import { useT } from "../../i18n";
import { Banner, Button, Card, Money, PageTitle, Spinner, Stepper, Toggle, formatInr } from "../../ui";

function selectionOf(quote: Quote): SelectedItem[] {
  return quote.items.map((i) => ({ product_id: i.product_id, quantity: i.quantity }));
}

export function QuotePage() {
  const { t, lt, lang } = useT();
  const { journey, update } = useJourney();
  const quote = journey.quote;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [checkout, setCheckout] = useState(false);
  const [placed, setPlaced] = useState<Placed | null>(null);
  const latest = useRef(0);

  if (placed) {
    return (
      <div>
        <PageTitle title={t("quote.title")} />
        <PlacedCard placed={placed} />
      </div>
    );
  }

  if (!quote) {
    return (
      <div>
        <PageTitle title={t("quote.title")} />
        <Card>
          <p className="font-semibold">{t("quote.none.title")}</p>
          <p className="mt-1 text-muted">{t("quote.none.body")}</p>
          <Link to="/advisor" className="mt-4 inline-block rounded-xl bg-brand-600 px-4 py-2.5 font-semibold text-white hover:bg-brand-700">
            {t("quote.none.cta")}
          </Link>
        </Card>
      </div>
    );
  }

  async function reprice(selected: SelectedItem[]) {
    if (!quote) return;
    const ticket = ++latest.current;
    setBusy(true);
    setError(null);
    try {
      const next = await api.quote({ profile: quote.profile, selected, quote_id: quote.quote_id });
      if (ticket === latest.current) update({ quote: next, profile: next.profile });
    } catch (e) {
      if (ticket === latest.current) setError(e instanceof ApiError ? e.message : t("common.error"));
    } finally {
      if (ticket === latest.current) setBusy(false);
    }
  }

  const current = selectionOf(quote);
  const setQty = (pid: string, quantity: number) =>
    reprice(current.map((s) => (s.product_id === pid ? { ...s, quantity } : s)));
  const remove = (pid: string) => reprice(current.filter((s) => s.product_id !== pid));
  const add = (item: LineItem) => reprice([...current, { product_id: item.product_id, quantity: item.quantity }]);

  const validUntil = new Date(quote.valid_until + "T00:00:00").toLocaleDateString(lang === "hi" ? "hi-IN" : "en-IN", { day: "numeric", month: "long" });

  return (
    <div className="flex flex-col gap-4 pb-24">
      <PageTitle title={t("quote.title")} subtitle={t("quote.subtitle")} />

      {quote.notices.map((n, i) => (
        <Banner key={i} tone={quote.gst_products_blocked && i === 0 ? "warn" : "info"}>{lt(n)}</Banner>
      ))}
      {error && <Banner tone="bad">{error}</Banner>}

      <Card className="bg-brand-50">
        <p className="text-sm font-semibold text-brand-700">{t("quote.monthly")}</p>
        <p className="mt-1 text-4xl font-extrabold text-ink">
          <Money amount={quote.monthly_total_inr} suffix={t("common.perMonth")} />
        </p>
        <p className="mt-1 text-sm text-muted">
          {t("quote.withGst", { amount: formatInr(quote.monthly_total_with_gst_inr) })}
        </p>
        <dl className="mt-3 grid grid-cols-2 gap-3 border-t border-brand-100 pt-3 text-sm">
          <div>
            <dt className="text-muted">{t("quote.setup")}</dt>
            <dd className="font-semibold">{quote.one_time_total_inr > 0 ? <Money amount={quote.one_time_total_inr} /> : t("quote.noSetup")}</dd>
          </div>
          <div>
            <dt className="text-muted">{t("quote.contract")}</dt>
            <dd className="font-semibold">{quote.contract_months > 0 ? t("common.months", { n: quote.contract_months }) : "–"}</dd>
          </div>
        </dl>
        <p className="mt-2 text-xs text-muted">{t("quote.validUntil", { date: validUntil })}</p>
        <div className="mt-2 h-5">{busy && <Spinner label={t("quote.updating")} />}</div>
      </Card>

      <section>
        <h2 className="mb-2 text-lg font-bold">{t("quote.included")}</h2>
        {quote.items.length === 0 && <p className="text-muted">{t("quote.empty")}</p>}
        <ul className="flex flex-col gap-3">
          {quote.items.map((item) => (
            <li key={item.product_id}>
              <Card>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-semibold">{item.name}</p>
                    <p className="mt-0.5 text-sm text-muted">{lt(item.reason)}</p>
                  </div>
                  <p className="shrink-0 text-right font-bold"><Money amount={item.monthly_inr} /></p>
                </div>
                <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Stepper value={item.quantity} label={t("quote.qty", { name: item.name })} onChange={(v) => setQty(item.product_id, v)} />
                    <span className="text-xs text-muted">{t("quote.each", { price: formatInr(item.unit_price_inr) })}</span>
                  </div>
                  <Button variant="ghost" size="sm" disabled={busy} onClick={() => remove(item.product_id)}>{t("quote.remove")}</Button>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      </section>

      {quote.addons_available.length > 0 && (
        <section>
          <h2 className="text-lg font-bold">{t("quote.addons")}</h2>
          <p className="mb-2 text-sm text-muted">{t("quote.addons.hint")}</p>
          <ul className="flex flex-col divide-y divide-line rounded-2xl border border-line bg-white">
            {quote.addons_available.map((item) => (
              <li key={item.product_id} className="flex items-start gap-3 p-4">
                <div className="min-w-0 flex-1">
                  <p className="font-semibold">{item.name}</p>
                  <p className="mt-0.5 text-sm text-muted">{lt(item.reason)}</p>
                  <p className="mt-1 text-sm font-semibold">
                    <Money amount={item.monthly_inr} suffix={t("common.perMonth")} />
                    {item.setup_inr > 0 && <span className="font-normal text-muted"> · {formatInr(item.setup_inr)} {t("common.oneTime")}</span>}
                  </p>
                </div>
                <Toggle checked={false} disabled={busy} label={t("quote.addon.toggle", { name: item.name })} onChange={() => add(item)} />
              </li>
            ))}
          </ul>
        </section>
      )}

      {quote.ineligible.length > 0 && (
        <details className="rounded-2xl border border-line bg-white p-4">
          <summary className="cursor-pointer font-semibold">{t("quote.ineligible", { n: quote.ineligible.length })}</summary>
          <ul className="mt-3 flex flex-col gap-2 text-sm">
            {quote.ineligible.map((x) => (
              <li key={x.product_id}>
                <span className="font-semibold">{x.name}</span>
                <span className="text-muted"> · {lt(x.reason)}</span>
              </li>
            ))}
          </ul>
        </details>
      )}

      {checkout ? (
        <Checkout quote={quote} onCancel={() => setCheckout(false)} onPlaced={(p) => { setPlaced(p); window.scrollTo(0, 0); }} />
      ) : (
        <div className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-white/95 px-4 py-3 backdrop-blur">
          <div className="mx-auto flex max-w-xl items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="text-lg font-extrabold leading-tight"><Money amount={quote.monthly_total_inr} suffix={t("common.perMonth")} /></p>
              <p className="text-xs text-muted">{t("common.plusGst")}</p>
            </div>
            <Button size="lg" disabled={busy || quote.items.length === 0} onClick={() => setCheckout(true)}>{t("quote.confirm")}</Button>
          </div>
        </div>
      )}
    </div>
  );
}

interface Placed { orderId: string; pin: string }

function PlacedCard({ placed }: { placed: Placed }) {
  const { t } = useT();
  const navigate = useNavigate();
  return (
    <Card className="border-ok">
      <p className="text-lg font-bold">{t("quote.done.title")}</p>
      <dl className="mt-3 grid grid-cols-2 gap-3">
        <div>
          <dt className="text-sm text-muted">{t("quote.done.order")}</dt>
          <dd className="font-semibold break-all">{placed.orderId}</dd>
        </div>
        <div>
          <dt className="text-sm text-muted">{t("quote.done.pin")}</dt>
          <dd className="tabular text-3xl font-extrabold tracking-widest">{placed.pin}</dd>
        </div>
      </dl>
      <p className="mt-3 text-sm text-muted">{t("quote.done.pinNote")}</p>
      <Button full size="lg" className="mt-4" onClick={() => navigate(`/kyc/${placed.orderId}`)}>{t("quote.done.next")}</Button>
    </Card>
  );
}

function Checkout({ quote, onCancel, onPlaced }: { quote: Quote; onCancel: () => void; onPlaced: (p: Placed) => void }) {
  const { t } = useT();
  const { update } = useJourney();
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [placing, setPlacing] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const digits = phone.replace(/\D/g, "").replace(/^(91|0)(?=\d{10}$)/, "");
    if (!name.trim()) return setFieldError(t("quote.form.nameError"));
    if (!/^[6-9]\d{9}$/.test(digits)) return setFieldError(t("quote.form.phoneError"));
    setFieldError(null);
    setError(null);
    setPlacing(true);
    try {
      const res = await api.createOrder({ quote_id: quote.quote_id, contact_name: name.trim(), phone: digits });
      update({ orderId: res.order_id, pin: res.pin });
      onPlaced({ orderId: res.order_id, pin: res.pin });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.error"));
    } finally {
      setPlacing(false);
    }
  }

  const input = "mt-1 w-full rounded-xl border border-line bg-white px-3 py-2.5 text-base focus:border-brand-600 focus:outline-none";
  return (
    <Card>
      <form onSubmit={submit} className="flex flex-col gap-3" noValidate>
        <p className="text-lg font-bold">{t("quote.form.title")}</p>
        <label className="text-sm font-semibold">
          {t("quote.form.name")}
          <input className={input} value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" maxLength={120} />
        </label>
        <label className="text-sm font-semibold">
          {t("quote.form.phone")}
          <input className={input} value={phone} onChange={(e) => setPhone(e.target.value)} type="tel" inputMode="numeric"
            autoComplete="tel-national" maxLength={15} />
          <span className="mt-1 block font-normal text-muted">{t("quote.form.phoneHint")}</span>
        </label>
        {fieldError && <Banner tone="bad">{fieldError}</Banner>}
        {error && <Banner tone="bad">{error}</Banner>}
        <div className="flex gap-2">
          <Button type="submit" size="lg" className="flex-1" disabled={placing}>{placing ? t("quote.form.placing") : t("quote.form.submit")}</Button>
          <Button type="button" variant="secondary" size="lg" onClick={onCancel} disabled={placing}>{t("quote.form.cancel")}</Button>
        </div>
      </form>
    </Card>
  );
}
