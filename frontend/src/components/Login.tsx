import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

type LoginProps = {
  onLogin: (passcode: string) => Promise<void>;
  error: string | null;
};

export function Login({ onLogin, error }: Readonly<LoginProps>) {
  const { t } = useTranslation();
  const [passcode, setPasscode] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!passcode.trim()) {
      return;
    }

    setSubmitting(true);
    try {
      await onLogin(passcode);
      setPasscode("");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-[#3e3e42] dark:bg-[#252526]">
        <h1 className="font-heading text-2xl font-bold text-ink dark:text-gray-100">BrunoFresh</h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{t("auth.loginPrompt")}</p>

        <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
          <input
            type="password"
            value={passcode}
            onChange={(e) => setPasscode(e.target.value)}
            placeholder={t("auth.passcodePlaceholder")}
            className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-gray-900 outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
            autoComplete="current-password"
          />
          {error && <p className="text-xs text-red-600">{error}</p>}
          <button
            type="submit"
            className="w-full rounded-xl bg-accent px-4 py-2 font-semibold text-white disabled:opacity-60"
            disabled={submitting}
          >
            {submitting ? t("auth.signingIn") : t("auth.signIn")}
          </button>
        </form>
      </div>
    </div>
  );
}
