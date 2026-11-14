"use client";

import { useCallback, useMemo, useSyncExternalStore } from "react";

const KEY = "bis_saathi_recent_standards";
const EVENT = "recent-standards:changed";
const MAX = 8;

export interface RecentStandard {
  id: number;
  standard_number: string;
  title: string;
  viewed_at: string;
}

function subscribe(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener(EVENT, callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(EVENT, callback);
  };
}

function parse(raw: string | null): RecentStandard[] {
  try {
    const value = JSON.parse(raw || "[]");
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

export function useRecentStandards() {
  const raw = useSyncExternalStore(subscribe, () => window.localStorage.getItem(KEY), () => null);
  const items = useMemo(() => parse(raw), [raw]);

  const add = useCallback((s: Omit<RecentStandard, "viewed_at">) => {
    const prev = parse(window.localStorage.getItem(KEY));
    const next = [{ ...s, viewed_at: new Date().toISOString() }, ...prev.filter((p) => p.id !== s.id)].slice(0, MAX);
    window.localStorage.setItem(KEY, JSON.stringify(next));
    window.dispatchEvent(new Event(EVENT));
  }, []);

  return { items, add };
}
