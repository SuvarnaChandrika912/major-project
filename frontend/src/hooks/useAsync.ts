"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface AsyncState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => Promise<void>;
  setData: (data: T | null) => void;
}

function message(err: unknown) {
  return err instanceof Error ? err.message : "Something went wrong.";
}

/** Loads data on mount (and when deps change), exposing loading/error state and a reload function. */
export function useAsync<T>(loader: () => Promise<T>, deps: unknown[] = []): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloading, setReloading] = useState(false);
  const depsKey = JSON.stringify(deps);
  const [settledKey, setSettledKey] = useState<string | null>(null);
  const loaderRef = useRef(loader);

  useEffect(() => {
    loaderRef.current = loader;
  });

  useEffect(() => {
    let cancelled = false;
    loaderRef.current()
      .then((result) => {
        if (cancelled) return;
        setData(result);
        setError(null);
      })
      .catch((err) => !cancelled && setError(message(err)))
      .finally(() => !cancelled && setSettledKey(depsKey));
    return () => {
      cancelled = true;
    };
  }, [depsKey]);

  const reload = useCallback(async () => {
    setReloading(true);
    setError(null);
    try {
      setData(await loaderRef.current());
    } catch (err) {
      setError(message(err));
    } finally {
      setReloading(false);
    }
  }, []);

  return { data, error, loading: reloading || settledKey !== depsKey, reload, setData };
}
