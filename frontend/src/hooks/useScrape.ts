import { useCallback, useEffect, useRef, useState } from "react";

import { fetchScrapeJob, queueScrape } from "../api/client";

type RefreshRecipes = () => Promise<void>;

async function wait(ms: number): Promise<void> {
  await new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

export function useScrape() {
  const [loading, setLoading] = useState(false);
  const [scrapeState, setScrapeState] = useState<string | null>(null);
  const isMountedRef = useRef(true);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const pollJob = useCallback(async (jobId: number, deadline: number, onRefresh: RefreshRecipes) => {
    if (!isMountedRef.current) {
      return;
    }

    if (Date.now() >= deadline) {
      setScrapeState("Scrape still running. Refresh recipes in a moment.");
      return;
    }

    const job = await fetchScrapeJob(jobId);
    if (!isMountedRef.current) {
      return;
    }

    if (job.status === "completed") {
      setScrapeState("Scrape completed.");
      await onRefresh();
      return;
    }

    if (job.status === "failed") {
      setScrapeState(job.error_message || "Scrape failed.");
      return;
    }

    await wait(1500);
    await pollJob(jobId, deadline, onRefresh);
  }, []);

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
        await pollJob(response.job_id, Date.now() + 90_000, onRefresh);
        return true;
      } finally {
        if (isMountedRef.current) {
          setLoading(false);
        }
      }
    },
    [pollJob]
  );

  return {
    loading,
    scrapeState,
    startScrape,
  };
}
