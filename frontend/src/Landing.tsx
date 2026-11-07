// Landing page. Phase 0 owns this file.
import { Link } from "react-router-dom";
import { useT } from "./i18n";
import { buttonClass } from "./ui";

export default function Landing() {
  const { t } = useT();
  const steps = ["landing.step1", "landing.step2", "landing.step3", "landing.step4"];
  return (
    <div className="flex flex-col gap-10 pt-2">
      <section>
        <h1 className="text-[2rem] font-semibold leading-[1.15] tracking-tight text-balance">{t("landing.title")}</h1>
        <p className="mt-3 text-muted-foreground">{t("landing.subtitle")}</p>
        <div className="mt-6 flex flex-col gap-3">
          <Link to="/advisor" className={buttonClass("primary", "lg")}>{t("landing.cta")}</Link>
          <Link to="/track" className="text-center text-sm text-muted-foreground underline underline-offset-4 hover:text-foreground">
            {t("landing.track")}
          </Link>
        </div>
      </section>
      <section>
        <h2 className="text-sm font-medium text-muted-foreground">{t("landing.how")}</h2>
        <ol className="mt-2 divide-y divide-border border-y border-border">
          {steps.map((key, i) => (
            <li key={key} className="flex gap-4 py-3.5">
              <span className="w-4 shrink-0 pt-px font-mono text-sm text-muted-foreground tabular">{i + 1}</span>
              <p>{t(key)}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
