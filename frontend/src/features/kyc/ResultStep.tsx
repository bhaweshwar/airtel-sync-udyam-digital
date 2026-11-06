// KYC result: the verdict, then every check in green / amber / red with fix hints and "Retake" for owner-fixable ones.
import { Link } from "react-router-dom";
import type { Check, DocType, KycResult, KycVerdict } from "../../api/types";
import { useT } from "../../i18n";
import { Banner, Button, Card, Pill, Spinner, type Tone } from "../../ui";
import { PhotoButton } from "./UploadStep";

// Failures the owner can fix with a new photo (the server's owner-fixable class).
const FIXABLE = new Set(["DOC_PRESENT", "DOC_TYPE", "IMAGE_READABLE", "GSTIN_FORMAT", "UDYAM_NUMBER", "ID_VALID", "ADDRESS_RECENT", "ADDRESS_MATCH"]);
const VERDICT_TONE: Record<KycVerdict, Tone> = { VERIFIED: "ok", ACTION_REQUIRED: "warn", MANUAL_REVIEW: "info", REJECTED: "bad" };
const CHECK_TONE: Record<Check["status"], Tone> = { PASS: "ok", WARN: "warn", FAIL: "bad" };
const ORDER: Record<Check["status"], number> = { FAIL: 0, WARN: 1, PASS: 2 };

export function ResultStep({ result, orderId, onRetake, onBack, busy }: {
  result: KycResult;
  orderId: string;
  onRetake: (doc: DocType, file: File) => void;
  onBack: () => void;
  busy: string | null;
}) {
  const { t, lt } = useT();
  const checks = [...result.checks].sort((a, b) => ORDER[a.status] - ORDER[b.status]);
  const label = { PASS: t("kyc.check.pass"), WARN: t("kyc.check.warn"), FAIL: t("kyc.check.fail") };

  return (
    <div className="space-y-4">
      <Banner tone={VERDICT_TONE[result.verdict]} title={t(`kyc.verdict.${result.verdict}`)}>{t(`kyc.verdict.${result.verdict}.body`)}</Banner>
      {/* Right under the verdict, so it is in view on a phone while a retake is checked. */}
      {busy && <div><Spinner label={busy} /></div>}
      {result.gst_products_blocked && <Banner tone="bad">{t("kyc.gstBlocked")}</Banner>}
      {result.verdict === "VERIFIED" && (
        <Link to={`/track/${orderId}`} className="block"><Button full size="lg">{t("kyc.track")}</Button></Link>
      )}
      <Card>
        <ul className="divide-y divide-line">
          {checks.map((c, i) => (
            <li key={`${c.code}-${c.doc_type ?? ""}-${i}`} className="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
              <span className="mt-0.5"><Pill tone={CHECK_TONE[c.status]}>{label[c.status]}</Pill></span>
              <div className="min-w-0 flex-1">
                <p className={c.status === "PASS" ? "text-muted" : "font-medium"}>{lt(c.message)}</p>
                {c.status !== "PASS" && c.fix_hint && <p className="mt-0.5 text-sm text-muted">{lt(c.fix_hint)}</p>}
                {c.status === "FAIL" && c.doc_type && FIXABLE.has(c.code) && result.verdict === "ACTION_REQUIRED" && (
                  <div className="mt-2">
                    <PhotoButton label={`${t("kyc.slot.retake")}: ${t(`kyc.doc.${c.doc_type}`)}`} onFile={(f) => onRetake(c.doc_type as DocType, f)} disabled={!!busy} />
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      </Card>
      {result.verdict !== "VERIFIED" && <Button variant="ghost" disabled={!!busy} onClick={onBack}>{t("kyc.backToDocs")}</Button>}
    </div>
  );
}
