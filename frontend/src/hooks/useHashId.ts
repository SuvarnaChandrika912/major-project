"use client";

import { useSyncExternalStore } from "react";

function subscribe(callback: () => void) {
  window.addEventListener("hashchange", callback);
  return () => window.removeEventListener("hashchange", callback);
}

/** Reads a numeric id from a URL hash such as `#report-12` (null on the server or when absent). */
export function useHashId(prefix: string): number | null {
  const hash = useSyncExternalStore(subscribe, () => window.location.hash, () => "");
  const match = new RegExp(`^#${prefix}-(\\d+)$`).exec(hash);
  return match ? Number(match[1]) : null;
}
