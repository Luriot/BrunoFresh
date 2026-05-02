import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { buildJobStreamUrl, rescrapeRecipe } from "../../api/client";
import type { RecipeDetail } from "../../types";

/**
 * Encapsulates the re-scrape SSE flow.
 * Call `cleanup()` on unmount (returned from the hook).
 */
export function useRecipeRescrape(
  recipe: RecipeDetail | null,
  loadRecipe: (id: number) => void,
) {
  const { t } = useTranslation();
  const [rescraping, setRescraping] = useState(false);
  const [rescrapeMsg, setRescrapeMsg] = useState<string | null>(null);
  const rescrapeStreamRef = useRef<EventSource | null>(null);

  function cleanup() {
    rescrapeStreamRef.current?.close();
    rescrapeStreamRef.current = null;
  }

  async function handleRescrape() {
    if (!recipe) return;
    cleanup();
    setRescraping(true);
    setRescrapeMsg(t("recipe.rescrapingInProgress"));
    try {
      const response = await rescrapeRecipe(recipe.id);
      const jobId = response.job_id;
      if (!jobId) {
        setRescrapeMsg(t("recipe.rescrapeQueued"));
        await new Promise((r) => setTimeout(r, 3000));
        loadRecipe(recipe.id);
        setRescrapeMsg(null);
        setRescraping(false);
        return;
      }

      const stream = new EventSource(buildJobStreamUrl(jobId), { withCredentials: true });
      rescrapeStreamRef.current = stream;

      stream.addEventListener("status", (rawEvent) => {
        const evt = rawEvent as MessageEvent<string>;
        let payload: { status: string; message?: string | null; error_message?: string | null };
        try { payload = JSON.parse(evt.data) as typeof payload; } catch { return; }

        if (payload.status === "completed") {
          stream.close();
          rescrapeStreamRef.current = null;
          setRescrapeMsg(payload.message || t("scrape.success") || "✓ Done");
          loadRecipe(recipe.id);
          setRescraping(false);
          return;
        }
        if (payload.status === "failed") {
          stream.close();
          rescrapeStreamRef.current = null;
          setRescrapeMsg(payload.error_message || t("recipe.rescrapeError"));
          setRescraping(false);
          return;
        }
        if (payload.message) {
          setRescrapeMsg(payload.message);
        }
      });

      stream.onerror = () => {
        stream.close();
        rescrapeStreamRef.current = null;
        setRescrapeMsg(t("recipe.rescrapeError"));
        setRescraping(false);
      };
    } catch {
      setRescrapeMsg(t("recipe.rescrapeError"));
      setRescraping(false);
    }
  }

  return { rescraping, rescrapeMsg, handleRescrape, cleanup };
}
