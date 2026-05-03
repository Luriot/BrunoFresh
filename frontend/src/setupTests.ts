import "@testing-library/jest-dom";
import { vi } from "vitest";

// Mock react-i18next globally so components can render without a provider.
// t(key) returns the key itself, making assertions straightforward.
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { changeLanguage: vi.fn(), language: "en" },
  }),
  Trans: ({ i18nKey }: { i18nKey: string }) => i18nKey,
  initReactI18next: { type: "3rdParty", init: vi.fn() },
}));
