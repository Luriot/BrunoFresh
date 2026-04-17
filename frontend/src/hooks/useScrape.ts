import { useCallback, useEffect, useRef, useState } from "react";

import { buildJobStreamUrl, queueScrape } from "../api/client";

type RefreshRecipes = () => Promise<void>;

type JobStreamStatus = "pending" | "running" | "completed" | "failed";

type JobStreamEvent = {
  job_id: number;
  status: JobStreamStatus;
  error_message?: string | null;
};

export function useScrape() {
  const [loading, setLoading] = useState(false);
  const [scrapeState, setScrapeState] = useState<string | null>(null);
  const isMountedRef = useRef(true);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
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

  const watchScrapeJob = useCallback(async (jobId: number, onRefresh: RefreshRecipes): Promise<void> => {
    closeActiveStream();

    await new Promise<void>((resolve) => {
      const stream = new EventSource(buildJobStreamUrl(jobId), { withCredentials: true });
      eventSourceRef.current = stream;

      stream.addEventListener("status", (rawEvent) => {
        const evt = rawEvent as MessageEvent<string>;
        let payload: JobStreamEvent;

        try {
          payload = JSON.parse(evt.data) as JobStreamEvent;
        } catch {
          return;
        }

        if (!isMountedRef.current) {
          closeActiveStream();
          resolve();
          return;
        }

        if (payload.status === "completed") {
          setScrapeState("Scrape completed.");
          closeActiveStream();
          void onRefresh();
          resolve();
          return;
        }

        if (payload.status === "failed") {
          setScrapeState(payload.error_message || "Scrape failed.");
          closeActiveStream();
          resolve();
          return;
        }

        setScrapeState("Scraping in progress...");
      });

      stream.onerror = () => {
        if (!isMountedRef.current) {
          closeActiveStream();
          resolve();
          return;
        }

        setScrapeState("Lost live job updates. Please try again.");
        closeActiveStream();
        resolve();
      };
    });
  }, [closeActiveStream]);

  const startScrape = useCallback(
    async (rawUrl: string, onRefresh: RefreshRecipes): Promise<boolean> => {
      const trimmedUrl = rawUrl.trim();
      if (!trimmedUrl) {
        return false;
      }

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

        setScrapeState("Scraping in progress...");
        await watchScrapeJob(response.job_id, onRefresh);
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
