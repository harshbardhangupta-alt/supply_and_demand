"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export function usePoll<T>(
  fetcher: () => Promise<T>,
  intervalMs = 0,
  deps: unknown[] = []
) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const savedFetcher = useRef(fetcher);
  savedFetcher.current = fetcher;

  const run = useCallback(async () => {
    try {
      const d = await savedFetcher.current();
      setData(d);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setLoading(true);
    run();
    if (intervalMs > 0) {
      const id = setInterval(run, intervalMs);
      return () => clearInterval(id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, error, loading, refresh: run };
}
