// Four upload slots (camera on phones), each with a status Pill and what we read, plus the demo sample picker.
import { useRef } from "react";
import type { DocType, DocumentResult } from "../../api/types";
import { useT } from "../../i18n";
import { useMeta } from "../../state/meta";
import { Banner, Button, Card, Chip, Pill, Spinner } from "../../ui";

export const DOC_TYPES: DocType[] = ["gst_certificate", "udyam_certificate", "signatory_id", "address_proof"];

export interface Slot { status: "empty" | "checking" | "done"; result?: DocumentResult; error?: string }

export function slotTone(slot: Slot): "neutral" | "info" | "ok" | "bad" {
  if (slot.status === "checking") return "info";
  if (slot.status === "empty") return "neutral";
  return slot.error || !slot.result?.readable || slot.result.issues.some((i) => i.status === "FAIL") ? "bad" : "ok";
}

/** A camera / file picker button. `capture` opens the back camera on phones. */
export function PhotoButton({ label, onFile, variant = "secondary" }: { label: string; onFile: (f: File) => void; variant?: "primary" | "secondary" }) {
  const input = useRef<HTMLInputElement>(null);
  return (
    <>
      <input ref={input} type="file" accept="image/*" capture="environment" className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value = ""; }} />
      <Button size="sm" variant={variant} onClick={() => input.current?.click()}>{label}</Button>
    </>
  );
}

export function UploadStep({ slots, onUpload, onSubmit, onSample, busy }: {
  slots: Record<DocType, Slot>;
  onUpload: (doc: DocType, file: File) => void;
  onSubmit: () => void;
  onSample: (id: string) => void;
  busy: string | null;
}) {
  const { t, lt } = useT();
  const meta = useMeta();
  const added = DOC_TYPES.filter((d) => slots[d].status === "done" && !slots[d].error).length;
  const anyChecking = DOC_TYPES.some((d) => slots[d].status === "checking");

  return (
    <div className="space-y-4">
      <p className="text-muted">{t("kyc.docs.intro")}</p>
      {DOC_TYPES.map((d) => {
        const slot = slots[d];
        const tone = slotTone(slot);
        const pill = slot.status === "checking" ? t("kyc.slot.checking") : slot.status === "empty" ? t("kyc.slot.empty")
          : tone === "ok" ? t("kyc.slot.ok") : t("kyc.slot.issue");
        const fields = Object.entries(slot.result?.fields ?? {});
        return (
          <Card key={d}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="font-semibold">{t(`kyc.doc.${d}`)}</p>
                <p className="text-sm text-muted">{t(`kyc.doc.${d}.hint`)}</p>
              </div>
              <span className="shrink-0 whitespace-nowrap"><Pill tone={tone}>{pill}</Pill></span>
            </div>
            {slot.error && <div className="mt-3"><Banner tone="bad">{slot.error}</Banner></div>}
            {slot.result?.issues.filter((i) => i.status !== "PASS").map((i) => (
              <div key={i.code} className="mt-3">
                <Banner tone={i.status === "FAIL" ? "bad" : "warn"} title={lt(i.message)}>{i.fix_hint && lt(i.fix_hint)}</Banner>
              </div>
            ))}
            {fields.length > 0 && (
              <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
                {fields.map(([k, v]) => (
                  <div key={k} className="contents">
                    <dt className="text-muted">{t(`kyc.field.${k}`)}</dt>
                    <dd className="min-w-0 break-words font-medium">{v}</dd>
                  </div>
                ))}
              </dl>
            )}
            {!!slot.result && slot.result.quality.skew_deg !== 0 && <p className="mt-2 text-xs text-muted">{t("kyc.slot.straightened")}</p>}
            <div className="mt-3">
              <PhotoButton label={slot.status === "empty" ? t("kyc.slot.take") : t("kyc.slot.retake")} onFile={(f) => onUpload(d, f)}
                variant={slot.status === "empty" ? "primary" : "secondary"} />
            </div>
          </Card>
        );
      })}

      {added < 4 && added > 0 && <p className="text-sm text-muted">{t("kyc.missing", { n: added })}</p>}
      <Button full size="lg" disabled={added === 0 || anyChecking || !!busy} onClick={onSubmit}>{t("kyc.submit")}</Button>

      {meta.demo_mode && meta.sample_applicants.length > 0 && (
        <Card className="border-dashed">
          <div className="flex items-center gap-2"><Pill tone="warn">{t("common.demo")}</Pill><p className="font-semibold">{t("kyc.sample.title")}</p></div>
          <p className="mt-1 text-sm text-muted">{t("kyc.sample.body")}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {meta.sample_applicants.map((id) => <Chip key={id} disabled={!!busy} onClick={() => onSample(id)}>{id}</Chip>)}
          </div>
        </Card>
      )}
      {busy && <Spinner label={busy} />}
    </div>
  );
}
