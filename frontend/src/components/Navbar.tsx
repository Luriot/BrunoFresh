import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

type Props = {
  onLogout: () => void;
};

export function Navbar({ onLogout }: Props) {
  const { t, i18n } = useTranslation();

  return (
    <header className="mx-auto max-w-7xl px-4 pb-4 pt-8 sm:px-6 lg:px-8">
      <div className="flex flex-col gap-4 rounded-2xl border border-gray-200 bg-white/80 p-4 shadow-sm backdrop-blur sm:flex-row sm:items-center sm:justify-between dark:border-[#3e3e42] dark:bg-[#1e1e1e]/80">
        <div>
          <h1 className="font-heading text-3xl font-bold sm:text-4xl dark:text-gray-100">{t("app.title")}</h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{t("app.subtitle")}</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <nav className="flex rounded-xl border border-gray-200 bg-green-50 p-1 text-sm dark:border-[#3e3e42] dark:bg-[#252526]">
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                `rounded-lg px-3 py-1 ${isActive ? "bg-accent font-semibold text-white" : "text-gray-700 dark:text-gray-300 dark:hover:text-white"}`
              }
            >
              {t("nav.dashboard")}
            </NavLink>
            <NavLink
              to="/history"
              className={({ isActive }) =>
                `rounded-lg px-3 py-1 ${isActive ? "bg-accent font-semibold text-white" : "text-gray-700 dark:text-gray-300 dark:hover:text-white"}`
              }
            >
              {t("nav.history")}
            </NavLink>
          </nav>

          <div className="flex rounded-xl border border-gray-200 bg-white p-1 dark:border-[#3e3e42] dark:bg-[#252526]">
            <button
              className={`rounded-lg px-3 py-1 text-sm ${
                i18n.language === "en" ? "bg-accent text-white" : "text-gray-700 dark:text-gray-300"
              }`}
              onClick={() => void i18n.changeLanguage("en")}
              type="button"
            >
              {t("lang.switchToEn")}
            </button>
            <button
              className={`rounded-lg px-3 py-1 text-sm ${
                i18n.language === "fr" ? "bg-accent text-white" : "text-gray-700 dark:text-gray-300"
              }`}
              onClick={() => void i18n.changeLanguage("fr")}
              type="button"
            >
              {t("lang.switchToFr")}
            </button>
          </div>

          <button
            className="rounded-xl border border-gray-200 bg-white px-3 py-1 text-sm text-gray-700 dark:border-[#3e3e42] dark:bg-[#252526] dark:text-gray-300 dark:hover:bg-[#2d2d30]"
            onClick={onLogout}
            type="button"
          >
            {t("auth.logout")}
          </button>
        </div>
      </div>
    </header>
  );
}
