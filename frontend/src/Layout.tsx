// App chrome: header with brand, navigation and EN/HI toggle; footer. Phase 0 owns this file.
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { MOCK } from "./api/client";
import { useLang, useT } from "./i18n";
import { cx } from "./ui";

export default function Layout() {
  const { t } = useT();
  const { lang, setLang } = useLang();
  const { pathname } = useLocation();
  const wide = pathname.startsWith("/backoffice");
  const navClass = ({ isActive }: { isActive: boolean }) =>
    cx("rounded-lg px-2.5 py-1.5 text-sm font-semibold", isActive ? "bg-brand-50 text-brand-700" : "text-muted hover:text-ink");

  return (
    <div className="flex min-h-full flex-col">
      <header className="sticky top-0 z-20 border-b border-line bg-white/95 backdrop-blur">
        <div className={cx("mx-auto flex items-center gap-3 px-4 py-2.5", wide ? "max-w-6xl" : "max-w-md")}>
          <Link to="/" className="mr-auto flex items-center gap-2" aria-label={t("common.product")}>
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-sm font-extrabold text-white" aria-hidden="true">A</span>
            <span className="leading-tight">
              <span className="block text-[0.7rem] font-semibold uppercase tracking-wider text-muted">{t("common.brand")}</span>
              <span className="block text-base font-bold text-ink">{t("common.product")}</span>
            </span>
          </Link>
          <nav className="hidden items-center gap-1 sm:flex" aria-label="Main">
            <NavLink to="/advisor" className={navClass}>{t("common.nav.advisor")}</NavLink>
            <NavLink to="/track" className={navClass}>{t("common.nav.track")}</NavLink>
          </nav>
          <div className="flex rounded-lg border border-line p-0.5 text-sm" role="group" aria-label="Language">
            {(["en", "hi"] as const).map((l) => (
              <button key={l} type="button" onClick={() => setLang(l)} aria-pressed={lang === l}
                className={cx("rounded-md px-2 py-1 font-semibold", lang === l ? "bg-brand-600 text-white" : "text-muted")}>
                {t(`common.lang.${l}`)}
              </button>
            ))}
          </div>
        </div>
        {MOCK && <p className="bg-accent-400 px-4 py-1 text-center text-xs font-semibold text-ink">{t("common.mockBanner")}</p>}
      </header>

      <main className={cx("mx-auto w-full flex-1 px-4 py-5", wide ? "max-w-6xl" : "max-w-md")}>
        <Outlet />
      </main>

      <footer className={cx("mx-auto w-full px-4 pb-6 text-xs text-muted", wide ? "max-w-6xl" : "max-w-md")}>
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line pt-3">
          <span>{t("common.footer")}</span>
          <Link to="/backoffice" className="font-semibold text-muted hover:text-ink">{t("common.nav.backoffice")}</Link>
        </div>
      </footer>
    </div>
  );
}
