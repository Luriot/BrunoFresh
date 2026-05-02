import { FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { createTag, deleteTag, fetchTags } from "../../api/client";
import type { Tag } from "../../types";
import { Tag as TagIcon, X } from "lucide-react";

type StatusMsg = { text: string; isError: boolean } | null;

export function TagsTab() {
  const { t } = useTranslation();
  const [tags, setTags] = useState<Tag[]>([]);
  const [newTagName, setNewTagName] = useState("");
  const [newTagColor, setNewTagColor] = useState("#6b7280");
  const [tagLoading, setTagLoading] = useState(false);
  const [status, setStatus] = useState<StatusMsg>(null);

  useEffect(() => {
    fetchTags().then(setTags).catch(() => {});
  }, []);

  async function handleCreateTag(e: FormEvent) {
    e.preventDefault();
    const name = newTagName.trim();
    if (!name) return;
    setTagLoading(true);
    try {
      const tag = await createTag(name, newTagColor);
      setTags((prev) => [...prev, tag]);
      setNewTagName("");
      setNewTagColor("#6b7280");
    } catch {
      setStatus({ text: t("tags.createError"), isError: true });
    } finally {
      setTagLoading(false);
    }
  }

  async function handleDeleteTag(tagId: number) {
    if (!confirm(t("tags.confirmDelete"))) return;
    try {
      await deleteTag(tagId);
      setTags((prev) => prev.filter((tg) => tg.id !== tagId));
    } catch {
      setStatus({ text: t("tags.deleteError"), isError: true });
    }
  }

  return (
    <section>
      <h2 className="mb-4 flex items-center gap-1.5 font-heading text-base font-bold text-ink dark:text-gray-100">
        <TagIcon className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
        {t("tags.manage")}
      </h2>
      <form onSubmit={(e) => void handleCreateTag(e)} className="mb-4 flex flex-wrap items-center gap-2">
        <input
          type="text"
          value={newTagName}
          onChange={(e) => setNewTagName(e.target.value)}
          placeholder={t("tags.namePlaceholder")}
          className="flex-1 rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
          required
        />
        <input
          type="color"
          value={newTagColor}
          onChange={(e) => setNewTagColor(e.target.value)}
          className="h-9 w-10 cursor-pointer rounded-lg border border-gray-200 p-0.5 dark:border-[#3e3e42]"
          title={t("tags.colorLabel")}
        />
        <button
          type="submit"
          disabled={tagLoading || !newTagName.trim()}
          className="rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
        >
          {t("tags.add")}
        </button>
      </form>

      {status && (
        <p className={`mb-4 text-sm font-medium ${status.isError ? "text-red-600 dark:text-red-400" : "text-green-600 dark:text-green-400"}`}>
          {status.text}
        </p>
      )}

      {tags.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">{t("tags.empty")}</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {tags.map((tag) => (
            <span
              key={tag.id}
              className="flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold text-white"
              style={{ backgroundColor: tag.color ?? "#6b7280" }}
            >
              {tag.name}
              <button
                type="button"
                onClick={() => void handleDeleteTag(tag.id)}
                className="ml-0.5 opacity-70 hover:opacity-100"
                aria-label={t("tags.delete")}
              >
                <X className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </span>
          ))}
        </div>
      )}
    </section>
  );
}
