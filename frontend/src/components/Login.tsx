import { FormEvent, useState } from "react";

type LoginProps = {
  onLogin: (passcode: string) => Promise<void>;
  error: string | null;
};

export function Login({ onLogin, error }: LoginProps) {
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
      <div className="w-full max-w-md rounded-2xl border border-orange-200 bg-white p-6 shadow-sm">
        <h1 className="font-heading text-2xl font-bold text-ink">BrunoFresh</h1>
        <p className="mt-1 text-sm text-gray-600">Enter passcode to access your recipes.</p>

        <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
          <input
            type="password"
            value={passcode}
            onChange={(e) => setPasscode(e.target.value)}
            placeholder="Passcode"
            className="w-full rounded-xl border border-orange-200 px-3 py-2 outline-none focus:border-accent"
            autoComplete="current-password"
          />
          {error && <p className="text-xs text-red-600">{error}</p>}
          <button
            type="submit"
            className="w-full rounded-xl bg-accent px-4 py-2 font-semibold text-white disabled:opacity-60"
            disabled={submitting}
          >
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
