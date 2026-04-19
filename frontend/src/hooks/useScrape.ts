import { useCallback, useEffect, useRef, useState } from "react";

import { buildJobStreamUrl, fetchRecipes, queueScrape } from "../api/client";

type RefreshRecipes = () => Promise<void>;

type JobStreamStatus = "pending" | "running" | "completed" | "failed";

type JobStreamEvent = {
  job_id: number;
  status: JobStreamStatus;
  message?: string | null;
  error_message?: string | null;
};

export function useScrape() {
  const [loading, setLoading] = useState(false);
  const [scrapeState, setScrapeState] = useState<string | null>(null);
  const isMountedRef = useRef(true);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      eventSourceRef.current?.close();
      eventSourceRef.current = null;
    };
  }, []);

  const closeActiveStream = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
  }, []);

  const watchScrapeJob = useCallback(async (jobId: number, targetUrl: string, onRefresh: RefreshRecipes): Promise<void> => {
    closeActiveStream();

    await new Promise<void>((resolve) => {
      const stream = new EventSource(buildJobStreamUrl(jobId), { withCredentials: true });
      eventSourceRef.current = stream;

      const finalize = (nextState: string, shouldRefresh = false) => {
        if (!isMountedRef.current) {
          closeActiveStream();
          resolve();
          return;
        }

        setScrapeState(nextState);
        closeActiveStream();
        if (shouldRefresh) {
          void onRefresh();
        }
        resolve();
      };

      stream.addEventListener("status", (rawEvent) => {
        const evt = rawEvent as MessageEvent<string>;
        let payload: JobStreamEvent;

        try {
          payload = JSON.parse(evt.data) as JobStreamEvent;
        } catch {
          return;
        }

        if (payload.status === "completed") {
          finalize(payload.message || "Recette ajoutée avec succès !", true);
          return;
        }

        if (payload.status === "failed") {
          finalize(payload.error_message || "Scrape failed.");
          return;
        }

        setScrapeState(payload.message || "Scraping in progress...");
      });

      stream.onerror = () => {
        // Fallback ultra léger (une seule requête) si le stream casse.
        void (async () => {
          try {
            const recipes = await fetchRecipes();
            const normalizeUrl = (value: string) => value.trim().replace(/\/+$/, "").toLowerCase();
            const target = normalizeUrl(targetUrl);
            const found = recipes.some((recipe) => normalizeUrl(recipe.url) === target);

            if (found) {
              finalize("Recette ajoutée avec succès !", true);
              return;
            }
          } catch {
            // ignore and show resilient stream error message below
          }

          finalize("Connexion temps réel interrompue. Utilise Refresh.");
        })();
      };
    });
  }, [closeActiveStream]);

  const startScrape = useCallback(
    async (rawUrl: string, onRefresh: RefreshRecipes): Promise<boolean> => {
      const trimmedUrl = rawUrl.trim();
      if (!trimmedUrl) {
        return false;
      }

      isMountedRef.current = true;
      setLoading(true);
      setScrapeState(null);

      try {
        const response = await queueScrape(trimmedUrl);

        if (response.status === "completed") {
          setScrapeState(response.message);
          await onRefresh();
          return true;
        }

        if (!response.job_id) {
          setScrapeState("Scrape job started but no job id returned.");
          return true;
        }

        await watchScrapeJob(response.job_id, trimmedUrl, onRefresh);
        return true;
      } finally {
        if (isMountedRef.current) {
          setLoading(false);
        }
      }
    },
    [watchScrapeJob]
  );

  return {
    loading,
    scrapeState,
    startScrape,
  };
}
