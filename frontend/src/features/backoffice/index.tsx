// Back office: leads, hand-offs, KYC reviews, orders, model. WS5 owns this folder. STUB (Phase 0).
import { Card, PageTitle } from "../../ui";
import { useT } from "../../i18n";

export function BackofficePage() {
  const { t } = useT();
  return (
    <div>
      <PageTitle title={t("backoffice.title")} />
      <Card><p className="font-semibold">{t("stub.title")}</p><p className="text-muted">{t("stub.body", { ws: "WS5" })}</p></Card>
    </div>
  );
}
