import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

type Props = {
  onLogout: () => void;
};

export function Navbar({ onLogout }: Props) {
  const { t, i18n } = useTranslation();

  return (
    <header className="mx-auto max-w-7xl px-4 pb-4 pt-8 sm:px-6 lg:px-8">
      <div className="flex flex-col gap-4 rounded-2xl border border-orange-200 bg-white/80 p-4 backdrop-blur sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-heading text-3xl font-bold sm:text-4xl">{t("app.title")}</h1>
          <p className="mt-1 text-sm text-gray-600">{t("app.subtitle")}</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <nav className="flex rounded-xl border border-orange-200 bg-orange-50 p-1 text-sm">
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                `rounded-lg px-3 py-1 ${isActive ? "bg-accent font-semibold text-white" : "text-gray-700"}`
              }
            >
              {t("nav.dashboard")}
            </NavLink>
            <NavLink
              to="/history"
              className={({ isActive }) =>
                `rounded-lg px-3 py-1 ${isActive ? "bg-accent font-semibold text-white" : "text-gray-700"}`
              }
            >
              {t("nav.history")}
            </NavLink>
          </nav>

          <div className="flex rounded-xl border border-orange-200 bg-white p-1">
            <button
              className={`rounded-lg px-3 py-1 text-sm ${
                i18n.language === "en" ? "bg-accent text-white" : "text-gray-700"
              }`}
              onClick={() => void i18n.changeLanguage("en")}
              type="button"
            >
              {t("lang.switchToEn")}
            </button>
            <button
              className={`rounded-lg px-3 py-1 text-sm ${
                i18n.language === "fr" ? "bg-accent text-white" : "text-gray-700"
              }`}
              onClick={() => void i18n.changeLanguage("fr")}
              type="button"
            >
              {t("lang.switchToFr")}
            </button>
          </div>

          <button
            className="rounded-xl border border-orange-200 bg-white px-3 py-1 text-sm text-gray-700"
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
