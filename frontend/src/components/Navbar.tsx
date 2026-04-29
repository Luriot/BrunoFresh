import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

type Props = {
  onLogout: () => void;
  isDark: boolean;
  onToggleDark: () => void;
};

export function Navbar({ onLogout, isDark, onToggleDark }: Readonly<Props>) {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `rounded-lg px-3 py-2 text-sm ${isActive ? "bg-accent font-semibold text-white" : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-[#2d2d30]"}`;

  function closeMenu() {
    setIsMenuOpen(false);
  }

  const DarkToggle = () => (
    <button
      className="rounded-xl border border-gray-200 bg-white p-2 text-gray-700 dark:border-[#3e3e42] dark:bg-[#252526] dark:text-gray-300 dark:hover:bg-[#2d2d30]"
      onClick={onToggleDark}
      type="button"
      aria-label={isDark ? "Passer en mode clair" : "Passer en mode sombre"}
    >
      {isDark ? (
        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <circle cx="12" cy="12" r="5" />
          <path strokeLinecap="round" d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
        </svg>
      ) : (
        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 12.79A9 9 0 1111.21 3a7 7 0 009.79 9.79z" />
        </svg>
      )}
    </button>
  );

  return (
    <header className="mx-auto max-w-7xl px-4 pb-4 pt-safe-or-8 sm:px-6 lg:px-8" style={{ paddingTop: "max(2rem, calc(0.5rem + env(safe-area-inset-top, 0px)))" }}>
      {/* ── Desktop navbar ──────────────────────────────────────────── */}
      <div className="hidden nav:flex items-center gap-4 rounded-2xl border border-gray-200 bg-white/80 p-4 shadow-sm backdrop-blur dark:border-[#3e3e42] dark:bg-[#1e1e1e]/80">
        <NavLink to="/" end className="min-w-0 shrink-0 flex items-center gap-3 rounded-xl hover:opacity-80 transition-opacity">
          <img src="/pwa-192x192.png" alt="" aria-hidden="true" className="h-10 w-10 shrink-0 rounded-xl" />
          <div>
            <h1 className="font-heading text-3xl font-bold sm:text-4xl dark:text-gray-100">{t("app.title")}</h1>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{t("app.subtitle")}</p>
          </div>
        </NavLink>

        <div className="ml-auto flex flex-wrap items-center gap-2 lg:flex-nowrap">
          <nav className="flex flex-wrap rounded-xl border border-gray-200 bg-green-50 p-1 text-sm dark:border-[#3e3e42] dark:bg-[#252526]">
            <NavLink to="/" end className={navLinkClass}>{t("nav.dashboard")}</NavLink>
            <NavLink to="/history" className={({ isActive }) => navLinkClass({ isActive: isActive || location.pathname.startsWith("/lists/") })}>{t("nav.history")}</NavLink>
            <NavLink to="/pantry" className={navLinkClass}>{t("nav.pantry")}</NavLink>
            <NavLink to="/planner" className={({ isActive }) => navLinkClass({ isActive: isActive || location.pathname.startsWith("/planner") })}>{t("nav.mealPlanner")}</NavLink>
            <NavLink to="/admin" className={navLinkClass}>{t("nav.admin")}</NavLink>
          </nav>

          <div className="flex rounded-xl border border-gray-200 bg-white p-1 dark:border-[#3e3e42] dark:bg-[#252526]">
            <button
              className={`rounded-lg px-3 py-1 text-sm ${i18n.language === "en" ? "bg-accent text-white" : "text-gray-700 dark:text-gray-300"}`}
              onClick={() => void i18n.changeLanguage("en")}
              type="button"
            >
              {t("lang.switchToEn")}
            </button>
            <button
              className={`rounded-lg px-3 py-1 text-sm ${i18n.language === "fr" ? "bg-accent text-white" : "text-gray-700 dark:text-gray-300"}`}
              onClick={() => void i18n.changeLanguage("fr")}
              type="button"
            >
              {t("lang.switchToFr")}
            </button>
          </div>

          <DarkToggle />

          <button
            className="rounded-xl border border-gray-200 bg-white px-3 py-1 text-sm text-gray-700 dark:border-[#3e3e42] dark:bg-[#252526] dark:text-gray-300 dark:hover:bg-[#2d2d30]"
            onClick={onLogout}
            type="button"
          >
            {t("auth.logout")}
          </button>
        </div>
      </div>

      {/* ── Mobile navbar ───────────────────────────────────────────── */}
      <div className="nav:hidden rounded-2xl border border-gray-200 bg-white/90 shadow-sm backdrop-blur dark:border-[#3e3e42] dark:bg-[#1e1e1e]/90">
        {/* Top bar: title + actions + hamburger */}
        <div className="flex items-center gap-3 px-4 py-3">
          <NavLink to="/" end className="min-w-0 flex-1 flex items-center gap-2 rounded-lg hover:opacity-80 transition-opacity">
            <img src="/pwa-192x192.png" alt="" aria-hidden="true" className="h-8 w-8 shrink-0 rounded-lg" />
            <h1 className="font-heading text-2xl font-bold dark:text-gray-100">{t("app.title")}</h1>
          </NavLink>
          <DarkToggle />
          <button
            type="button"
            aria-label={isMenuOpen ? "Fermer le menu" : "Ouvrir le menu"}
            onClick={() => setIsMenuOpen((v) => !v)}
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-gray-200 bg-white text-gray-700 dark:border-[#3e3e42] dark:bg-[#252526] dark:text-gray-300"
          >
            {isMenuOpen ? (
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>

        {/* Dropdown nav */}
        {isMenuOpen && (
          <div className="border-t border-gray-100 px-4 pb-4 pt-2 dark:border-[#3e3e42]">
            <nav className="mb-3 flex flex-col gap-1">
              <NavLink to="/" end className={navLinkClass} onClick={closeMenu}>{t("nav.dashboard")}</NavLink>
              <NavLink to="/history" className={({ isActive }) => navLinkClass({ isActive: isActive || location.pathname.startsWith("/lists/") })} onClick={closeMenu}>{t("nav.history")}</NavLink>
              <NavLink to="/pantry" className={navLinkClass} onClick={closeMenu}>{t("nav.pantry")}</NavLink>
              <NavLink to="/planner" className={({ isActive }) => navLinkClass({ isActive: isActive || location.pathname.startsWith("/planner") })} onClick={closeMenu}>{t("nav.mealPlanner")}</NavLink>
              <NavLink to="/admin" className={navLinkClass} onClick={closeMenu}>{t("nav.admin")}</NavLink>
            </nav>

            <div className="flex items-center gap-2">
              <div className="flex rounded-xl border border-gray-200 bg-white p-1 dark:border-[#3e3e42] dark:bg-[#252526]">
                <button
                  className={`rounded-lg px-3 py-1 text-sm ${i18n.language === "en" ? "bg-accent text-white" : "text-gray-700 dark:text-gray-300"}`}
                  onClick={() => void i18n.changeLanguage("en")}
                  type="button"
                >
                  {t("lang.switchToEn")}
                </button>
                <button
                  className={`rounded-lg px-3 py-1 text-sm ${i18n.language === "fr" ? "bg-accent text-white" : "text-gray-700 dark:text-gray-300"}`}
                  onClick={() => void i18n.changeLanguage("fr")}
                  type="button"
                >
                  {t("lang.switchToFr")}
                </button>
              </div>

              <button
                className="ml-auto rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 dark:border-[#3e3e42] dark:bg-[#252526] dark:text-gray-300 dark:hover:bg-[#2d2d30]"
                onClick={() => { closeMenu(); onLogout(); }}
                type="button"
              >
                {t("auth.logout")}
              </button>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
