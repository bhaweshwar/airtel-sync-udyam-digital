// Landing page. Phase 0 owns this file.
import { Link } from "react-router-dom";
import { useT } from "./i18n";

export default function Landing() {
  const { t } = useT();
  const steps = ["landing.step1", "landing.step2", "landing.step3", "landing.step4"];
  return (
    <div className="flex flex-col gap-6">
      <section className="rounded-3xl bg-brand-600 px-5 py-7 text-white">
        <h1 className="text-3xl font-extrabold leading-tight text-balance">{t("landing.title")}</h1>
        <p className="mt-3 text-brand-50">{t("landing.subtitle")}</p>
        <div className="mt-6 flex flex-col gap-3">
          <Link to="/advisor" className="rounded-xl bg-accent-400 px-5 py-3.5 text-center text-lg font-bold text-ink hover:bg-accent-500">
            {t("landing.cta")}
          </Link>
          <Link to="/track" className="rounded-xl border border-white/40 px-5 py-3 text-center font-semibold text-white hover:bg-white/10">
            {t("landing.track")}
          </Link>
        </div>
      </section>
      <ol className="flex flex-col gap-3">
        {steps.map((key, i) => (
          <li key={key} className="flex gap-3 rounded-2xl border border-line bg-white p-4">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-50 font-bold text-brand-700">{i + 1}</span>
            <p className="pt-1">{t(key)}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}
