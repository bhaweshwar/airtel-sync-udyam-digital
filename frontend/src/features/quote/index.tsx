// Quote + checkout. WS1 owns this folder. STUB (Phase 0).
import { Card, PageTitle } from "../../ui";
import { useT } from "../../i18n";

export function QuotePage() {
  const { t } = useT();
  return (
    <div>
      <PageTitle title={t("quote.title")} />
      <Card><p className="font-semibold">{t("stub.title")}</p><p className="text-muted">{t("stub.body", { ws: "WS1" })}</p></Card>
    </div>
  );
}
