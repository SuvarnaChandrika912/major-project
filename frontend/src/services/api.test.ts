import { describe, expect, it, vi } from "vitest";
import { tokenStore } from "./api";

describe("tokenStore", () => {
  it("notifies subscribers when the authentication token changes in another tab", () => {
    const listener = vi.fn();
    const unsubscribe = tokenStore.subscribe(listener);

    window.dispatchEvent(new StorageEvent("storage", { key: "another_key" }));
    expect(listener).not.toHaveBeenCalled();

    window.dispatchEvent(new StorageEvent("storage", { key: "bis_saathi_token" }));
    expect(listener).toHaveBeenCalledOnce();

    unsubscribe();
    window.dispatchEvent(new StorageEvent("storage", { key: "bis_saathi_token" }));
    expect(listener).toHaveBeenCalledOnce();
  });
});
