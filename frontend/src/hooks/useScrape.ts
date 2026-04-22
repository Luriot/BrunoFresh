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
  const eventSourceRef = useRef<EventSource | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
      eventSourceRef.current?.close();
      eventSourceRef.current = null;
    };
  }, []);

  const closeActiveStream = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
  }, []);

  const beginRun = useCallback((): AbortController => {
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;
    return controller;
  }, []);

  const watchScrapeJob = useCallback(async (
    jobId: number,
    targetUrl: string,
    onRefresh: RefreshRecipes,
    signal: AbortSignal,
  ): Promise<void> => {
    closeActiveStream();

    await new Promise<void>((resolve) => {
      if (signal.aborted) {
        resolve();
        return;
      }

      const stream = new EventSource(buildJobStreamUrl(jobId), { withCredentials: true });
      eventSourceRef.current = stream;
      let settled = false;

      const settle = (nextState?: string, shouldRefresh = false) => {
        if (settled) {
          return;
        }
        settled = true;

        signal.removeEventListener("abort", onAbort);
        closeActiveStream();

        if (nextState && !signal.aborted) {
          setScrapeState(nextState);
        }

        if (shouldRefresh && !signal.aborted) {
          void onRefresh();
        }

        resolve();
      };

      const onAbort = () => {
        settle();
      };

      signal.addEventListener("abort", onAbort, { once: true });

      stream.addEventListener("status", (rawEvent) => {
        const evt = rawEvent as MessageEvent<string>;
        let payload: JobStreamEvent;

        try {
          payload = JSON.parse(evt.data) as JobStreamEvent;
        } catch {
          return;
        }

        if (signal.aborted) {
          settle();
          return;
        }

        if (payload.status === "completed") {
          settle(payload.message || "Recette ajoutée avec succès !", true);
          return;
        }

        if (payload.status === "failed") {
          settle(payload.error_message || "Scrape failed.");
          return;
        }

        setScrapeState(payload.message || "Scraping in progress...");
      });

      stream.onerror = () => {
        // Fermer le flux immédiatement pour éviter que le navigateur n'essaie de reconnecter en boucle (spam resubscribe)
        closeActiveStream();

        // Fallback ultra léger (une seule requête) si le stream casse.
        void (async () => {
          if (signal.aborted) {
            settle();
            return;
          }

          try {
            const recipes = await fetchRecipes();
            const normalizeUrl = (value: string) => value.trim().replace(/\/+$/, "").toLowerCase();
            const target = normalizeUrl(targetUrl);
            const found = recipes.some((recipe) => normalizeUrl(recipe.url) === target);

            if (found) {
              settle("Recette ajoutée avec succès !", true);
              return;
            }
          } catch {
            // ignore and show resilient stream error message below
          }

          settle("Connexion temps réel interrompue. Utilise Refresh.");
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

      const controller = beginRun();
      const { signal } = controller;

      setLoading(true);
      setScrapeState(null);

      try {
        const response = await queueScrape(trimmedUrl);

        if (signal.aborted) {
          return false;
        }

        if (response.status === "completed") {
          setScrapeState(response.message);
          await onRefresh();
          return true;
        }

        if (!response.job_id) {
          setScrapeState("Scrape job started but no job id returned.");
          return true;
        }

        await watchScrapeJob(response.job_id, trimmedUrl, onRefresh, signal);
        return true;
      } finally {
        if (!signal.aborted) {
          setLoading(false);
        }
      }
    },
    [beginRun, watchScrapeJob]
  );

  return {
    loading,
    scrapeState,
    startScrape,
  };
}
