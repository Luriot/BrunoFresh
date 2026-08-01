import { FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { KeyRound, ShieldCheck, Users } from "lucide-react";
import { adminListUsers, adminPatchUser, adminResetUserPassword } from "../../api/client";
import type { AdminUser, User } from "../../types";
import type { StatusMsg } from "../../types";

export function UsersTab({ currentUser }: Readonly<{ currentUser: User }>) {
  const { t, i18n } = useTranslation();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<StatusMsg>(null);
  const [resetTarget, setResetTarget] = useState<AdminUser | null>(null);
  const [newPassword, setNewPassword] = useState("");

  useEffect(() => {
    adminListUsers()
      .then(setUsers)
      .catch(() => setStatus({ text: t("admin.users.loadError"), isError: true }))
      .finally(() => setLoading(false));
  }, [t]);

  async function handleRoleChange(u: AdminUser, role: "admin" | "user") {
    if (u.role === role) return;
    try {
      const updated = await adminPatchUser(u.id, { role });
      setUsers((prev) => prev.map((x) => (x.id === u.id ? updated : x)));
    } catch (e) {
      setStatus({ text: (e as Error).message || t("admin.users.saveError"), isError: true });
    }
  }

  async function handleResetPassword(e: FormEvent) {
    e.preventDefault();
    if (!resetTarget || newPassword.length < 8) return;
    try {
      const updated = await adminResetUserPassword(resetTarget.id, newPassword);
      setUsers((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
      setResetTarget(null);
      setNewPassword("");
      setStatus({ text: t("admin.users.resetDone"), isError: false });
    } catch (err) {
      setStatus({ text: (err as Error).message || t("admin.users.saveError"), isError: true });
    }
  }

  const dateFmt = (iso: string) => new Date(iso).toLocaleDateString(i18n.language, { year: "numeric", month: "short", day: "numeric" });

  return (
    <section>
      <h2 className="mb-4 flex items-center gap-1.5 font-heading text-base font-bold text-ink dark:text-gray-100">
        <Users className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
        {t("admin.users.title")}
      </h2>

      {status && (
        <p className={`mb-4 text-sm font-medium ${status.isError ? "text-red-600 dark:text-red-400" : "text-green-600 dark:text-green-400"}`}>
          {status.text}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">{t("admin.users.loading")}</p>
      ) : users.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">{t("admin.users.empty")}</p>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-gray-200 dark:border-[#3e3e42]">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 dark:bg-[#252526] dark:text-gray-400">
              <tr>
                <th className="px-3 py-2">{t("admin.users.colUser")}</th>
                <th className="px-3 py-2">{t("admin.users.colRole")}</th>
                <th className="px-3 py-2">{t("admin.users.colCreated")}</th>
                <th className="px-3 py-2 text-right">{t("admin.users.colActions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-[#3e3e42]">
              {users.map((u) => {
                const isSelf = u.id === currentUser.id;
                return (
                  <tr key={u.id} className="align-middle">
                    <td className="px-3 py-2 font-medium text-ink dark:text-gray-100">
                      {u.username}
                      {isSelf && (
                        <span className="ml-2 rounded-full bg-accent/10 px-1.5 py-0.5 text-[10px] font-semibold text-accent">
                          {t("admin.users.you")}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${
                          u.role === "admin"
                            ? "bg-accent/15 text-accent"
                            : "bg-gray-100 text-gray-600 dark:bg-[#3e3e42] dark:text-gray-300"
                        }`}
                      >
                        {u.role === "admin" && <ShieldCheck className="h-3 w-3" aria-hidden="true" />}
                        {t(`admin.users.role.${u.role}`)}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-gray-500 dark:text-gray-400">{dateFmt(u.created_at)}</td>
                    <td className="px-3 py-2 text-right">
                      <div className="inline-flex items-center gap-2">
                        <select
                          value={u.role}
                          disabled={isSelf}
                          onChange={(e) => void handleRoleChange(u, e.target.value as "admin" | "user")}
                          className="rounded-lg border border-gray-200 bg-white px-2 py-1 text-xs text-gray-900 outline-none focus:border-accent disabled:opacity-50 dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
                          title={isSelf ? t("admin.users.selfRoleDisabled") : undefined}
                        >
                          <option value="user">{t("admin.users.role.user")}</option>
                          <option value="admin">{t("admin.users.role.admin")}</option>
                        </select>
                        <button
                          type="button"
                          disabled={isSelf}
                          onClick={() => {
                            setResetTarget(u);
                            setNewPassword("");
                          }}
                          className="inline-flex items-center gap-1 rounded-lg border border-gray-200 px-2 py-1 text-xs font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-[#3e3e42] dark:text-gray-200 dark:hover:bg-[#2d2d2d]"
                          title={isSelf ? t("admin.users.selfResetDisabled") : t("admin.users.reset")}
                        >
                          <KeyRound className="h-3 w-3" aria-hidden="true" />
                          {t("admin.users.reset")}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {resetTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <form
            onSubmit={(e) => void handleResetPassword(e)}
            className="w-full max-w-sm rounded-2xl bg-white p-5 shadow-xl dark:bg-[#1e1e1e]"
          >
            <h3 className="mb-1 font-heading text-base font-bold text-ink dark:text-gray-100">
              {t("admin.users.resetTitle")}
            </h3>
            <p className="mb-3 text-sm text-gray-500 dark:text-gray-400">
              {t("admin.users.resetFor", { user: resetTarget.username })}
            </p>
            <input
              type="password"
              autoFocus
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder={t("admin.users.newPasswordPlaceholder")}
              minLength={8}
              className="mb-3 w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
              required
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setResetTarget(null);
                  setNewPassword("");
                }}
                className="rounded-xl px-3 py-2 text-sm font-semibold text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-[#2d2d2d]"
              >
                {t("common.cancel")}
              </button>
              <button
                type="submit"
                disabled={newPassword.length < 8}
                className="rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
              >
                {t("admin.users.resetConfirm")}
              </button>
            </div>
          </form>
        </div>
      )}
    </section>
  );
}