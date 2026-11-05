// Consent screen (DPDP Act 2023): plain language first, required vs optional purposes, full notice on demand.
import { useEffect, useState } from "react";
import { api, ApiError } from "../../api/client";
import type { ConsentNotice } from "../../api/types";
import { useT } from "../../i18n";
import { Banner, Button, Card, Pill, Spinner } from "../../ui";

export function ConsentStep({ orderId, notice: banner, onDone }: { orderId: string; notice?: string; onDone: () => void }) {
  const { t, lt } = useT();
  const [notice, setNotice] = useState<ConsentNotice | null>(null);
  const [accepted, setAccepted] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.kycNotice().then(setNotice).catch(() => setError(t("common.error")));
  }, [t]);

  if (!notice) return error ? <Banner tone="bad">{error}</Banner> : <Spinner label={t("common.loading")} />;

  const requiredOk = notice.purposes.filter((p) => p.required).every((p) => accepted[p.id]);

  async function agree() {
    if (!notice) return;
    setBusy(true);
    setError(null);
    try {
      await api.giveConsent(orderId, { version: notice.version, purposes_accepted: notice.purposes.filter((p) => accepted[p.id]).map((p) => p.id) });
      onDone();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("common.error"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      {banner && <Banner tone="warn">{banner}</Banner>}
      <Card>
        <h2 className="text-lg font-semibold">{t("kyc.consent.title")}</h2>
        <p className="mt-1 text-muted">{t("kyc.consent.intro")}</p>
        <ul className="mt-4 space-y-3">
          {notice.purposes.map((p) => (
            <li key={p.id}>
              <label className="flex items-start gap-3">
                <input type="checkbox" className="mt-1 h-5 w-5 shrink-0 accent-brand-600" checked={!!accepted[p.id]}
                  onChange={(e) => setAccepted((a) => ({ ...a, [p.id]: e.target.checked }))} />
                <span className="min-w-0">
                  <span className="block">{lt(p.text)}</span>
                  <Pill tone={p.required ? "info" : "neutral"}>{p.required ? t("kyc.consent.required") : t("kyc.consent.optional")}</Pill>
                </span>
              </label>
            </li>
          ))}
        </ul>
        <details className="mt-4 rounded-xl bg-surface p-3 text-sm">
          <summary className="cursor-pointer font-semibold text-brand-700">{t("kyc.consent.fullNotice")}</summary>
          <div className="mt-2 space-y-2 whitespace-pre-line">{lt(notice.body)}</div>
          <p className="mt-3 font-semibold">{t("kyc.consent.retention")}</p>
          <p>{lt(notice.retention)}</p>
          <p className="mt-2 text-xs text-muted">{t("kyc.consent.version", { v: notice.version })}</p>
        </details>
      </Card>
      {!requiredOk && <p className="text-sm text-muted">{t("kyc.consent.needRequired")}</p>}
      {error && <Banner tone="bad">{error}</Banner>}
      <Button full size="lg" disabled={!requiredOk || busy} onClick={agree}>{t("kyc.consent.agree")}</Button>
    </div>
  );
}
