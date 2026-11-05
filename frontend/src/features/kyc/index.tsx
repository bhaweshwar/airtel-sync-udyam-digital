// Smart KYC: consent, document upload, results. WS3 owns this folder. STUB (Phase 0).
import { useParams } from "react-router-dom";
import { Card, PageTitle } from "../../ui";
import { useT } from "../../i18n";

export function KycPage() {
  const { t } = useT();
  const { orderId } = useParams();
  return (
    <div>
      <PageTitle title={t("kyc.title")} subtitle={orderId} />
      <Card><p className="font-semibold">{t("stub.title")}</p><p className="text-muted">{t("stub.body", { ws: "WS3" })}</p></Card>
    </div>
  );
}
