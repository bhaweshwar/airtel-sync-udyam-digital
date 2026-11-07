// App chrome: header with brand, navigation and EN/HI toggle; footer. Phase 0 owns this file.
import { useEffect } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { MOCK } from "./api/client";
import { useLang, useT } from "./i18n";
import { cx } from "./ui";

export default function Layout() {
  const { t } = useT();
  const { lang, setLang } = useLang();
  const { pathname } = useLocation();
  const wide = pathname.startsWith("/backoffice");
  // A new page starts at the top, not at the previous page's scroll position.
  useEffect(() => { window.scrollTo(0, 0); }, [pathname]);
  const navClass = ({ isActive }: { isActive: boolean }) =>
    cx("px-2 py-1.5 text-sm", isActive ? "font-medium text-foreground underline decoration-primary decoration-2 underline-offset-[6px]" : "text-muted-foreground hover:text-foreground");

  return (
    <div className="flex min-h-full flex-col">
      <header className="sticky top-0 z-20 border-b border-border bg-background">
        <div className={cx("mx-auto flex h-14 items-center gap-3 px-4", wide ? "max-w-6xl" : "max-w-md")}>
          <Link to="/" className="mr-auto leading-tight" aria-label={t("common.product")}>
            <span className="block text-[0.95rem] font-semibold tracking-tight text-foreground">{t("common.product")}</span>
            <span className="block text-xs text-muted-foreground">{t("common.brand")}</span>
          </Link>
          <nav className="hidden items-center gap-1 sm:flex" aria-label="Main">
            <NavLink to="/advisor" className={navClass}>{t("common.nav.advisor")}</NavLink>
            <NavLink to="/track" className={navClass}>{t("common.nav.track")}</NavLink>
          </nav>
          <div className="flex items-center text-sm" role="group" aria-label="Language">
            {(["en", "hi"] as const).map((l) => (
              <button key={l} type="button" onClick={() => setLang(l)} aria-pressed={lang === l}
                className={cx("px-1.5 py-1 first:border-r first:border-border", lang === l ? "font-medium text-foreground" : "text-muted-foreground hover:text-foreground")}>
                {t(`common.lang.${l}`)}
              </button>
            ))}
          </div>
        </div>
        {MOCK && <p className="border-t border-border bg-secondary px-4 py-1 text-center text-xs text-secondary-foreground">{t("common.mockBanner")}</p>}
      </header>

      <main className={cx("mx-auto w-full flex-1 px-4 py-6", wide ? "max-w-6xl" : "max-w-md")}>
        <Outlet />
      </main>

      <footer className={cx("mx-auto w-full px-4 pb-6 text-xs text-muted-foreground", wide ? "max-w-6xl" : "max-w-md")}>
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border pt-3">
          <span>{t("common.footer")}</span>
          <Link to="/backoffice" className="text-muted-foreground underline-offset-4 hover:text-foreground hover:underline">{t("common.nav.backoffice")}</Link>
        </div>
      </footer>
    </div>
  );
}
