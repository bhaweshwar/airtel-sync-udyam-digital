// Smart KYC: consent, document upload, results. WS3 owns this folder.
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../../api/client";
import type { DocType, KycResult } from "../../api/types";
import { useT } from "../../i18n";
import { Banner, Button, PageTitle } from "../../ui";
import { ConsentStep } from "./ConsentStep";
import { ResultStep } from "./ResultStep";
import { DOC_TYPES, UploadStep, type Slot } from "./UploadStep";

// Whether consent was given for this order in this tab. The server is the source of truth: any 403 sends us back.
const consentKey = (orderId: string) => `udyam.kyc.consent.${orderId}`;
function loadConsent(orderId: string): boolean {
  try { return sessionStorage.getItem(consentKey(orderId)) === "1"; } catch { return false; }
}
function saveConsent(orderId: string, value: boolean) {
  try {
    if (value) sessionStorage.setItem(consentKey(orderId), "1");
    else sessionStorage.removeItem(consentKey(orderId));
  } catch { /* storage blocked: keep in memory */ }
}

const emptySlots = (): Record<DocType, Slot> =>
  Object.fromEntries(DOC_TYPES.map((d) => [d, { status: "empty" }])) as Record<DocType, Slot>;

export function KycPage() {
  const { t } = useT();
  const { orderId = "" } = useParams();
  const [consented, setConsented] = useState(() => loadConsent(orderId));
  const [consentNotice, setConsentNotice] = useState<string | undefined>();
  const [slots, setSlots] = useState<Record<DocType, Slot>>(emptySlots);
  const [result, setResult] = useState<KycResult | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [withdrawn, setWithdrawn] = useState(false);

  useEffect(() => { if (result) window.scrollTo({ top: 0 }); }, [result]);

  if (!orderId) {
    return (
      <div>
        <PageTitle title={t("kyc.title")} />
        <Banner tone="warn">{t("kyc.noOrder")}</Banner>
        <Link to="/advisor" className="mt-4 inline-block text-brand-700 underline">{t("kyc.toAdvisor")}</Link>
      </div>
    );
  }

  /** Show an API error; if the server says consent is missing, go back to the consent screen. */
  function handle(e: unknown): void {
    if (e instanceof ApiError && e.code === "CONSENT_REQUIRED") {
      saveConsent(orderId, false);
      setConsented(false);
      setConsentNotice(t("kyc.consent.expired"));
      return;
    }
    setError(e instanceof ApiError ? e.message : t("common.error"));
  }

  async function upload(doc: DocType, file: File) {
    setError(null);
    setSlots((s) => ({ ...s, [doc]: { status: "checking" } }));
    try {
      const res = await api.uploadDocument(orderId, doc, file);
      setSlots((s) => ({ ...s, [doc]: { status: "done", result: res } }));
      return true;
    } catch (e) {
      setSlots((s) => ({ ...s, [doc]: { status: "done", error: e instanceof ApiError ? e.message : t("common.error") } }));
      handle(e);
      return false;
    }
  }

  async function submit() {
    setError(null);
    setBusy(t("kyc.submitting"));
    try {
      setResult(await api.submitKyc(orderId));
    } catch (e) {
      handle(e);
    } finally {
      setBusy(null);
    }
  }

  async function retake(doc: DocType, file: File) {
    if (await upload(doc, file)) await submit();
  }

  async function sample(id: string) {
    setError(null);
    setBusy(t("kyc.sample.running", { id }));
    try {
      const res = await api.kycSample(orderId, id);
      setSlots(emptySlots());  // the sample's photos live on the server; retakes replace single documents
      setResult(res);
    } catch (e) {
      handle(e);
    } finally {
      setBusy(null);
    }
  }

  async function withdraw() {
    if (!window.confirm(t("kyc.withdraw.confirm"))) return;
    try {
      await api.withdrawConsent(orderId);
      saveConsent(orderId, false);
      setConsented(false);
      setSlots(emptySlots());
      setResult(null);
      setConsentNotice(undefined);
      setWithdrawn(true);
    } catch (e) {
      handle(e);
    }
  }

  return (
    <div>
      <PageTitle title={result ? t("kyc.result.title") : consented ? t("kyc.docs.title") : t("kyc.title")} subtitle={t("kyc.order", { id: orderId })} />
      {withdrawn && !consented && <div className="mb-4"><Banner tone="info">{t("kyc.withdraw.done")}</Banner></div>}
      {error && <div className="mb-4"><Banner tone="bad">{error}</Banner></div>}
      {!consented ? (
        <ConsentStep orderId={orderId} notice={consentNotice}
          onDone={() => { saveConsent(orderId, true); setConsented(true); setWithdrawn(false); setConsentNotice(undefined); }} />
      ) : result ? (
        <ResultStep result={result} orderId={orderId} onRetake={retake} onBack={() => setResult(null)} busy={busy} />
      ) : (
        <UploadStep slots={slots} onUpload={upload} onSubmit={submit} onSample={sample} busy={busy} />
      )}
      {consented && (
        <div className="mt-6 text-center">
          <Button variant="ghost" size="sm" onClick={withdraw}>{t("kyc.withdraw")}</Button>
        </div>
      )}
    </div>
  );
}
