import { FormEvent, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import axios from "axios";
import type { User } from "../types";
import { UserAvatar } from "../components/UserAvatar";
import { API_BASE_URL } from "../api/client";

async function patchMe(payload: {
  username?: string;
  current_password: string;
  new_password?: string;
}): Promise<User> {
  const resp = await axios.patch<User>(`${API_BASE_URL}/api/users/me`, payload, {
    withCredentials: true,
  });
  return resp.data;
}

type Props = {
  user: User;
  onUserUpdate: (user: User) => void;
};

export function ProfilePage({ user, onUserUpdate }: Readonly<Props>) {
  const { t } = useTranslation();

  // Avatar upload
  const avatarInputRef = useRef<HTMLInputElement>(null);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const [avatarError, setAvatarError] = useState<string | null>(null);

  async function handleAvatarChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setAvatarError(null);
    setAvatarUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const resp = await axios.post<User>(`${API_BASE_URL}/api/users/me/avatar`, form, {
        withCredentials: true,
        headers: { "Content-Type": "multipart/form-data" },
      });
      onUserUpdate(resp.data);
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const status = err.response?.status;
        if (status === 413) setAvatarError(t("profile.avatarTooLarge"));
        else if (status === 422) setAvatarError(t("profile.avatarInvalidType"));
        else setAvatarError(t("profile.avatarError"));
      } else {
        setAvatarError(t("profile.avatarError"));
      }
    } finally {
      setAvatarUploading(false);
      // Reset input so re-uploading same file triggers onChange
      if (avatarInputRef.current) avatarInputRef.current.value = "";
    }
  }

  // Change username form
  const [newUsername, setNewUsername] = useState("");
  const [usernamePassword, setUsernamePassword] = useState("");
  const [usernameError, setUsernameError] = useState<string | null>(null);
  const [usernameSaved, setUsernameSaved] = useState(false);
  const [usernameSubmitting, setUsernameSubmitting] = useState(false);

  // Change password form
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSaved, setPasswordSaved] = useState(false);
  const [passwordSubmitting, setPasswordSubmitting] = useState(false);

  async function handleUsernameSubmit(e: FormEvent) {
    e.preventDefault();
    if (!newUsername.trim() || !usernamePassword) return;
    setUsernameSubmitting(true);
    setUsernameError(null);
    setUsernameSaved(false);
    try {
      const updated = await patchMe({ username: newUsername.trim(), current_password: usernamePassword });
      onUserUpdate(updated);
      setUsernameSaved(true);
      setNewUsername("");
      setUsernamePassword("");
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 400) {
        const detail = (err.response.data as { detail?: string }).detail ?? "";
        if (detail.toLowerCase().includes("taken") || detail.toLowerCase().includes("username")) {
          setUsernameError(t("profile.errorUsernameTaken"));
        } else {
          setUsernameError(t("profile.errorCurrentPassword"));
        }
      } else if (axios.isAxiosError(err) && err.response?.status === 401) {
        setUsernameError(t("profile.errorCurrentPassword"));
      } else {
        setUsernameError(t("profile.errorCurrentPassword"));
      }
    } finally {
      setUsernameSubmitting(false);
    }
  }

  async function handlePasswordSubmit(e: FormEvent) {
    e.preventDefault();
    if (!currentPassword || !newPassword) return;
    setPasswordSubmitting(true);
    setPasswordError(null);
    setPasswordSaved(false);
    try {
      const updated = await patchMe({ current_password: currentPassword, new_password: newPassword });
      onUserUpdate(updated);
      setPasswordSaved(true);
      setCurrentPassword("");
      setNewPassword("");
    } catch {
      setPasswordError(t("profile.errorCurrentPassword"));
    } finally {
      setPasswordSubmitting(false);
    }
  }

  const inputClass =
    "w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-gray-900 outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200";

  return (
    <main className="mx-auto max-w-lg px-4 pb-10 pt-6 sm:px-6">
      <h1 className="mb-6 font-heading text-2xl font-bold dark:text-gray-100">{t("profile.title")}</h1>

      {/* Current identity + avatar */}
      <div className="mb-6 flex items-center gap-4 rounded-2xl border border-gray-200 bg-white p-4 dark:border-[#3e3e42] dark:bg-[#252526]">
        <div className="relative shrink-0">
          <UserAvatar user={user} size="h-16 w-16" className="text-2xl" />
          <button
            type="button"
            onClick={() => avatarInputRef.current?.click()}
            disabled={avatarUploading}
            className="absolute -bottom-1 -right-1 flex h-6 w-6 items-center justify-center rounded-full border-2 border-white bg-accent text-white shadow dark:border-[#252526]"
            aria-label={t("profile.changeAvatar")}
          >
            {avatarUploading ? (
              <svg className="h-3 w-3 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
            ) : (
              <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536M9 13l6.586-6.586a2 2 0 012.828 2.828L11.828 15.828a2 2 0 01-1.414.586H8v-2.414a2 2 0 01.586-1.414z" />
              </svg>
            )}
          </button>
          <input
            ref={avatarInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="sr-only"
            onChange={(e) => void handleAvatarChange(e)}
            aria-label={t("profile.changeAvatar")}
          />
        </div>
        <div>
          <p className="font-semibold dark:text-gray-100">{user.username}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {t("profile.role")}: {user.role === "admin" ? t("profile.admin") : t("profile.user")}
          </p>
          {avatarError && <p className="mt-1 text-xs text-red-600">{avatarError}</p>}
        </div>
      </div>

      {/* Change username */}
      <section className="mb-6 rounded-2xl border border-gray-200 bg-white p-4 dark:border-[#3e3e42] dark:bg-[#252526]">
        <h2 className="mb-3 font-semibold dark:text-gray-100">{t("profile.changeUsername")}</h2>
        <form onSubmit={(e) => void handleUsernameSubmit(e)} className="space-y-2">
          <input
            type="text"
            value={newUsername}
            onChange={(e) => setNewUsername(e.target.value)}
            placeholder={t("profile.newUsername")}
            className={inputClass}
            autoComplete="username"
          />
          <input
            type="password"
            value={usernamePassword}
            onChange={(e) => setUsernamePassword(e.target.value)}
            placeholder={t("profile.currentPassword")}
            className={inputClass}
            autoComplete="current-password"
          />
          {usernameError && <p className="text-xs text-red-600">{usernameError}</p>}
          {usernameSaved && <p className="text-xs text-green-600">{t("profile.saved")}</p>}
          <button
            type="submit"
            disabled={usernameSubmitting}
            className="w-full rounded-xl bg-accent px-4 py-2 font-semibold text-white disabled:opacity-60"
          >
            {usernameSubmitting ? "..." : t("profile.save")}
          </button>
        </form>
      </section>

      {/* Change password */}
      <section className="rounded-2xl border border-gray-200 bg-white p-4 dark:border-[#3e3e42] dark:bg-[#252526]">
        <h2 className="mb-3 font-semibold dark:text-gray-100">{t("profile.changePassword")}</h2>
        <form onSubmit={(e) => void handlePasswordSubmit(e)} className="space-y-2">
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            placeholder={t("profile.currentPassword")}
            className={inputClass}
            autoComplete="current-password"
          />
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder={t("profile.newPassword")}
            className={inputClass}
            autoComplete="new-password"
          />
          {passwordError && <p className="text-xs text-red-600">{passwordError}</p>}
          {passwordSaved && <p className="text-xs text-green-600">{t("profile.saved")}</p>}
          <button
            type="submit"
            disabled={passwordSubmitting}
            className="w-full rounded-xl bg-accent px-4 py-2 font-semibold text-white disabled:opacity-60"
          >
            {passwordSubmitting ? "..." : t("profile.save")}
          </button>
        </form>
      </section>
    </main>
  );
}
