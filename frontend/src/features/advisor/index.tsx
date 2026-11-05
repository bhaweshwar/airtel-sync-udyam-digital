// Advisor chat + voice input. WS2 owns this folder. STUB (Phase 0).
import { Card, PageTitle } from "../../ui";
import { useT } from "../../i18n";

export function AdvisorPage() {
  const { t } = useT();
  return (
    <div>
      <PageTitle title={t("advisor.title")} />
      <Card><p className="font-semibold">{t("stub.title")}</p><p className="text-muted">{t("stub.body", { ws: "WS2" })}</p></Card>
    </div>
  );
}
