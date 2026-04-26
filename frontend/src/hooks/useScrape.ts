import { useCallback, useEffect, useRef, useState } from "react";

import { buildJobStreamUrl, fetchRecipes, queueScrape } from "../api/client";
import i18n from "../i18n/config";
import type { DuplicateWarningInfo } from "../types";

type RefreshRecipes = () => Promise<void>;

type JobStreamStatus = "pending" | "running" | "completed" | "failed" | "duplicate_warning";

type JobStreamEvent = {
  job_id: number;
  status: JobStreamStatus;
  message?: string | null;
  error_message?: string | null;
  // duplicate_warning extras
  similar_id?: number;
  similar_title?: string;
  similar_url?: string;
  similar_image?: string | null;
  title_score?: number;
  ingredient_score?: number;
};

type SettleFn = (message?: string, refresh?: boolean) => void;

async function handleStreamError(
  targetUrl: string,
  signal: AbortSignal,
  settle: SettleFn,
): Promise<void> {
  if (signal.aborted) { settle(); return; }
  try {
    const recipes = await fetchRecipes();
    const norm = (v: string) => v.trim().replace(/\/+$/, "").toLowerCase();
    if (recipes.some((r) => norm(r.url) === norm(targetUrl))) {
      settle(i18n.t("scrape.success"), true);
      return;
    }
  } catch { /* ignore */ }
  settle(i18n.t("scrape.streamError"));
}

export function useScrape() {
  const [loading, setLoading] = useState(false);
  const [scrapeState, setScrapeState] = useState<string | null>(null);
  const [duplicateWarning, setDuplicateWarning] = useState<{
    similarRecipe: DuplicateWarningInfo;
    pendingUrl: string;
    onRefresh: RefreshRecipes;
  } | null>(null);

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
    onDuplicate: (info: DuplicateWarningInfo) => void,
  ): Promise<void> => {
    closeActiveStream();

    await new Promise<void>((resolve) => {
      if (signal.aborted) { resolve(); return; }

      const stream = new EventSource(buildJobStreamUrl(jobId), { withCredentials: true });
      eventSourceRef.current = stream;
      let settled = false;

      const settle = (nextState?: string, shouldRefresh = false) => {
        if (settled) return;
        settled = true;
        signal.removeEventListener("abort", onAbort);
        closeActiveStream();
        if (nextState && !signal.aborted) setScrapeState(nextState);
        if (shouldRefresh && !signal.aborted) void onRefresh();
        resolve();
      };

      const onAbort = () => settle();
      signal.addEventListener("abort", onAbort, { once: true });

      stream.addEventListener("status", (rawEvent) => {
        const evt = rawEvent as MessageEvent<string>;
        let payload: JobStreamEvent;
        try { payload = JSON.parse(evt.data) as JobStreamEvent; } catch { return; }
        if (signal.aborted) { settle(); return; }

        if (payload.status === "completed") {
          settle(payload.message || i18n.t("scrape.success"), true);
          return;
        }
        if (payload.status === "failed") {
          settle(payload.error_message || i18n.t("scrape.failed"));
          return;
        }
        if (payload.status === "duplicate_warning") {
          settle(); // stop loading
          onDuplicate({
            id: payload.similar_id!,
            title: payload.similar_title!,
            url: payload.similar_url!,
            image_local_path: payload.similar_image ?? null,
            title_score: payload.title_score ?? 0,
            ingredient_score: payload.ingredient_score ?? 0,
          });
          return;
        }
        setScrapeState(payload.message || i18n.t("scrape.inProgress"));
      });

      stream.onerror = () => {
        closeActiveStream();
        void handleStreamError(targetUrl, signal, settle);
      };
    });
  }, [closeActiveStream]);

  const startScrape = useCallback(
    async (rawUrl: string, onRefresh: RefreshRecipes, force = false): Promise<boolean> => {
      const trimmedUrl = rawUrl.trim();
      if (!trimmedUrl) return false;

      const controller = beginRun();
      const { signal } = controller;

      setLoading(true);
      setScrapeState(null);
      setDuplicateWarning(null);

      try {
        const response = await queueScrape(trimmedUrl, force);
        if (signal.aborted) return false;

        if (response.status === "completed") {
          setScrapeState(response.message);
          await onRefresh();
          return true;
        }
        if (!response.job_id) {
          setScrapeState(i18n.t("scrape.noJobId"));
          return true;
        }

        await watchScrapeJob(
          response.job_id,
          trimmedUrl,
          onRefresh,
          signal,
          (info) => {
            setDuplicateWarning({ similarRecipe: info, pendingUrl: trimmedUrl, onRefresh });
            setLoading(false);
          },
        );
        return true;
      } finally {
        if (!signal.aborted) setLoading(false);
      }
    },
    [beginRun, watchScrapeJob]
  );

  const confirmImport = useCallback(async () => {
    if (!duplicateWarning) return;
    const { pendingUrl, onRefresh } = duplicateWarning;
    setDuplicateWarning(null);
    await startScrape(pendingUrl, onRefresh, true);
  }, [duplicateWarning, startScrape]);

  const dismissDuplicate = useCallback(() => {
    setDuplicateWarning(null);
    setScrapeState(null);
  }, []);

  return {
    loading,
    scrapeState,
    duplicateWarning,
    startScrape,
    confirmImport,
    dismissDuplicate,
  };
}
