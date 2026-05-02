import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./en.json";
import fr from "./fr.json";

void i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    fr: { translation: fr },
  },
  lng: "en",
  fallbackLng: "en",
  // React already escapes rendered values; i18next escaping is not needed.
  interpolation: { escapeValue: false },
});

export default i18n;
